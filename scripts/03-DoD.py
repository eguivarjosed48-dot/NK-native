"""
Paso 3: DoD (DEM of Difference) sobre el polígono del glaciar 2017.

Compara los DEMs corregidos contra la referencia 2025 en dos modos:
  - Opción B (principal): todos los DEMs en variante NK (consistencia).
  - Opción A (sensibilidad): variante mixta según decisión de CV del Paso 2.

Salidas:
  - dod/<year>_vs_2025_<opcion>.tif   (GeoTIFF del DoD)
  - dod_summary.csv                    (métricas por DoD)
  - dod_figures/<year>_vs_2025_<opcion>.png (histograma + mapa)
"""

from __future__ import annotations

import csv
import gc
import os
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
from nkdem.io import write_csv  # noqa: E402
from nkdem.raster import (  # noqa: E402
    downsample_mean,
    load_dem_with_mask,
    read_raster,
    write_geotiff,
)
from nkdem.stats import estimar_n_eff, nmad  # noqa: E402

OUTPUT_DOD_DIR_NAME = "dod"
OUTPUT_FIG_DIR_NAME = "dod_figures"
CSV_OUTPUT_NAME = "dod_summary.csv"

YEARS = ["2017", "2018", "2023"]

# Número efectivo de píxeles independientes para propagación de error.
# Se mantiene como fallback explícito si el variograma no converge.
N_EFF_FRACTION = 0.05


def calcular_dod(dem_a, dem_b, mask_dod):
    """dH = dem_a - dem_b (a: año, b: referencia). NaN fuera de la máscara."""
    dh = dem_a - dem_b
    dh[~mask_dod] = np.nan
    return dh


