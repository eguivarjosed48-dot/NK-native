"""
Paso 4: Generación de figuras y tablas para el informe final.

Asume que se han ejecutado:
  - 00-check-input.py         -> dems_alineados/
  - 01-nuth-kaab.py            -> dems_nk/
  - 02-NK-Variantes.py         -> dems_variants/ + coreg_variants_summary.csv
  - 03-DoD.py                  -> dod/ + dod_summary.csv + dod_figures/
  - test_glaciar_vs_estable.py -> test_outputs/

Genera:
  report/tables/*.csv, report/tables/T6_report_main.md
  report/figures/*.png
  report/dod_geotiffs/*.tif (copia de los GeoTIFFs del DoD)
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
from matplotlib.colors import TwoSlopeNorm, ListedColormap
from matplotlib.patches import Patch
from scipy.stats import binned_statistic, spearmanr

warnings.filterwarnings("ignore", message=".*partition.*MaskedArray.*")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nkdem.config import load_config, require_files  # noqa: E402
from nkdem.io import leer_csv, write_csv  # noqa: E402
from nkdem.raster import (  # noqa: E402
    downsample_mean,
    load_dem_with_mask,
    read_raster,
)

REFERENCE_YEAR = "2025"

YEARS = ["2017", "2018", "2023"]

# Variante elegida por año (según decisión de CV del Paso 2)
VARIANT_CHOICE = {"2017": "NK", "2018": "deramp3", "2023": "NK"}

# Resolución para mapas (evita PNGs gigantes). 1 = resolución nativa.
MAP_DOWNSAMPLE = 4

# Percentiles para recorte visual en mapas
VMIN_PCT = 2
VMAX_PCT = 98

# Franjas altitudinales para hipsometría
N_HYPSO_BINS = 20


def nmad(data):
    med = np.median(data)
    return float(1.4826 * np.median(np.abs(data - med)))


def fig1_polygons_overview(transform, crs, stable_mask, glacier_mask, figures_dir):
    print("  [F1] Vista general de polígonos...")
    fig, ax = plt.subplots(figsize=(10, 9))

    bg = np.full(stable_mask.shape, np.nan)
    bg[stable_mask] = 1.0
    bg[glacier_mask] = 2.0

    cmap = ListedColormap(["green", "red"])
    ds = MAP_DOWNSAMPLE
    bg_ds = downsample_mean(np.where(np.isfinite(bg), bg, 0), ds)
    bg_ds_plot = np.where(bg_ds < 0.5, np.nan, bg_ds)

    ax.imshow(bg_ds_plot, cmap=cmap, vmin=1, vmax=2, interpolation="nearest")
    ax.set_title("Zona estable (verde) y glaciar 2017 (rojo)")
    ax.axis("off")

    legend_elements = [
        Patch(facecolor="green", label="Terreno estable"),
        Patch(facecolor="red", label="Glaciar 2017"),
    ]
    ax.legend(handles=legend_elements, loc="upper right")
    plt.tight_layout()
    plt.savefig(figures_dir / "F1_polygons_overview.png",
                dpi=130, bbox_inches="tight")
    plt.close(fig)


def fig2_3_residuals_nk(ref_arr, stable_mask, cfg, figures_dir):
    print("  [F2/F3] Residuales NK por año...")
    fig_h, axes_h = plt.subplots(1, len(YEARS), figsize=(5 * len(YEARS), 4))
    fig_m, axes_m = plt.subplots(1, len(YEARS), figsize=(5 * len(YEARS), 5))

    for i, year in enumerate(YEARS):
        ruta = cfg.variants_dir / f"{year}_NK.tif"
        if not ruta.exists():
            continue
        with open(ruta, "rb") as _fh:
            import rasterio
            with rasterio.open(_fh) as src:
                arr = src.read(1).astype(np.float32)
                if src.nodata is not None:
                    arr[arr == src.nodata] = np.nan
        diff = arr - ref_arr
        vals = diff[stable_mask]
        vals = vals[np.isfinite(vals)]

        ax = axes_h[i]
        ax.hist(vals, bins=100, color="steelblue", alpha=0.85)
        ax.axvline(np.median(vals), color="red", linestyle="--",
                   label=f"Mediana = {np.median(vals):+.3f}")
        ax.axvline(np.mean(vals), color="orange", linestyle=":",
                   label=f"Media = {np.mean(vals):+.3f}")
        ax.set_title(f"Residual NK {year} — zona estable")
        ax.set_xlabel("dH (m)")
        ax.set_ylabel("Frecuencia")
        ax.legend(fontsize=8)

        vmin, vmax = np.percentile(vals, [VMIN_PCT, VMAX_PCT])
        diff_plot = np.where(stable_mask, diff, np.nan)
        ds = MAP_DOWNSAMPLE
        diff_ds = downsample_mean(np.where(np.isfinite(diff_plot), diff_plot, 0), ds)
        diff_ds = np.where(diff_ds == 0, np.nan, diff_ds)
        im = axes_m[i].imshow(diff_ds, cmap="RdBu_r", vmin=vmin, vmax=vmax,
                              interpolation="nearest")
        axes_m[i].set_title(f"Residual NK {year} — mapa")
        axes_m[i].axis("off")
        fig_m.colorbar(im, ax=axes_m[i], shrink=0.7, label="dH (m)")

    fig_h.tight_layout()
    fig_h.savefig(figures_dir / "F2_residuals_nk_hist.png",
                  dpi=120, bbox_inches="tight")
    plt.close(fig_h)

    fig_m.tight_layout()
    fig_m.savefig(figures_dir / "F3_residuals_nk_map.png",
                  dpi=120, bbox_inches="tight")
    plt.close(fig_m)


def fig4_deramp_correction_2018(ref_arr, stable_mask, glacier_mask, cfg, figures_dir):
    print("  [F4] Campo de corrección del deramp3 en 2018...")
    ruta_nk = cfg.variants_dir / "2018_NK.tif"
    ruta_d3 = cfg.variants_dir / "2018_deramp3.tif"
    if not (ruta_nk.exists() and ruta_d3.exists()):
        print("    Faltan archivos de 2018, se omite.")
        return

    import rasterio

    with rasterio.open(ruta_nk) as src:
        nk = src.read(1).astype(np.float32)
        transform = src.transform
        crs = src.crs
        if src.nodata is not None:
            nk[nk == src.nodata] = np.nan
    with rasterio.open(ruta_d3) as src:
        d3 = src.read(1).astype(np.float32)
        if src.nodata is not None:
            d3[d3 == src.nodata] = np.nan

    corr = d3 - nk  # corrección aplicada por deramp3
    valid = np.isfinite(corr)

    corr_stable = corr[stable_mask & valid]
    corr_glacier = corr[glacier_mask & valid]

    print(
        f"    Corrección media en zona estable: {np.nanmean(corr_stable):+.3f} m "
        f"(mediana {np.nanmedian(corr_stable):+.3f})"
    )
    print(
        f"    Corrección media en glaciar:      {np.nanmean(corr_glacier):+.3f} m "
        f"(mediana {np.nanmedian(corr_glacier):+.3f})"
    )
    print(
        f"    Rango en glaciar: P5={np.nanpercentile(corr_glacier,5):+.3f} "
        f"P95={np.nanpercentile(corr_glacier,95):+.3f}"
    )

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    vmax = max(abs(np.nanpercentile(corr_glacier, 5)),
               abs(np.nanpercentile(corr_glacier, 95)))
    ds = MAP_DOWNSAMPLE
    corr_plot = np.where(valid & (stable_mask | glacier_mask), corr, np.nan)
    corr_ds = downsample_mean(np.where(np.isfinite(corr_plot), corr_plot, 0), ds)
    corr_ds = np.where(corr_ds == 0, np.nan, corr_ds)
    im = axes[0].imshow(corr_ds, cmap="RdBu_r", vmin=-vmax, vmax=vmax,
                        interpolation="nearest")
    axes[0].set_title("Campo de corrección deramp3 — 2018\n(rojo = resta, azul = suma)")
    axes[0].axis("off")
    fig.colorbar(im, ax=axes[0], shrink=0.7, label="Corrección (m)")

    axes[1].hist(corr_stable, bins=80, alpha=0.6, color="green",
                 label=f"Zona estable (n={corr_stable.size:,})")
    axes[1].hist(corr_glacier, bins=80, alpha=0.6, color="red",
                 label=f"Glaciar (n={corr_glacier.size:,})")
    axes[1].axvline(0, color="k", lw=0.5)
    axes[1].set_xlabel("Corrección aplicada (m)")
    axes[1].set_ylabel("Frecuencia")
    axes[1].set_title("Distribución de la corrección")
    axes[1].legend(fontsize=8)

    plt.tight_layout()
    plt.savefig(figures_dir / "F4_deramp_correction_map_2018.png",
                dpi=130, bbox_inches="tight")
    plt.close(fig)


def fig5_deramp_vs_slope_aspect(ref_arr, stable_mask, glacier_mask, cfg, figures_dir):
    print("  [F5] Correlación corrección deramp3 vs pendiente/aspecto (2018)...")
    ruta_nk = cfg.variants_dir / "2018_NK.tif"
    ruta_d3 = cfg.variants_dir / "2018_deramp3.tif"
    if not (ruta_nk.exists() and ruta_d3.exists()):
        return

    import rasterio
    import xdem

    with rasterio.open(ruta_nk) as src:
        nk = src.read(1).astype(np.float32)
        transform = src.transform
        if src.nodata is not None:
            nk[nk == src.nodata] = np.nan
    with rasterio.open(ruta_d3) as src:
        d3 = src.read(1).astype(np.float32)
        if src.nodata is not None:
            d3[d3 == src.nodata] = np.nan
    corr = d3 - nk

    ref_dem = xdem.DEM(cfg.reference_dem)
    slope = ref_dem.slope().data
    aspect = ref_dem.aspect().data

    valid = (np.isfinite(corr) & np.isfinite(slope) & np.isfinite(aspect)
             & glacier_mask)

    corr_v = corr[valid]
    slope_v = slope[valid]
    aspect_v = aspect[valid]

    print(f"    N válidos en glaciar: {corr_v.size:,}")
    print(f"    Correlación Spearman corrección vs pendiente: "
          f"{spearmanr(corr_v, slope_v).correlation:+.3f}")

    slope_bins = np.linspace(0, np.percentile(slope_v, 99), 15)
    stat_mean, _, _ = binned_statistic(slope_v, corr_v, statistic="mean", bins=slope_bins)
    stat_std, _, _ = binned_statistic(slope_v, corr_v, statistic="std", bins=slope_bins)
    bin_centers = 0.5 * (slope_bins[:-1] + slope_bins[1:])

    aspect_bins = np.linspace(0, 360, 33)
    stat_aspect, _, _ = binned_statistic(aspect_v, corr_v, statistic="mean", bins=aspect_bins)
    aspect_centers = np.deg2rad(0.5 * (aspect_bins[:-1] + aspect_bins[1:]))

    fig = plt.figure(figsize=(14, 5))

    ax1 = fig.add_subplot(1, 2, 1)
    ax1.errorbar(bin_centers, stat_mean, yerr=stat_std, fmt="o-", color="C0", capsize=3)
    ax1.axhline(0, color="k", lw=0.5)
    ax1.set_xlabel("Pendiente (°)")
    ax1.set_ylabel("Corrección media (m)")
    ax1.set_title("Corrección deramp3 vs pendiente (glaciar)")
    ax1.grid(alpha=0.3)

    ax2 = fig.add_subplot(1, 2, 2, projection="polar")
    ax2.bar(aspect_centers, stat_aspect, width=np.deg2rad(360 / 32),
            color="C1", alpha=0.85, edgecolor="k")
    ax2.set_theta_zero_location("N")
    ax2.set_theta_direction(-1)
    ax2.set_title("Corrección media por orientación (glaciar)")
    ax2.set_rlabel_position(45)

    plt.tight_layout()
    plt.savefig(figures_dir / "F5_deramp_vs_slope_aspect.png",
                dpi=130, bbox_inches="tight")
    plt.close(fig)


def fig6_7_dod(ref_transform, ref_crs, cfg, figures_dir):
    print("  [F6/F7] Mapas e histogramas del DoD...")
    dod_files = {}
    for year in YEARS:
        ruta = cfg.dod_dir / f"{year}_vs_{REFERENCE_YEAR}_A.tif"
        if not ruta.exists():
            ruta = cfg.dod_dir / f"{year}_vs_{REFERENCE_YEAR}_B.tif"
        if ruta.exists():
            dod_files[year] = ruta

    if not dod_files:
        print("    No hay DoD generados.")
        return

    fig, axes = plt.subplots(1, len(dod_files), figsize=(5 * len(dod_files), 5))
    if len(dod_files) == 1:
        axes = [axes]
    for i, (year, ruta) in enumerate(dod_files.items()):
        with rasterio.open(ruta) as src:
            dh = src.read(1).astype(np.float32)
            if src.nodata is not None:
                dh[dh == src.nodata] = np.nan
        vals = dh[np.isfinite(dh)]
        vmin, vmax = np.percentile(vals, [VMIN_PCT, VMAX_PCT])
        ds = MAP_DOWNSAMPLE
        dh_ds = downsample_mean(np.where(np.isfinite(dh), dh, 0), ds)
        dh_ds = np.where(dh_ds == 0, np.nan, dh_ds)
        im = axes[i].imshow(dh_ds, cmap="RdBu_r", vmin=vmin, vmax=vmax,
                            interpolation="nearest")
        axes[i].set_title(f"DoD {year} vs {REFERENCE_YEAR}\n"
                          f"Mediana = {np.median(vals):+.2f} m")
        axes[i].axis("off")
        fig.colorbar(im, ax=axes[i], shrink=0.7, label="dH (m)")
    plt.tight_layout()
    plt.savefig(figures_dir / "F6_dod_maps.png",
                dpi=130, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5))
    colors = {"2017": "C0", "2018": "C1", "2023": "C2"}
    for year, ruta in dod_files.items():
        with rasterio.open(ruta) as src:
            dh = src.read(1).astype(np.float32)
            if src.nodata is not None:
                dh[dh == src.nodata] = np.nan
        vals = dh[np.isfinite(dh)]
        ax.hist(vals, bins=80, alpha=0.5, color=colors.get(year, "gray"),
                label=f"{year} (n={vals.size:,}, med={np.median(vals):+.2f} m)")
    ax.axvline(0, color="k", lw=0.5)
    ax.set_xlabel("dH (m)")
    ax.set_ylabel("Frecuencia")
    ax.set_title(f"Histogramas de DoD (referencia {REFERENCE_YEAR})")
    ax.legend(fontsize=9)
    plt.tight_layout()
    plt.savefig(figures_dir / "F7_dod_histograms.png",
                dpi=130, bbox_inches="tight")
    plt.close(fig)


def fig8_hypsometry(ref_arr, glacier_mask, cfg, figures_dir):
    print("  [F8] Hipsometría del cambio...")
    dod_files = {}
    for year in YEARS:
        for suf in ["A", "B"]:
            ruta = cfg.dod_dir / f"{year}_vs_{REFERENCE_YEAR}_{suf}.tif"
            if ruta.exists():
                dod_files[year] = ruta
                break

    if not dod_files:
        return

    elev = ref_arr[glacier_mask]
    valid_elev = np.isfinite(elev)
    elev = elev[valid_elev]
    if elev.size == 0:
        return

    bins = np.linspace(np.percentile(elev, 1), np.percentile(elev, 99), N_HYPSO_BINS)
    centers = 0.5 * (bins[:-1] + bins[1:])

    fig, ax = plt.subplots(figsize=(8, 6))
    colors = {"2017": "C0", "2018": "C1", "2023": "C2"}

    import rasterio
    for year, ruta in dod_files.items():
        with rasterio.open(ruta) as src:
            dh = src.read(1).astype(np.float32)
            if src.nodata is not None:
                dh[dh == src.nodata] = np.nan
        dh_glacier = dh[glacier_mask]
        elev_orig = ref_arr[glacier_mask]
        valid = np.isfinite(elev_orig) & np.isfinite(dh_glacier)
        e = elev_orig[valid]
        d = dh_glacier[valid]
        if e.size == 0:
            continue
        stat, _, _ = binned_statistic(e, d, statistic="median", bins=bins)
        ax.plot(centers, stat, "o-", color=colors.get(year, "gray"),
                label=f"{year} vs {REFERENCE_YEAR}")

    ax.axvline(0, color="k", lw=0.5)
    ax.set_xlabel(f"Elevación DEM {REFERENCE_YEAR} (m)")
    ax.set_ylabel("dH mediano (m)")
    ax.set_title("Hipsometría del cambio (glaciar 2017)")
    ax.legend()
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(figures_dir / "F8_dod_hypsometry.png",
                dpi=130, bbox_inches="tight")
    plt.close(fig)


def fig9_sensitivity_B_vs_A(dod_csv_rows, figures_dir):
    print("  [F9] Sensibilidad Opción B vs A...")
    if not dod_csv_rows:
        return

    years_b, vol_b, vol_a = [], [], []
    for year in YEARS:
        b = next((r for r in dod_csv_rows if r["year"] == year and r["option"] == "B"), None)
        a = next((r for r in dod_csv_rows if r["year"] == year and r["option"] == "A"), None)
        if b and a:
            years_b.append(year)
            vol_b.append(float(b["volume_m3"]) / 1e6)
            vol_a.append(float(a["volume_m3"]) / 1e6)

    if not years_b:
        return

    x = np.arange(len(years_b))
    w = 0.35

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(x - w / 2, vol_b, w, label="Opción B (todo NK)", color="C0")
    ax.bar(x + w / 2, vol_a, w, label="Opción A (mixta)", color="C1")
    for i, (b, a) in enumerate(zip(vol_b, vol_a)):
        if b != 0:
            pct = 100 * (a - b) / b
            ax.annotate(f"{pct:+.1f}%", (x[i], max(b, a)),
                        textcoords="offset points", xytext=(0, 5),
                        ha="center", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(years_b)
    ax.set_ylabel("Volumen (10⁶ m³)")
    ax.set_title("Sensibilidad del volumen: Opción B vs Opción A")
    ax.legend()
    ax.grid(alpha=0.3, axis="y")
    plt.tight_layout()
    plt.savefig(figures_dir / "F9_sensitivity_B_vs_A.png",
                dpi=130, bbox_inches="tight")
    plt.close(fig)


def generar_tablas(cfg):
    print("\nGenerando tablas...")

    # T4: DoD summary
    if cfg.dod_csv.exists():
        rows = leer_csv(cfg.dod_csv)
        write_csv(rows, cfg.tables_dir / "T4_dod_summary.csv")

    # T3: variantes de co-registro
    if cfg.coreg_csv.exists():
        rows = leer_csv(cfg.coreg_csv)
        write_csv(rows, cfg.tables_dir / "T3_coreg_step2_variants.csv")

    # T5: glaciar vs estable
    if cfg.test_outputs_dir.joinpath("test_glaciar_vs_estable.csv").exists():
        rows = leer_csv(cfg.test_outputs_dir / "test_glaciar_vs_estable.csv")
        write_csv(rows, cfg.tables_dir / "T5_glacier_vs_stable.csv")

    # T6: markdown consolidado
    md_path = cfg.tables_dir / "T6_report_main.md"
    with open(md_path, "w") as f:
        f.write("# Tablas de resultados del análisis DoD\n\n")
        f.write(f"**Referencia:** {REFERENCE_YEAR}\n\n")

        f.write("## Tabla 3. Variantes de co-registro (Paso 2)\n\n")
        f.write("| Año | N_valid | NMAD_NK (m) | NMAD_deramp3 (m) | NMAD_CV (m) | NMAD_NKcv (m) | CV acepta | NMAD final (m) |\n")
        f.write("|---|---|---|---|---|---|---|---|\n")
        for r in leer_csv(cfg.tables_dir / "T3_coreg_step2_variants.csv"):
            f.write(f"| {r['year']} | {int(r['n_valid']):,} | "
                    f"{float(r['nmad_nk']):.3f} | {float(r['nmad_deramp3']):.3f} | "
                    f"{float(r['nmad_cv']):.3f} | {float(r['nmad_nk_cv']):.3f} | "
                    f"{r['cv_acepta']} | {float(r['nmad_derampCV']):.3f} |\n")
        f.write("\n")

        f.write("## Tabla 4. Resumen del DoD (Paso 3)\n\n")
        f.write("| Año | Opción | Variante | N_px | dH medio (m) | dH mediana (m) | NMAD (m) | Volumen (10⁶ m³) |\n")
        f.write("|---|---|---|---|---|---|---|---|\n")
        for r in leer_csv(cfg.tables_dir / "T4_dod_summary.csv"):
            f.write(f"| {r['year']} | {r['option']} | {r['variant']} | "
                    f"{int(r['n_pixels']):,} | {float(r['dh_mean_m']):+.3f} | "
                    f"{float(r['dh_median_m']):+.3f} | {float(r['dh_nmad_m']):.3f} | "
                    f"{float(r['volume_m3'])/1e6:+.3f} |\n")
        f.write("\n")

        f.write("## Tabla 5. Glaciar vs zona estable\n\n")
        for r in leer_csv(cfg.tables_dir / "T5_glacier_vs_stable.csv"):
            for k, v in r.items():
                f.write(f"- **{k}**: {v}\n")
        f.write("\n")

    print(f"    Markdown consolidado: {md_path.resolve()}")


def main() -> None:
    cfg = load_config()
    require_files(
        {
            "DEM de referencia": cfg.reference_dem,
            "Polígono terreno estable": cfg.stable_terrain,
            "Polígono glaciar 2017": cfg.glacier_polygon,
        }
    )

    for d in [cfg.report_dir, cfg.tables_dir, cfg.figures_dir,
              cfg.root / "report" / "dod_geotiffs"]:
        Path(d).mkdir(parents=True, exist_ok=True)

    print("=" * 78)
    print("PASO 4: GENERACIÓN DE FIGURAS Y TABLAS")
    print("=" * 78)

    print("\nCargando referencia y máscaras...")
    ref_arr, ref_transform, ref_crs, ref_mask = load_dem_with_mask(
        cfg.reference_dem, cfg.stable_terrain
    )
    _, _, _, glacier_mask = load_dem_with_mask(
        cfg.reference_dem, cfg.glacier_polygon
    )

    print("\nGenerando figuras...")
    fig1_polygons_overview(ref_transform, ref_crs, ref_mask, glacier_mask, cfg.figures_dir)
    fig2_3_residuals_nk(ref_arr, ref_mask, cfg, cfg.figures_dir)
    fig4_deramp_correction_2018(ref_arr, ref_mask, glacier_mask, cfg, cfg.figures_dir)
    fig5_deramp_vs_slope_aspect(ref_arr, ref_mask, glacier_mask, cfg, cfg.figures_dir)
    fig6_7_dod(ref_transform, ref_crs, cfg, cfg.figures_dir)
    fig8_hypsometry(ref_arr, glacier_mask, cfg, cfg.figures_dir)
    fig9_sensitivity_B_vs_A(leer_csv(cfg.dod_csv), cfg.figures_dir)

    # Copiar GeoTIFFs DoD a report/dod_geotiffs
    dod_geotiff_dir = cfg.root / "report" / "dod_geotiffs"
    dod_geotiff_dir.mkdir(parents=True, exist_ok=True)
    import shutil
    for tif in sorted((cfg.dod_dir).glob("*.tif")):
        shutil.copy2(tif, dod_geotiff_dir / tif.name)
    print(f"    GeoTIFFs DoD copiados a: {dod_geotiff_dir.resolve()}")

    generar_tablas(cfg)

    print("\n" + "=" * 78)
    print("PASO 4 completado.")
    print(f"Figuras: {cfg.figures_dir.resolve()}")
    print(f"Tablas:  {cfg.tables_dir.resolve()}")
    print("=" * 78)


if __name__ == "__main__":
    main()
