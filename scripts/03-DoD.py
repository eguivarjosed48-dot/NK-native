"""
Paso 3: DoD (DEM of Difference) sobre el polígono del glaciar 2017.

Compara los DEMs corregidos contra la referencia 2025 en tres modos:
  - Opción B (principal): todos los DEMs en variante NK (consistencia).
  - Opción A (según CV): variante aceptada por la validación cruzada del
    Paso 2 para cada año (NK o deramp3).
  - Opción C (sensibilidad): deramp3 forzado en todos los años, es decir, el
    resultado que se obtendría aplicando el deramp sin verificación.

Salidas:
  - dod/<year>_vs_2025_<opcion>.tif   (GeoTIFF del DoD)
  - dod_summary.csv                    (métricas por DoD)
  - dod_figures/<year>_vs_2025_<opcion>.png (histograma + mapa)
"""

from __future__ import annotations

import gc
import sys
import warnings
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore", message=".*partition.*MaskedArray.*")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nkdem.config import load_config, require_files  # noqa: E402
from nkdem.io import read_csv, write_csv  # noqa: E402
from nkdem.raster import (  # noqa: E402
    load_dem_with_mask,
    read_raster,
    write_geotiff,
)
from nkdem.stats import estimar_n_eff, nmad  # noqa: E402

YEARS = ["2017", "2018", "2023"]

# Número efectivo de píxeles independientes para propagación de error.
# Se mantiene como fallback explícito si el variograma no converge.
N_EFF_FRACTION = 0.05


def calcular_dod(dem_a, dem_b, mask_dod):
    """dH = dem_a - dem_b (a: año, b: referencia). NaN fuera de la máscara."""
    dh = dem_a - dem_b
    dh[~mask_dod] = np.nan
    return dh


def estadisticas_dod(dh, pixel_area, ruido):
    """Métricas robustas y propagación de error.

    La incertidumbre del volumen se propaga a partir del **ruido** medido en
    el terreno estable (``ruido["sigma_m"]``, NMAD del residual de
    co-registro) y de su longitud de correlación espacial
    (``ruido["rango_m"]``), no de la dispersión del cambio real:

        σ_V ≈ σ_noise × A / √N_eff,   N_eff = A / rango²

    que equivale a σ_V ≈ σ_noise × rango × √A (Rolstad et al., 2009).
    """
    vals = dh[np.isfinite(dh)]
    if vals.size == 0:
        return None

    n = vals.size
    mean = float(np.mean(vals))
    median = float(np.median(vals))
    nmad_v = float(nmad(vals))
    p5 = float(np.percentile(vals, 5))
    p95 = float(np.percentile(vals, 95))
    std = float(np.std(vals))

    area = n * pixel_area
    volume = float(np.sum(vals) * pixel_area)  # m³
    volume_mean = mean * area  # m³ (equivalente)

    if not np.isfinite(ruido["rango_m"]):
        # Fallback documentado: fracción arbitraria de píxeles efectivos.
        n_eff = max(1, int(n * N_EFF_FRACTION))
    else:
        rango_m = max(float(ruido["rango_m"]), float(pixel_area**0.5))
        n_eff = max(1, int(round(area / (rango_m**2))))
    sigma_v = float(ruido["sigma_m"]) * area / np.sqrt(n_eff)
    sigma_pct = 100.0 * sigma_v / volume if volume != 0 else float("nan")

    return {
        "n_pixels": int(n),
        "area_m2": float(area),
        "area_km2": float(area / 1e6),
        "dh_mean_m": mean,
        "dh_median_m": median,
        "dh_nmad_m": nmad_v,
        "dh_std_m": std,
        "dh_p5_m": p5,
        "dh_p95_m": p95,
        "volume_m3": volume,
        "volume_mean_m3": float(volume_mean),
        "volume_km3": volume / 1e9,
        "n_eff_used": int(n_eff),
        "sigma_noise_m": float(ruido["sigma_m"]),
        "rango_correlacion_px": float(ruido["rango_px"]),
        "rango_correlacion_m": float(ruido["rango_m"]),
        "modelo_variograma": ruido["modelo"],
        "usando_fallback": bool(ruido["usando_fallback"]),
        "sigma_volume_m3": float(sigma_v),
        "sigma_volume_pct": float(sigma_pct),
    }