def estadisticas_dod(dh, pixel_area, n_eff):
    """Métricas robustas y propagación de error.

    ``n_eff`` es el número efectivo de píxeles independientes, estimado
    preferentemente por variograma (``estimar_n_eff``) o por fracción
    arbitraria de fallback (``N_EFF_FRACTION``).
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

    # Propagación de error (aleatorio)
    # σ_V ≈ σ_dH × A / √N_eff
    n_eff = max(1, int(n_eff))
    sigma_v = std * area / np.sqrt(n_eff)
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


def _n_eff_para_dod(dh: np.ndarray, pixel_size: float) -> dict:
    """Estima n_eff por variograma con fallback a fracción arbitraria.

    Devuelve un dict con n_eff, rango_correlacion_px, rango_correlacion_m
    y usando_fallback.
    """
    return estimar_n_eff(dh, pixel_size)


def main() -> None:
    cfg = load_config()
    output_dod_dir = Path(cfg.root / OUTPUT_DOD_DIR_NAME)
    output_fig_dir = Path(cfg.root / OUTPUT_FIG_DIR_NAME)
    output_dod_dir.mkdir(parents=True, exist_ok=True)
    output_fig_dir.mkdir(parents=True, exist_ok=True)

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
    _, _, _, glacier_mask = load_dem_with_mask(
        cfg.reference_dem, cfg.glacier_polygon
    )
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

    # Variante elegida por año (según decisión de CV del Paso 2).
    variant_choice = {"2017": "NK", "2018": "deramp3", "2023": "NK"}

    resultados = []

    # --- Opción B (principal): todos NK ---
    print("\n" + "-" * 84)
    print("OPCIÓN B (principal): todos los DEMs en variante NK")
    print("-" * 84)

    for year in YEARS:
        ruta = cfg.variant_dem(year, "NK")
        print(f"\n  [{year} vs {cfg.reference_year}] usando NK")
        dem_arr, _, _, _ = read_raster(ruta)
        mask_dod = glacier_mask & np.isfinite(dem_arr) & np.isfinite(ref_arr)
        dh = calcular_dod(dem_arr, ref_arr, mask_dod)

        # Propagación de error por variograma (con fallback a fracción arbitraria).
        neff = _n_eff_para_dod(dh, pixel_size)
        stats = estadisticas_dod(dh, pixel_area, neff["n_eff"])
        if stats is None:
            print("    Sin píxeles válidos. Se omite.")
            continue

        print(
            f"    n = {stats['n_pixels']:,} px | Área = {stats['area_km2']:.3f} km²"
        )
        print(
            f"    dH medio = {stats['dh_mean_m']:+.3f} m | Mediana = {stats['dh_median_m']:+.3f} m | NMAD = {stats['dh_nmad_m']:.3f} m"
        )
        print(
            f"    P5 = {stats['dh_p5_m']:+.3f} | P95 = {stats['dh_p95_m']:+.3f} m"
        )
        print(
            f"    Volumen = {stats['volume_m3']/1e6:+.3f} × 10⁶ m³  "
            f"(σ_V = {stats['sigma_volume_m3']/1e6:.3f} × 10⁶ m³, "
            f"{stats['sigma_volume_pct']:+.2f}% del volumen)"
        )
        if neff["usando_fallback"]:
            print(
                f"    [fallback] n_eff por fracción arbitraria "
                f"(N_EFF_FRACTION={N_EFF_FRACTION})"
            )
        else:
            print(
                f"    [variograma] rango = {neff['rango_correlacion_px']:.1f} px "
                f"({neff['rango_correlacion_m']:.1f} m), modelo = {neff['modelo']}, "
                f"n_eff = {neff['n_eff']:,}"
            )

        ruta_tif = output_dod_dir / f"{year}_vs_{cfg.reference_year}_B.tif"
        write_geotiff(ruta_tif, dh, ref_transform, ref_crs)
        ruta_png = output_fig_dir / f"{year}_vs_{cfg.reference_year}_B.png"
        figura_diagnostico(dh, year, "B (NK)", ruta_png)

        resultados.append(
            {
                "option": "B",
                "variant": "NK",
                "year": year,
                "ref_year": cfg.reference_year,
                "rango_correlacion_px": neff["rango_correlacion_px"],
                "rango_correlacion_m": neff["rango_correlacion_m"],
                "n_eff_calculado": neff["n_eff"],
                "modelo_variograma": neff["modelo"],
                "usando_fallback": neff["usando_fallback"],
                **stats,
                "geotiff": str(ruta_tif.resolve()),
                "figure": str(ruta_png.resolve()),
            }
        )
        del dem_arr, dh; gc.collect()

    # --- Opción A (sensibilidad): mixta según CV ---
    print("\n" + "-" * 84)
    print("OPCIÓN A (sensibilidad): variante mixta según decisión de CV")
    print("-" * 84)

    for year in YEARS:
        var = variant_choice[year]
        if var == "NK":
            ruta = cfg.variant_dem(year, "NK")
        elif var == "deramp3":
            ruta = cfg.variant_dem(year, "deramp3")
        elif var == "derampCV":
            ruta = cfg.variant_dem(year, "derampCV")
        else:
            print(f"  [{year}] variante desconocida: {var}. Se omite.")
            continue

        print(f"\n  [{year} vs {cfg.reference_year}] usando {var}")
        dem_arr, _, _, _ = read_raster(ruta)
        mask_dod = glacier_mask & np.isfinite(dem_arr) & np.isfinite(ref_arr)
        dh = calcular_dod(dem_arr, ref_arr, mask_dod)

        neff = _n_eff_para_dod(dh, pixel_size)
        stats = estadisticas_dod(dh, pixel_area, neff["n_eff"])
        if stats is None:
            print("    Sin píxeles válidos. Se omite.")
            continue

        print(
            f"    n = {stats['n_pixels']:,} px | Área = {stats['area_km2']:.3f} km²"
        )
        print(
            f"    dH medio = {stats['dh_mean_m']:+.3f} m | Mediana = {stats['dh_median_m']:+.3f} m | NMAD = {stats['dh_nmad_m']:.3f} m"
        )
        print(
            f"    P5 = {stats['dh_p5_m']:+.3f} | P95 = {stats['dh_p95_m']:+.3f} m"
        )
        print(
            f"    Volumen = {stats['volume_m3']/1e6:+.3f} × 10⁶ m³  "
            f"(σ_V = {stats['sigma_volume_m3']/1e6:.3f} × 10⁶ m³, "
            f"{stats['sigma_volume_pct']:+.2f}% del volumen)"
        )
        if neff["usando_fallback"]:
            print(
                f"    [fallback] n_eff por fracción arbitraria "
                f"(N_EFF_FRACTION={N_EFF_FRACTION})"
            )
        else:
            print(
                f"    [variograma] rango = {neff['rango_correlacion_px']:.1f} px "
                f"({neff['rango_correlacion_m']:.1f} m), modelo = {neff['modelo']}, "
                f"n_eff = {neff['n_eff']:,}"
            )

        ruta_tif = output_dod_dir / f"{year}_vs_{cfg.reference_year}_A.tif"
        write_geotiff(ruta_tif, dh, ref_transform, ref_crs)
        ruta_png = output_fig_dir / f"{year}_vs_{cfg.reference_year}_A.png"
        figura_diagnostico(dh, year, f"A ({var})", ruta_png)

        resultados.append(
            {
                "option": "A",
                "variant": var,
                "year": year,
                "ref_year": cfg.reference_year,
                "rango_correlacion_px": neff["rango_correlacion_px"],
                "rango_correlacion_m": neff["rango_correlacion_m"],
                "n_eff_calculado": neff["n_eff"],
                "modelo_variograma": neff["modelo"],
                "usando_fallback": neff["usando_fallback"],
                **stats,
                "geotiff": str(ruta_tif.resolve()),
                "figure": str(ruta_png.resolve()),
            }
        )
        del dem_arr, dh; gc.collect()

    # ==========================================================================
    # RESUMEN Y CSV
    # ==========================================================================
    print("\n" + "=" * 84)
    print("RESUMEN DoD")
    print("=" * 84)

    print(f"\n{'Year':<6} {'Opción':<7} {'Variante':<9} {'n_px':>10} "
          f"{'dH_mean':>10} {'dH_med':>10} {'NMAD':>8} {'Vol (10⁶ m³)':>15}")
    print("-" * 84)
    for r in resultados:
        print(
            f"{r['year']:<6} {r['option']:<7} {r['variant']:<9} {r['n_pixels']:>10,} "
            f"{r['dh_mean_m']:>+10.3f} {r['dh_median_m']:>+10.3f} "
            f"{r['dh_nmad_m']:>8.3f} {r['volume_m3']/1e6:>+15.3f}"
        )

    print("\n" + "-" * 84)
    print("SENSIBILIDAD: diferencia Opción A (mixta) − Opción B (todo NK)")
    print("-" * 84)
    print(f"{'Year':<6} {'ΔVolumen (10⁶ m³)':>20} {'ΔVolumen (%)':>15} {'ΔdH_mean (m)':>15}")
    print("-" * 60)
    for year in YEARS:
        b = next((r for r in resultados if r["year"] == year and r["option"] == "B"), None)
        a = next((r for r in resultados if r["year"] == year and r["option"] == "A"), None)
        if b is None or a is None:
            continue
        dvol = (a["volume_m3"] - b["volume_m3"]) / 1e6
        dvol_pct = 100 * (a["volume_m3"] - b["volume_m3"]) / b["volume_m3"] if b["volume_m3"] != 0 else np.nan
        ddh = a["dh_mean_m"] - b["dh_mean_m"]
        print(f"{year:<6} {dvol:>+20.3f} {dvol_pct:>+14.2f}% {ddh:>+15.3f}")

    csv_path = Path(cfg.root / CSV_OUTPUT_NAME)
    if resultados:
        write_csv(resultados, csv_path)
        print(f"\nCSV guardado: {csv_path.resolve()}")

    print("\nArchivos generados:")
    print(f"  GeoTIFFs DoD: {output_dod_dir.resolve()}/")
    print(f"  Figuras:      {output_fig_dir.resolve()}/")


if __name__ == "__main__":
    main()
