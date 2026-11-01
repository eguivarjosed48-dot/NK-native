"""
Paso 4: Generación de figuras y tablas para el informe final.

Consolida:
  - Figuras F1–F9  (Paso 4 original)
  - Figuras F10–F14 (Paso 6, confianza) — solo verifica que existan
  - Tablas T3–T5    (Pasos 2 y 3)
  - Tablas T8–T13   (Paso 6, confianza)
  - Markdown consolidado T6_report_main.md

Asume que se han ejecutado:
  - 00-check-input.py
  - 01-nuth-kaab.py
  - 02-NK-Variantes.py
  - 03-DoD.py
  - 06-confianza.py (para F10–F14 y T8–T13)
"""

import os
import csv
import gc
import warnings
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.features import geometry_mask
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from matplotlib.patches import Patch
from scipy.stats import binned_statistic, spearmanr
import xdem

warnings.filterwarnings("ignore", message=".*partition.*MaskedArray.*")

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================

REFERENCE_YEAR = "2025"
REFERENCE_FILE = "/Users/eguivar/Documents/2-2026/dron_ortofoto_dem_v4_completo/2025_B/2025_B_DSM.tif"
STABLE_TERRAIN_PATH = "data/stable_terrain.gpkg"
GLACIER_2017_PATH = "data/glaciar_2017.gpkg"

VARIANTS_DIR = "dems_variants"
DOD_DIR = "dod"
DOD_CSV = "dod_summary.csv"
VARIANTS_CSV = "coreg_variants_summary.csv"
GLACIER_STABLE_CSV = os.path.join("test_outputs", "test_glaciar_vs_estable.csv")

REPORT_DIR = "report"
TABLES_DIR = os.path.join(REPORT_DIR, "tables")
FIGURES_DIR = os.path.join(REPORT_DIR, "figures")
DOD_TIF_DIR = os.path.join(REPORT_DIR, "dod_geotiffs")

YEARS = ["2017", "2018", "2023"]
VARIANT_CHOICE = {"2017": "NK", "2018": "deramp3", "2023": "NK"}

MAP_DOWNSAMPLE = 4
VMIN_PCT = 2
VMAX_PCT = 98
N_HYPSO_BINS = 20

# Tablas del Paso 6 (confianza)
T8_CSV  = os.path.join(TABLES_DIR, "T8_confianza_pixel.csv")
T8B_CSV = os.path.join(TABLES_DIR, "T8b_confianza_r2.csv")
T9_CSV  = os.path.join(TABLES_DIR, "T9_confianza_variograma.csv")
T10_CSV = os.path.join(TABLES_DIR, "T10_confianza_volumen.csv")
T11_CSV = os.path.join(TABLES_DIR, "T11_confianza_literatura.csv")
T12_CSV = os.path.join(TABLES_DIR, "T12_confianza_extrap.csv")
T13_CSV = os.path.join(TABLES_DIR, "T13_confianza_temporal.csv")


# ==============================================================================
# UTILIDADES
# ==============================================================================

def nmad(data):
    med = np.nanmedian(data)
    return 1.4826 * np.nanmedian(np.abs(data - med))


def cargar_dem_con_mascara(ruta_dem, ruta_poligono):
    with rasterio.open(ruta_dem) as src:
        arr = src.read(1).astype(np.float32)
        transform = src.transform
        crs = src.crs
        nodata = src.nodata
        if nodata is not None:
            arr[arr == nodata] = np.nan
        gdf = gpd.read_file(ruta_poligono)
        if gdf.crs is None:
            raise ValueError(f"El polígono '{ruta_poligono}' no tiene CRS.")
        if gdf.crs != crs:
            gdf = gdf.to_crs(crs)
        out_mask = geometry_mask(
            gdf.geometry, out_shape=arr.shape, transform=transform, invert=False
        )
        mask = (~out_mask) & np.isfinite(arr)
    return arr, transform, crs, mask