def figura_diagnostico(dh, year, variant, ruta_png, vmin_pct=2, vmax_pct=98):
    """Histograma + mapa del DoD."""
    vals = dh[np.isfinite(dh)]
    if vals.size == 0:
        return
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    axes[0].hist(vals, bins=100, color="steelblue", alpha=0.85)
    axes[0].axvline(np.median(vals), color="red", linestyle="--",
                    label=f"Mediana = {np.median(vals):.2f} m")
    axes[0].axvline(np.mean(vals), color="orange", linestyle=":",
                    label=f"Media = {np.mean(vals):.2f} m")
    axes[0].set_xlabel("dH (m)")
    axes[0].set_ylabel("Frecuencia")
    axes[0].set_title(f"DoD {year} vs 2025 [{variant}] — Histograma")
    axes[0].legend()

    vmin, vmax = np.percentile(vals, [vmin_pct, vmax_pct])
    im = axes[1].imshow(dh, cmap="RdBu_r", vmin=vmin, vmax=vmax)
    axes[1].set_title(f"DoD {year} vs 2025 [{variant}] — Mapa")
    axes[1].axis("off")
    fig.colorbar(im, ax=axes[1], label="dH (m)", shrink=0.8)

    plt.tight_layout()
    plt.savefig(ruta_png, dpi=120, bbox_inches="tight")
    plt.close(fig)


def modelo_ruido_terreno_estable(
    dem_arr: np.ndarray,
    ref_arr: np.ndarray,
    stable_mask: np.ndarray,
    pixel_size: float,
    margen_px: int = 60,
) -> dict:
    """Caracteriza el ruido del co-registro en terreno estable.

    Devuelve el NMAD del residual de co-registro (``sigma_m``) y la longitud
    de correlación estimada con el variograma experimental del mismo residual
    (``rango_px``/``rango_m``). Si el variograma no converge se usa la
    fracción arbitraria ``N_EFF_FRACTION`` como fallback documentado.
    """
    dh = dem_arr - ref_arr
    valores = dh[stable_mask]
    valores = valores[np.isfinite(valores)]
    if valores.size == 0:
        return {
            "sigma_m": float("nan"),
            "rango_px": float("nan"),
            "rango_m": float("nan"),
            "modelo": "fallback",
            "usando_fallback": True,
            "n_estable": 0,
        }

    sigma_m = float(nmad(valores))

    filas, columnas = np.nonzero(stable_mask)
    r0 = max(int(filas.min()) - margen_px, 0)
    r1 = min(int(filas.max()) + margen_px + 1, dh.shape[0])
    c0 = max(int(columnas.min()) - margen_px, 0)
    c1 = min(int(columnas.max()) + margen_px + 1, dh.shape[1])
    recorte = np.where(stable_mask, dh, np.nan)[r0:r1, c0:c1]

    variograma = estimar_n_eff(recorte, pixel_size)
    if variograma["usando_fallback"] or variograma["rango_correlacion_px"] is None:
        return {
            "sigma_m": sigma_m,
            "rango_px": float("nan"),
            "rango_m": float("nan"),
            "modelo": "fallback",
            "usando_fallback": True,
            "n_estable": int(valores.size),
        }

    return {
        "sigma_m": sigma_m,
        "rango_px": float(variograma["rango_correlacion_px"]),
        "rango_m": float(variograma["rango_correlacion_m"]),
        "modelo": variograma["modelo"],
        "usando_fallback": False,
        "n_estable": int(valores.size),
    }


def elegir_variantes_por_cv(cfg) -> dict[str, str]:
    """Variante aceptada por año según la validación cruzada del Paso 2.

    Lee ``coreg_variants_summary.csv`` y usa la columna ``cv_acepta``: si la CV
    aceptó el deramp se usa ``deramp3``, en caso contrario ``NK``.
    """
    filas = read_csv(cfg.coreg_csv)
    eleccion = {year: "NK" for year in YEARS}
    if not filas:
        print(
            "  AVISO: no se encontró coreg_variants_summary.csv; "
            "se usa NK en todos los años para la Opción A."
        )
        return eleccion

    for fila in filas:
        year = str(fila.get("year", "")).strip()
        if year not in eleccion:
            continue
        acepta = str(fila.get("cv_acepta", "")).strip().lower()
        if acepta in {"true", "1", "sí", "si"}:
            eleccion[year] = "deramp3"
    return eleccion


def procesar_dod(
    year: str,
    opcion: str,
    variante: str,
    *,
    cfg,
    ref_arr: np.ndarray,
    ref_transform,
    ref_crs,
    glacier_mask: np.ndarray,
    pixel_area: float,
    ruido: dict,
    resultados: list[dict],
) -> None:
    """Calcula, guarda y resume el DoD de un año para una opción dada."""
    ruta = cfg.variant_dem(year, variante)
    if not ruta.exists():
        print(f"    [{year} | opción {opcion}] variante no disponible: {ruta.name}")
        return

    print(f"\n  [{year} vs {cfg.reference_year}] opción {opcion} — variante {variante}")
    dem_arr, _, _, _ = read_raster(ruta)
    mask_dod = glacier_mask & np.isfinite(dem_arr) & np.isfinite(ref_arr)
    dh = calcular_dod(dem_arr, ref_arr, mask_dod)

    stats = estadisticas_dod(dh, pixel_area, ruido)
    if stats is None:
        print("    Sin píxeles válidos. Se omite.")
        return

    print(f"    n = {stats['n_pixels']:,} px | Área = {stats['area_km2']:.3f} km²")
    print(
        f"    dH medio = {stats['dh_mean_m']:+.3f} m | "
        f"Mediana = {stats['dh_median_m']:+.3f} m | NMAD = {stats['dh_nmad_m']:.3f} m"
    )
    print(f"    P5 = {stats['dh_p5_m']:+.3f} | P95 = {stats['dh_p95_m']:+.3f} m")
    print(
        f"    Volumen = {stats['volume_m3']/1e6:+.3f} × 10⁶ m³  "
        f"(σ_V = {stats['sigma_volume_m3']:,.0f} m³, "
        f"{stats['sigma_volume_pct']:+.2f}% del volumen)"
    )
    if stats["usando_fallback"]:
        print(
            "    [ruido] fallback: variograma no convergido en terreno estable "
            f"(N_EFF_FRACTION={N_EFF_FRACTION}); se usa n_eff = "
            f"{stats['n_eff_used']:,}"
        )
    else:
        print(
            f"    [ruido] σ_estable = {stats['sigma_noise_m']:.3f} m, "
            f"rango = {stats['rango_correlacion_px']:.1f} px "
            f"({stats['rango_correlacion_m']:.1f} m), modelo = "
            f"{stats['modelo_variograma']}, N_eff = {stats['n_eff_used']:,}"
        )

    ruta_tif = cfg.dod_dir / f"{year}_vs_{cfg.reference_year}_{opcion}.tif"
    write_geotiff(ruta_tif, dh, ref_transform, ref_crs)
    ruta_png = cfg.dod_figures_dir / f"{year}_vs_{cfg.reference_year}_{opcion}.png"
    figura_diagnostico(dh, year, f"{opcion} ({variante})", ruta_png)

    resultados.append(
        {
            "option": opcion,
            "variant": variante,
            "year": year,
            "ref_year": cfg.reference_year,
            **stats,
            "geotiff": cfg.rel(ruta_tif),
            "figure": cfg.rel(ruta_png),
        }
    )
    del dem_arr, dh
    gc.collect()