def downsample(arr, factor):
    if factor <= 1:
        return arr
    h, w = arr.shape
    h2, w2 = (h // factor) * factor, (w // factor) * factor
    return arr[:h2, :w2].reshape(h2 // factor, factor, w2 // factor, factor).mean(axis=(1, 3))


def guardar_csv(filas, ruta):
    if not filas:
        return
    with open(ruta, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)


def leer_csv(ruta):
    if not os.path.exists(ruta):
        return []
    with open(ruta) as f:
        return list(csv.DictReader(f))


# ==============================================================================
# FIGURA 1: vista general de polígonos
# ==============================================================================

def fig1_polygons_overview(transform, crs, stable_mask, glacier_mask):
    print("  [F1] Vista general de polígonos...")
    fig, ax = plt.subplots(figsize=(10, 9))

    bg = np.full(stable_mask.shape, np.nan)
    bg[stable_mask] = 1.0
    bg[glacier_mask] = 2.0

    cmap = matplotlib.colors.ListedColormap(["green", "red"])
    ds = MAP_DOWNSAMPLE
    bg_ds = downsample(np.where(np.isfinite(bg), bg, 0), ds)
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
    plt.savefig(os.path.join(FIGURES_DIR, "F1_polygons_overview.png"),
                dpi=130, bbox_inches="tight")
    plt.close(fig)


# ==============================================================================
# FIGURA 2 y 3: residuales NK
# ==============================================================================

def fig2_3_residuals_nk(ref_arr, stable_mask):
    print("  [F2/F3] Residuales NK por año...")
    fig_h, axes_h = plt.subplots(1, len(YEARS), figsize=(5 * len(YEARS), 4))
    fig_m, axes_m = plt.subplots(1, len(YEARS), figsize=(5 * len(YEARS), 5))

    for i, year in enumerate(YEARS):
        ruta = os.path.join(VARIANTS_DIR, f"{year}_NK.tif")
        if not os.path.exists(ruta):
            continue
        with rasterio.open(ruta) as src:
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
        diff_ds = downsample(np.where(np.isfinite(diff_plot), diff_plot, 0), ds)
        diff_ds = np.where(diff_ds == 0, np.nan, diff_ds)
        im = axes_m[i].imshow(diff_ds, cmap="RdBu_r", vmin=vmin, vmax=vmax,
                              interpolation="nearest")
        axes_m[i].set_title(f"Residual NK {year} — mapa")
        axes_m[i].axis("off")
        fig_m.colorbar(im, ax=axes_m[i], shrink=0.7, label="dH (m)")

    fig_h.tight_layout()
    fig_h.savefig(os.path.join(FIGURES_DIR, "F2_residuals_nk_hist.png"),
                  dpi=120, bbox_inches="tight")
    plt.close(fig_h)

    fig_m.tight_layout()
    fig_m.savefig(os.path.join(FIGURES_DIR, "F3_residuals_nk_map.png"),
                  dpi=120, bbox_inches="tight")
    plt.close(fig_m)


# ==============================================================================
# FIGURA 4: campo de corrección del deramp3 en 2018
# ==============================================================================

def fig4_deramp_correction_2018(ref_arr, stable_mask, glacier_mask):
    print("  [F4] Campo de corrección del deramp3 en 2018...")
    ruta_nk = os.path.join(VARIANTS_DIR, "2018_NK.tif")
    ruta_d3 = os.path.join(VARIANTS_DIR, "2018_deramp3.tif")
    if not (os.path.exists(ruta_nk) and os.path.exists(ruta_d3)):
        print("    Faltan archivos de 2018, se omite.")
        return

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

    corr = d3 - nk
    valid = np.isfinite(corr)

    corr_stable = corr[stable_mask & valid]
    corr_glacier = corr[glacier_mask & valid]

    print(f"    Corrección media en zona estable: {np.nanmean(corr_stable):+.3f} m "
          f"(mediana {np.nanmedian(corr_stable):+.3f})")
    print(f"    Corrección media en glaciar:      {np.nanmean(corr_glacier):+.3f} m "
          f"(mediana {np.nanmedian(corr_glacier):+.3f})")
    print(f"    Rango en glaciar: P5={np.nanpercentile(corr_glacier,5):+.3f} "
          f"P95={np.nanpercentile(corr_glacier,95):+.3f}")

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    vmax = max(abs(np.nanpercentile(corr_glacier, 5)),
               abs(np.nanpercentile(corr_glacier, 95)))
    ds = MAP_DOWNSAMPLE
    corr_plot = np.where(valid & (stable_mask | glacier_mask), corr, np.nan)
    corr_ds = downsample(np.where(np.isfinite(corr_plot), corr_plot, 0), ds)
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
    plt.savefig(os.path.join(FIGURES_DIR, "F4_deramp_correction_map_2018.png"),
                dpi=130, bbox_inches="tight")
    plt.close(fig)


# ==============================================================================
# FIGURA 5: correlación corrección vs pendiente y aspecto (2018)
# ==============================================================================

def fig5_deramp_vs_slope_aspect(ref_arr, stable_mask, glacier_mask):
    print("  [F5] Correlación corrección deramp3 vs pendiente/aspecto (2018)...")
    ruta_nk = os.path.join(VARIANTS_DIR, "2018_NK.tif")
    ruta_d3 = os.path.join(VARIANTS_DIR, "2018_deramp3.tif")
    if not (os.path.exists(ruta_nk) and os.path.exists(ruta_d3)):
        return

    with rasterio.open(ruta_nk) as src:
        nk = src.read(1).astype(np.float32)
        if src.nodata is not None:
            nk[nk == src.nodata] = np.nan
    with rasterio.open(ruta_d3) as src:
        d3 = src.read(1).astype(np.float32)
        if src.nodata is not None:
            d3[d3 == src.nodata] = np.nan
    corr = d3 - nk

    ref_dem = xdem.DEM(REFERENCE_FILE)
    slope = ref_dem.slope().data
    aspect = ref_dem.aspect().data

    valid = np.isfinite(corr) & np.isfinite(slope) & np.isfinite(aspect) & glacier_mask

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
    plt.savefig(os.path.join(FIGURES_DIR, "F5_deramp_vs_slope_aspect.png"),
                dpi=130, bbox_inches="tight")
    plt.close(fig)


# ==============================================================================
# FIGURA 6 y 7: mapas e histogramas del DoD
# ==============================================================================

def fig6_7_dod(ref_transform, ref_crs):
    print("  [F6/F7] Mapas e histogramas del DoD...")
    dod_files = {}
    for year in YEARS:
        ruta = os.path.join(DOD_DIR, f"{year}_vs_{REFERENCE_YEAR}_A.tif")
        if os.path.exists(ruta):
            dod_files[year] = ruta
        else:
            ruta = os.path.join(DOD_DIR, f"{year}_vs_{REFERENCE_YEAR}_B.tif")
            if os.path.exists(ruta):
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
        dh_ds = downsample(np.where(np.isfinite(dh), dh, 0), ds)
        dh_ds = np.where(dh_ds == 0, np.nan, dh_ds)
        im = axes[i].imshow(dh_ds, cmap="RdBu_r", vmin=vmin, vmax=vmax,
                            interpolation="nearest")
        axes[i].set_title(f"DoD {year} vs {REFERENCE_YEAR}\n"
                          f"Mediana = {np.median(vals):+.2f} m")
        axes[i].axis("off")
        fig.colorbar(im, ax=axes[i], shrink=0.7, label="dH (m)")
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "F6_dod_maps.png"),
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
    plt.savefig(os.path.join(FIGURES_DIR, "F7_dod_histograms.png"),
                dpi=130, bbox_inches="tight")
    plt.close(fig)


# ==============================================================================
# FIGURA 8: hipsometría del cambio
# ==============================================================================

def fig8_hypsometry(ref_arr, glacier_mask):
    print("  [F8] Hipsometría del cambio...")
    dod_files = {}
    for year in YEARS:
        for suf in ["A", "B"]:
            ruta = os.path.join(DOD_DIR, f"{year}_vs_{REFERENCE_YEAR}_{suf}.tif")
            if os.path.exists(ruta):
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
    plt.savefig(os.path.join(FIGURES_DIR, "F8_dod_hypsometry.png"),
                dpi=130, bbox_inches="tight")
    plt.close(fig)


# ==============================================================================
# FIGURA 9: sensibilidad B vs A
# ==============================================================================

def fig9_sensitivity_B_vs_A(dod_csv_rows):
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
    plt.savefig(os.path.join(FIGURES_DIR, "F9_sensitivity_B_vs_A.png"),
                dpi=130, bbox_inches="tight")
    plt.close(fig)


# ==============================================================================
# TABLAS
# ==============================================================================

def generar_tablas():
    print("\nGenerando tablas...")

    # Copiar CSVs existentes a report/tables/
    for src, dst in [
        (DOD_CSV, "T4_dod_summary.csv"),
        (VARIANTS_CSV, "T3_coreg_step2_variants.csv"),
        (GLACIER_STABLE_CSV, "T5_glacier_vs_stable.csv"),
    ]:
        if os.path.exists(src):
            rows = leer_csv(src)
            guardar_csv(rows, os.path.join(TABLES_DIR, dst))

    # Markdown consolidado
    md_path = os.path.join(TABLES_DIR, "T6_report_main.md")
    with open(md_path, "w") as f:
        f.write("# Tablas de resultados del análisis DoD\n\n")
        f.write(f"**Referencia:** {REFERENCE_YEAR}\n\n")

        # --- T3: Variantes de co-registro ---
        f.write("## Tabla 3. Variantes de co-registro (Paso 2)\n\n")
        f.write("| Año | N_valid | NMAD_NK (m) | NMAD_deramp3 (m) | NMAD_CV (m) | NMAD_NKcv (m) | CV acepta | NMAD final (m) |\n")
        f.write("|---|---|---|---|---|---|---|---|\n")
        for r in leer_csv(os.path.join(TABLES_DIR, "T3_coreg_step2_variants.csv")):
            f.write(f"| {r['year']} | {int(r['n_valid']):,} | "
                    f"{float(r['nmad_nk']):.3f} | {float(r['nmad_deramp3']):.3f} | "
                    f"{float(r['nmad_cv']):.3f} | {float(r['nmad_nk_cv']):.3f} | "
                    f"{r['cv_acepta']} | {float(r['nmad_derampCV']):.3f} |\n")
        f.write("\n")

        # --- T4: Resumen del DoD ---
        f.write("## Tabla 4. Resumen del DoD (Paso 3)\n\n")
        f.write("| Año | Opción | Variante | N_px | dH medio (m) | dH mediana (m) | NMAD (m) | Volumen (10⁶ m³) |\n")
        f.write("|---|---|---|---|---|---|---|---|\n")
        for r in leer_csv(os.path.join(TABLES_DIR, "T4_dod_summary.csv")):
            f.write(f"| {r['year']} | {r['option']} | {r['variant']} | "
                    f"{int(r['n_pixels']):,} | {float(r['dh_mean_m']):+.3f} | "
                    f"{float(r['dh_median_m']):+.3f} | {float(r['dh_nmad_m']):.3f} | "
                    f"{float(r['volume_m3'])/1e6:+.3f} |\n")
        f.write("\n")

        # --- T5: Glaciar vs zona estable ---
        f.write("## Tabla 5. Glaciar vs zona estable\n\n")
        for r in leer_csv(os.path.join(TABLES_DIR, "T5_glacier_vs_stable.csv")):
            for k, v in r.items():
                f.write(f"- **{k}**: {v}\n")
        f.write("\n")

        # --- NUEVA SECCIÓN: CONFIANZA EN LA SEÑAL ---
        f.write("---\n\n")
        f.write("# Confianza en la señal de cambio (Paso 6)\n\n")

        t8 = leer_csv(T8_CSV)
        if t8:
            f.write("## Tabla 8. NMAD por franja de pendiente\n\n")
            f.write("| Año | Variante | Pendiente | N píxeles | Media (m) | Mediana (m) | SD (m) | NMAD (m) |\n")
            f.write("|---|---|---|---|---|---|---|---|\n")
            for r in t8:
                f.write(f"| {r['year']} | {r['variant']} | {r['slope_bin']} | "
                        f"{int(r['n_pixels']):,} | {float(r['mean_m']):+.3f} | "
                        f"{float(r['median_m']):+.3f} | {float(r['sd_m']):.3f} | "
                        f"{float(r['nmad_m']):.3f} |\n")
            f.write("\n**Interpretación:** el NMAD crece con la pendiente en los tres años, "
                    "confirmando heterocedasticidad. El 60–65% del glaciar está en la franja >30°, "
                    "así que el NMAD representativo es el de esa franja.\n\n")

        t8b = leer_csv(T8B_CSV)
        if t8b:
            f.write("## Tabla 8b. R²_aspecto y R²_Z antes/después\n\n")
            f.write("| Año | Variante | R²_asp antes | R²_asp después | R²_Z antes | R²_Z después |\n")
            f.write("|---|---|---|---|---|---|\n")
            for r in t8b:
                f.write(f"| {r['year']} | {r['variant']} | "
                        f"{float(r['r2_aspect_before']):.4f} | {float(r['r2_aspect_after']):.4f} | "
                        f"{float(r['r2_z_before']):.4f} | {float(r['r2_z_after']):.4f} |\n")
            f.write("\n**Interpretación:** en 2018, el deramp3 reduce el R²_aspecto de 0.0053 a 0.0006 "
                    "(factor ~9), confirmando que capturó un sesgo direccional real. En 2017 y 2023 "
                    "no hay cambio porque no se aplicó deramp; el R²_Z residual se propaga como incertidumbre.\n\n")

        t9 = leer_csv(T9_CSV)
        if t9:
            f.write("## Tabla 9. Variograma y N_eff\n\n")
            f.write("| Año | Variante | N píxeles | Rango (m) | N_eff ráster | N_eff glaciar | Modelo |\n")
            f.write("|---|---|---|---|---|---|---|\n")
            for r in t9:
                rango = r.get("rango_m", "")
                rango_str = f"{float(rango):.1f}" if rango not in ("", "None") else "n/a"
                n_eff_r = r.get("n_eff_raster", "")
                n_eff_r_str = f"{int(n_eff_r)}" if n_eff_r not in ("", "None") else "n/a"
                f.write(f"| {r['year']} | {r['variant']} | {int(r['n_pixels']):,} | "
                        f"{rango_str} | {n_eff_r_str} | {r['n_eff_glaciar']} | {r['modelo']} |\n")
            f.write("\n**Interpretación:** el rango de correlación (1115–2012 m) excede el tamaño del glaciar "
                    "(~430 m de lado). Eso significa que el error está correlacionado a escala regional, y no se "
                    "puede promediar espacialmente dentro del glaciar. El N_eff conservador es 1; el realista "
                    "(200) es una asunción externa basada en la literatura de DEM de dron.\n\n")

        t10 = leer_csv(T10_CSV)
        if t10:
            f.write("## Tabla 10. Propagación de error al volumen (3 escenarios de N_eff)\n\n")
            f.write("| Año | V (10⁶ m³) | N_eff ultra | σ_V ultra (%) | z ultra | σ_V cons (%) | z cons | σ_V real (%) | z real |\n")
            f.write("|---|---|---|---|---|---|---|---|---|\n")
            for r in t10:
                f.write(f"| {r['year']} | {float(r['volume_m3'])/1e6:+.3f} | "
                        f"{r['n_eff_ultra']} | {float(r['sv_real_ultra_pct']):.2f} | "
                        f"{float(r['z_real_ultra']):.1f} | "
                        f"{float(r['sv_real_cons_pct']):.2f} | {float(r['z_real_cons']):.1f} | "
                        f"{float(r['sv_real_real_pct']):.2f} | {float(r['z_real_real']):.1f} |\n")
            f.write("\n**Interpretación:** en el escenario ultraconservador (N_eff=1, correlación total), "
                    "σ_V = 4.2–7.5% del volumen y z = 13–24. En el realista (N_eff=200), σ_V = 0.3–0.5% y "
                    "z > 190. **En todos los escenarios, la señal es significativa con z > 10.**\n\n")

        t11 = leer_csv(T11_CSV)
        if t11:
            f.write("## Tabla 11. Comparación con literatura\n\n")
            f.write("| Estudio | Región | Fuente | NMAD (m) |\n")
            f.write("|---|---|---|---|\n")
            for r in t11:
                nmad_v = r.get("nmad_m", "")
                nmad_str = f"{float(nmad_v):.2f}" if nmad_v not in ("", "None") else "n/a"
                f.write(f"| {r['study']} | {r['region']} | {r['source']} | {nmad_str} |\n")
            f.write("\n**Interpretación:** el NMAD de este estudio (0.14–0.52 m) es 5–40× mejor que la "
                    "fotogrametría histórica (2.39–15.22 m), lo que es esperable por la diferencia de resolución "
                    "(dron 0.1 m vs fotogrametría 1–10 m).\n\n")

        t12 = leer_csv(T12_CSV)
        if t12:
            f.write("## Tabla 12. Control de extrapolación\n\n")
            f.write("| Año | Variante | Fracción en hull | NMAD estable (m) | Guarda (m) | Máx. extrap (m) | OK |\n")
            f.write("|---|---|---|---|---|---|---|\n")
            for r in t12:
                f.write(f"| {r['year']} | {r['variant']} | {float(r['frac_in_hull']):.3f} | "
                        f"{float(r['nmad_stable_m']):.3f} | {float(r['guarda_m']):.2f} | "
                        f"{float(r['max_extrap_glaciar_m']):.2f} | {r['extrap_ok']} |\n")
            f.write("\n**Interpretación:** los tres años pasan el control. La corrección del deramp3 en 2018 "
                    "(máx. 2.49 m) está dentro de la guarda (3.00 m). No hay extrapolación problemática.\n\n")

        t13 = leer_csv(T13_CSV)
        if t13:
            f.write("## Tabla 13. Consistencia temporal\n\n")
            f.write("| Intervalo | Δt (años) | Tasa (10⁶ m³/año) |\n")
            f.write("|---|---|---|\n")
            for r in t13:
                t = r.get("tasa_10e6_m3_per_year", "")
                t_str = f"{float(t):+.3f}" if t not in ("", "None") else "n/a"
                f.write(f"| {r['interval']} | {r['dt_years']} | {t_str} |\n")
            f.write("\n**Interpretación:** las tasas anuales son consistentes (ratio 1.08 entre intervalos). "
                    "No hay evento anómalo en 2018.\n\n")

        # --- Conclusión de confianza ---
        f.write("## Conclusión de confianza\n\n")
        f.write("La señal de cambio es distinguible del error de co-registro en todos los escenarios. "
                "Incluso en el peor caso (N_eff = 1, correlación total del error), z > 13. "
                "En el escenario realista (N_eff = 200), z > 190. "
                "El rango de correlación del error no se puede estimar con precisión con la zona estable "
                "disponible, pero es al menos 1 km, lo que justifica el N_eff = 1 como escenario conservador. "
                "La elección de la variante mixta (Opción A) está justificada por la reducción del "
                "R²_aspecto en 2018 (factor 9).\n")

    print(f"    Markdown consolidado: {os.path.abspath(md_path)}")


# ==============================================================================
# VERIFICACIÓN DE FIGURAS DEL PASO 6
# ==============================================================================

def verificar_figuras_paso6():
    print("\nVerificando figuras del Paso 6 (confianza)...")
    for fig_name in [
        "F10_nmad_vs_slope.png",
        "F11_variograma.png",
        "F12_propagacion_volumen.png",
        "F13_r2_antes_despues.png",
        "F14_flag_extrapolacion.png",
    ]:
        fig_path = os.path.join(FIGURES_DIR, fig_name)
        if os.path.exists(fig_path):
            print(f"  [OK] {fig_name}")
        else:
            print(f"  [FALTA] {fig_name} — ejecutar scripts/06-confianza.py primero")


# ==============================================================================
# EJECUCIÓN PRINCIPAL
# ==============================================================================

def main():
    print("=" * 78)
    print("PASO 4: GENERACIÓN DE FIGURAS Y TABLAS")
    print("=" * 78)

    for d in [REPORT_DIR, TABLES_DIR, FIGURES_DIR, DOD_TIF_DIR]:
        os.makedirs(d, exist_ok=True)

    # Cargar referencia y máscaras
    print("\nCargando referencia y máscaras...")
    ref_arr, ref_transform, ref_crs, ref_mask = cargar_dem_con_mascara(
        REFERENCE_FILE, STABLE_TERRAIN_PATH
    )
    _, _, _, glacier_mask = cargar_dem_con_mascara(REFERENCE_FILE, GLACIER_2017_PATH)

    # Figuras F1–F9
    print("\nGenerando figuras F1–F9...")
    fig1_polygons_overview(ref_transform, ref_crs, ref_mask, glacier_mask)
    fig2_3_residuals_nk(ref_arr, ref_mask)
    fig4_deramp_correction_2018(ref_arr, ref_mask, glacier_mask)
    fig5_deramp_vs_slope_aspect(ref_arr, ref_mask, glacier_mask)
    fig6_7_dod(ref_transform, ref_crs)
    fig8_hypsometry(ref_arr, glacier_mask)
    fig9_sensitivity_B_vs_A(leer_csv(DOD_CSV))

    # Tablas T3–T5 + T8–T13 + markdown consolidado
    generar_tablas()

    # Verificar figuras F10–F14 (generadas por el Paso 6)
    verificar_figuras_paso6()

    print("\n" + "=" * 78)
    print("PASO 4 completado.")
    print(f"Figuras: {os.path.abspath(FIGURES_DIR)}")
    print(f"Tablas:  {os.path.abspath(TABLES_DIR)}")
    print("=" * 78)


if __name__ == "__main__":
    main()