def main() -> None:
    cfg = load_config()
    cfg.dod_dir.mkdir(parents=True, exist_ok=True)
    cfg.dod_figures_dir.mkdir(parents=True, exist_ok=True)

    require_files(
        {
            "DEM de referencia": cfg.reference_dem,
            "Polígono glaciar 2017": cfg.glacier_polygon,
            **{
                f"DEM variante NK {year}": cfg.variant_dem(year, "NK")
                for year in YEARS
            },
        }
    )

    print("=" * 84)
    print("PASO 3: DoD SOBRE GLACIAR 2017")
    print(f"Referencia: {cfg.reference_year}  |  Años: {YEARS}")
    print("=" * 84)

    ref_arr, ref_transform, ref_crs, _ = read_raster(cfg.reference_dem)
    _, _, _, glacier_mask = load_dem_with_mask(cfg.reference_dem, cfg.glacier_polygon)
    n_glaciar = int(glacier_mask.sum())
    if n_glaciar == 0:
        raise ValueError(
            "El polígono del glaciar no cubre ningún píxel válido del ráster "
            f"de referencia ({cfg.reference_dem}). Revisa que el polígono "
            "tenga el CRS correcto y solape con la extensión del DEM."
        )
    pixel_area = abs(ref_transform.a * ref_transform.e)
    pixel_size = (pixel_area) ** 0.5  # píxel asumido cuadrado (m)
    print(f"  Píxeles dentro del polígono del glaciar: {n_glaciar:,}")
    print(f"  Área del polígono: {n_glaciar * pixel_area / 1e6:.3f} km²")

    variantes_cv = elegir_variantes_por_cv(cfg)
    print(
        "  Variante aceptada por la CV del paso 2: "
        + ", ".join(f"{year}={variante}" for year, variante in variantes_cv.items())
    )

    # Modelo de ruido del co-registro en terreno estable (por año).
    _, _, _, stable_mask = load_dem_with_mask(cfg.reference_dem, cfg.stable_terrain)
    ruidos: dict[str, dict] = {}
    for year in YEARS:
        dem_nk, _, _, dem_mask = load_dem_with_mask(cfg.nk_dem(year), cfg.stable_terrain)
        ruido = modelo_ruido_terreno_estable(
            dem_nk, ref_arr, stable_mask & dem_mask, pixel_size
        )
        ruidos[year] = ruido
        print(
            f"  Ruido {year} (terreno estable): σ = {ruido['sigma_m']:.3f} m, "
            f"rango = {ruido['rango_m']:.1f} m, modelo = {ruido['modelo']}"
        )
        del dem_nk, dem_mask
        gc.collect()

    resultados: list[dict] = []
    contexto = dict(
        cfg=cfg,
        ref_arr=ref_arr,
        ref_transform=ref_transform,
        ref_crs=ref_crs,
        glacier_mask=glacier_mask,
        pixel_area=pixel_area,
        resultados=resultados,
    )

    print("\n" + "-" * 84)
    print("OPCIÓN B (principal): todos los DEMs en variante NK")
    print("-" * 84)
    for year in YEARS:
        procesar_dod(year, "B", "NK", **contexto, ruido=ruidos[year])

    print("\n" + "-" * 84)
    print("OPCIÓN A (según CV): variante aceptada por la validación cruzada")
    print("-" * 84)
    for year in YEARS:
        procesar_dod(year, "A", variantes_cv[year], **contexto, ruido=ruidos[year])

    print("\n" + "-" * 84)
    print("OPCIÓN C (sensibilidad): deramp3 aplicado en todos los años")
    print("-" * 84)
    for year in YEARS:
        procesar_dod(year, "C", "deramp3", **contexto, ruido=ruidos[year])

    # ==========================================================================
    # RESUMEN Y CSV
    # ==========================================================================
    print("\n" + "=" * 84)
    print("RESUMEN DoD")
    print("=" * 84)

    print(f"\n{'Year':<6} {'Opción':<7} {'Variante':<9} {'n_px':>10} "
          f"{'dH_mean':>10} {'dH_med':>10} {'NMAD':>8} {'Vol (10⁶ m³)':>15} "
          f"{'σ_V (10⁶ m³)':>14}")
    print("-" * 84)
    for r in resultados:
        print(
            f"{r['year']:<6} {r['option']:<7} {r['variant']:<9} {r['n_pixels']:>10,} "
            f"{r['dh_mean_m']:>+10.3f} {r['dh_median_m']:>+10.3f} "
            f"{r['dh_nmad_m']:>8.3f} {r['volume_m3']/1e6:>+15.3f} "
            f"{r['sigma_volume_m3']/1e6:>14.3f}"
        )

    for etiqueta, opcion in (
        ("A (según CV) − B (todo NK)", "A"),
        ("C (deramp3 forzado) − B (todo NK)", "C"),
    ):
        print("\n" + "-" * 84)
        print(f"SENSIBILIDAD: {etiqueta}")
        print("-" * 84)
        print(f"{'Year':<6} {'ΔVolumen (10⁶ m³)':>20} {'ΔVolumen (%)':>15} "
              f"{'ΔdH_mean (m)':>15}")
        print("-" * 60)
        for year in YEARS:
            b = next(
                (r for r in resultados if r["year"] == year and r["option"] == "B"),
                None,
            )
            a = next(
                (r for r in resultados if r["year"] == year and r["option"] == opcion),
                None,
            )
            if b is None or a is None:
                continue
            dvol = (a["volume_m3"] - b["volume_m3"]) / 1e6
            dvol_pct = (
                100 * (a["volume_m3"] - b["volume_m3"]) / b["volume_m3"]
                if b["volume_m3"] != 0
                else np.nan
            )
            ddh = a["dh_mean_m"] - b["dh_mean_m"]
            print(f"{year:<6} {dvol:>+20.3f} {dvol_pct:>+14.2f}% {ddh:>+15.3f}")

    if resultados:
        write_csv(resultados, cfg.dod_csv)
        print(f"\nCSV guardado: {cfg.dod_csv}")

    print("\nArchivos generados:")
    print(f"  GeoTIFFs DoD: {cfg.dod_dir}")
    print(f"  Figuras:      {cfg.dod_figures_dir}")


if __name__ == "__main__":
    main()
