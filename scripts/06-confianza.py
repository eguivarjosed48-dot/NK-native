"""
Paso 6 (v6): Justificación formal de confianza en la señal.

Correcciones respecto a v5:
  - tabla_b: enmascara fuera de la zona estable antes del variograma,
    y submuestrea para acelerar. El rango de correlación ahora mide el
    error puro, no la mezcla de error + cambio glaciar.
  - tabla_c: usa el NMAD del co-registro (nmad_nk de
    coreg_variants_summary.csv), no el NMAD del DoD. Usa el área del
    polígono del glaciar (184,233 m²), no el área del DoD.
  - tabla_c: reporta tres escenarios de N_eff (ultra, cons, real).

Produce:
  T8  — NMAD y media por pendiente
  T8b — R²_aspecto y R²_Z antes/después
  T9  — variograma y N_eff (solo zona estable)
  T10 — propagación al volumen (3 escenarios de N_eff)
  T11 — comparación con literatura
  T12 — flag de extrapolación y guarda
  T13 — consistencia temporal

Figuras F10–F14.
"""

import os
import sys
import csv
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import geopandas as gpd
import rasterio
from rasterio.features import geometry_mask
from scipy.stats import linregress
from scipy.spatial import ConvexHull
from matplotlib.path import Path as MplPath
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore", message=".*partition.*MaskedArray.*")

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================

REFERENCE_YEAR = "2025"
REFERENCE_FILE = "/Users/eguivar/Documents/2-2026/dron_ortofoto_dem_v4_completo/2025_B/2025_B_DSM.tif"
STABLE_TERRAIN_PATH = "data/stable_terrain.gpkg"
GLACIER_PATH = "data/glaciar_2017.gpkg"
VARIANTS_DIR = "dems_variants"
DOD_DIR = "dod"
DOD_CSV = "dod_summary.csv"
COREG_VARIANTS_CSV = "coreg_variants_summary.csv"

YEARS = ["2017", "2018", "2023"]
VARIANT_FINAL = {"2017": "NK", "2018": "deramp3", "2023": "NK"}

TABLES_DIR = "report/tables"
FIGURES_DIR = "report/figures"

SLOPE_BINS = [0, 10, 20, 30, 90]
SLOPE_LABELS = ["0–10°", "10–20°", "20–30°", ">30°"]

SIGMA_DEM_REALISTA = 0.2
SIGMA_DEM_CONSERVADOR = 0.5

MAX_LAG_PIXELS = 2000
FALLBACK_CORR_LENGTH_M = 30.0
SUB_SAMPLE_TARGET = 1_000_000  # píxeles a los que se submuestrea el variograma

EXTRAP_GUARD_FACTOR = 2.5
EXTRAP_GUARD_MIN_M = 3.0
EXTRAP_PCT_LO = 0.5
EXTRAP_PCT_HI = 99.5


# ==============================================================================
# UTILIDADES
# ==============================================================================

def nmad(data):
    med = np.nanmedian(data)
    return 1.4826 * np.nanmedian(np.abs(data - med))


def leer_csv(ruta):
    if not os.path.exists(ruta):
        return []
    with open(ruta) as f:
        return list(csv.DictReader(f))


def guardar_csv(filas, ruta):
    if not filas:
        return
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)


def cargar_dem_y_mascara(ruta_dem, ruta_poligono):
    with rasterio.open(ruta_dem) as src:
        arr = src.read(1).astype(np.float32)
        transform = src.transform
        crs = src.crs
        if src.nodata is not None:
            arr[arr == src.nodata] = np.nan
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


def r2_lineal(x, y):
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 100:
        return np.nan, np.nan
    res = linregress(x[m], y[m])
    return res.rvalue ** 2, res.slope


def desempaquetar_n_eff(out):
    if isinstance(out, dict):
        n_eff = out.get("n_eff")
        rango_px = out.get("rango_correlacion_px")
        modelo = out.get("modelo", "esferico")
        if out.get("usando_fallback"):
            modelo = "fallback"
        return n_eff, rango_px, modelo
    if isinstance(out, tuple):
        n_eff = out[0] if len(out) > 0 else None
        rango_px = out[1] if len(out) > 1 else None
        modelo = out[2] if len(out) > 2 else "esferico"
        return n_eff, rango_px, modelo
    return out, None, "esferico"


def cargar_variante(year, variant):
    ruta = os.path.join(VARIANTS_DIR, f"{year}_{variant}.tif")
    if not os.path.exists(ruta):
        return None, None
    with rasterio.open(ruta) as src:
        arr = src.read(1).astype(np.float32)
        if src.nodata is not None:
            arr[arr == src.nodata] = np.nan
        pixel_size = abs(src.transform.a)
    return arr, pixel_size


def derivar_pendiente_aspecto_elevacion(dem, pixel_size):
    """Deriva pendiente (grados), aspecto (grados desde el norte) y elevación
    desde el propio DEM de referencia. Devuelve arrays float32 con NaN donde
    el gradiente no está definido."""
    elev = dem.copy()
    # Gradiente en unidades del DEM por metro
    gy, gx = np.gradient(np.nan_to_num(dem, nan=np.nan), pixel_size)
    # np.gradient sobre NaN propaga NaN; recuperamos la máscara original
    inval = ~np.isfinite(dem)
    gy[inval] = np.nan
    gx[inval] = np.nan
    slope_rad = np.arctan(np.hypot(gx, gy))
    slope_deg = np.degrees(slope_rad).astype(np.float32)
    # Aspecto: 0 = norte, 90 = este
    aspect_rad = np.arctan2(-gx, gy)  # convención: norte-arriba
    aspect_deg = np.degrees(aspect_rad) % 360.0
    aspect_deg = aspect_deg.astype(np.float32)
    aspect_deg[inval] = np.nan
    slope_deg[inval] = np.nan
    return slope_deg, aspect_deg, elev.astype(np.float32)


# ==============================================================================
# TABLA A — NMAD por pendiente
# ==============================================================================

def tabla_a(ref_arr, ref_mask, slope):
    print("\n[TABLA A] NMAD por franja de pendiente")
    filas = []
    for year in YEARS:
        var = VARIANT_FINAL[year]
        arr, _ = cargar_variante(year, var)
        if arr is None:
            print(f"  [{year}] falta variante {var}, se omite")
            continue
        diff = arr - ref_arr
        mask = ref_mask & np.isfinite(diff) & np.isfinite(slope)
        for lo, hi, label in zip(SLOPE_BINS[:-1], SLOPE_BINS[1:], SLOPE_LABELS):
            bm = mask & (slope >= lo) & (slope < hi)
            vals = diff[bm]
            vals = vals[np.isfinite(vals)]
            if vals.size < 100:
                continue
            filas.append({
                "year": year, "variant": var, "slope_bin": label,
                "n_pixels": int(vals.size),
                "mean_m": float(np.mean(vals)),
                "median_m": float(np.median(vals)),
                "sd_m": float(np.std(vals)),
                "nmad_m": float(nmad(vals)),
            })
            print(f"  {year} {label:<8}: n={vals.size:>10,}  "
                  f"media={np.mean(vals):+.3f}  NMAD={nmad(vals):.3f}")
    guardar_csv(filas, os.path.join(TABLES_DIR, "T8_confianza_pixel.csv"))
    return filas


# ==============================================================================
# TABLA A2 — R²_aspecto y R²_Z antes/después
# ==============================================================================

def tabla_a2_r2(ref_arr, ref_mask, aspect, elev):
    print("\n[TABLA A2] R²_aspecto y R²_Z antes/después")
    filas = []
    cos_asp = np.cos(np.radians(aspect))
    for year in YEARS:
        var = VARIANT_FINAL[year]
        nk, _ = cargar_variante(year, "NK")
        if nk is None:
            continue
        fin, _ = cargar_variante(year, var)
        if fin is None:
            fin = nk

        diff_nk = nk - ref_arr
        m = ref_mask & np.isfinite(diff_nk) & np.isfinite(aspect) & np.isfinite(elev)
        r2_asp_b, _ = r2_lineal(cos_asp[m], diff_nk[m])
        r2_z_b, _ = r2_lineal(elev[m], diff_nk[m])

        diff_fin = fin - ref_arr
        m2 = ref_mask & np.isfinite(diff_fin) & np.isfinite(aspect) & np.isfinite(elev)
        r2_asp_a, _ = r2_lineal(cos_asp[m2], diff_fin[m2])
        r2_z_a, _ = r2_lineal(elev[m2], diff_fin[m2])

        filas.append({
            "year": year, "variant": var,
            "r2_aspect_before": float(r2_asp_b),
            "r2_aspect_after": float(r2_asp_a),
            "r2_z_before": float(r2_z_b),
            "r2_z_after": float(r2_z_a),
        })
        print(f"  {year} {var}: R²_asp {r2_asp_b:.4f}→{r2_asp_a:.4f} | "
              f"R²_Z {r2_z_b:.4f}→{r2_z_a:.4f}")
    guardar_csv(filas, os.path.join(TABLES_DIR, "T8b_confianza_r2.csv"))
    return filas


# ==============================================================================
# TABLA B — variograma y N_eff (solo zona estable)
# ==============================================================================

def tabla_b(ref_arr, ref_mask, glaciar_area_m2):
    print(f"\n[TABLA B] Variograma y N_eff (max_lag={MAX_LAG_PIXELS}, solo zona estable)")
    filas = []
    for year in YEARS:
        var = VARIANT_FINAL[year]
        arr, pixel_size = cargar_variante(year, var)
        if arr is None:
            continue

        # Enmascarar fuera de la zona estable: el residual debe ser error puro
        diff = arr - ref_arr
        diff[~ref_mask] = np.nan

        n_valid_total = int(np.isfinite(diff).sum())
        if n_valid_total < 1000:
            print(f"  [{year}] pocos píxeles válidos ({n_valid_total}), se omite")
            continue

        # Submuestreo espacial para acelerar el variograma
        diff_sub = diff
        pixel_size_sub = pixel_size
        max_lag_sub = MAX_LAG_PIXELS
        step = 1
        if n_valid_total > SUB_SAMPLE_TARGET:
            step = int(np.sqrt(n_valid_total / SUB_SAMPLE_TARGET)) + 1
            diff_sub = diff[::step, ::step]
            pixel_size_sub = pixel_size * step
            max_lag_sub = max(50, MAX_LAG_PIXELS // step)
            print(f"  [{year}] submuestreo x{step}: "
                  f"{diff_sub.shape}, pixel_size={pixel_size_sub:.2f} m, "
                  f"max_lag={max_lag_sub}")

        n_eff = None
        rango_px = None
        modelo = "fallback"
        try:
            from nkdem.stats import estimar_n_eff
            out = estimar_n_eff(diff_sub, pixel_size=pixel_size_sub,
                                max_lag_pixels=max_lag_sub)
            n_eff, rango_px, modelo = desempaquetar_n_eff(out)
        except Exception as e:
            print(f"  [{year}] estimar_n_eff falló: {e}. Usando fallback.")

        n_valid = int(np.isfinite(diff).sum())
        rango_m = rango_px * pixel_size_sub if rango_px else None

        n_eff_raster = (n_eff if isinstance(n_eff, (int, float, np.integer, np.floating))
                        else None)
        if rango_m and rango_m > 0:
            n_eff_glaciar = max(1, int(glaciar_area_m2 / (rango_m ** 2)))
        elif n_eff_raster:
            n_eff_glaciar = max(1, int(n_eff_raster))
        else:
            n_eff_glaciar = max(1, int(glaciar_area_m2 / FALLBACK_CORR_LENGTH_M ** 2))
            modelo = "fallback"

        filas.append({
            "year": year, "variant": var, "n_pixels": n_valid,
            "rango_px": rango_px if rango_px is not None else "",
            "rango_m": rango_m if rango_m is not None else "",
            "n_eff_raster": int(n_eff_raster) if n_eff_raster else "",
            "n_eff_glaciar": int(n_eff_glaciar),
            "modelo": modelo,
        })
        print(f"  {year}: rango={rango_px:.1f} px ({rango_m:.1f} m), "
              f"N_eff_raster={n_eff_raster}, N_eff_glaciar={n_eff_glaciar}, "
              f"modelo={modelo}")
    guardar_csv(filas, os.path.join(TABLES_DIR, "T9_confianza_variograma.csv"))
    return filas


# ==============================================================================
# TABLA C — propagación al volumen (3 escenarios de N_eff)
# ==============================================================================

def tabla_c(tabla_b_rows, glaciar_area_m2):
    print("\n[TABLA C] Propagación al volumen (3 escenarios de N_eff)")
    dod = leer_csv(DOD_CSV)
    coreg = leer_csv(COREG_VARIANTS_CSV)
    coreg_by_year = {r["year"]: r for r in coreg}

    filas = []
    for year in YEARS:
        var = VARIANT_FINAL[year]
        opt = {"NK": "B", "deramp3": "A", "derampCV": "A"}.get(var, "B")
        row = next((r for r in dod if r["year"] == year and r["option"] == opt), None)
        if not row:
            continue
        vol = float(row["volume_m3"])

        # NMAD del co-registro (no del DoD)
        cr = coreg_by_year.get(year, {})
        if var == "deramp3":
            nmad_px = float(cr.get("nmad_deramp3", 0.5))
        else:
            nmad_px = float(cr.get("nmad_nk", 0.5))

        area = glaciar_area_m2

        s_px_r = nmad_px / np.sqrt(2)
        s_px_c = nmad_px
        s_r = np.sqrt(s_px_r**2 + 2 * SIGMA_DEM_REALISTA**2)
        s_c = np.sqrt(s_px_c**2 + 2 * SIGMA_DEM_CONSERVADOR**2)

        tb = next((r for r in tabla_b_rows if r["year"] == year), None)
        rango_m = None
        if tb and tb.get("rango_m") not in (None, "", "None"):
            try:
                rango_m = float(tb["rango_m"])
            except (ValueError, TypeError):
                rango_m = None

        n_eff_ultra = 1
        n_eff_cons = max(1, int(area / (rango_m ** 2))) if rango_m else 1
        n_eff_real = max(1, int(area / (FALLBACK_CORR_LENGTH_M ** 2)))

        def sv(s_dh, n):
            return s_dh * area / np.sqrt(n)
        def z(v, s):
            return v / s if s > 0 else np.nan
        def pct(s, v):
            return 100 * s / abs(v) if v != 0 else np.nan

        sv_r_ultra = sv(s_r, n_eff_ultra)
        sv_r_cons  = sv(s_r, n_eff_cons)
        sv_r_real  = sv(s_r, n_eff_real)
        sv_c_ultra = sv(s_c, n_eff_ultra)
        sv_c_cons  = sv(s_c, n_eff_cons)
        sv_c_real  = sv(s_c, n_eff_real)

        filas.append({
            "year": year, "variant": var,
            "volume_m3": vol, "area_m2": area, "nmad_coreg_m": nmad_px,
            "rango_m": rango_m if rango_m else "",
            "n_eff_ultra": n_eff_ultra,
            "n_eff_cons": n_eff_cons,
            "n_eff_real": n_eff_real,
            "sigma_px_real_m": float(s_r),
            "sigma_px_cons_m": float(s_c),
            "sv_real_ultra_m3": float(sv_r_ultra),
            "sv_real_ultra_pct": float(pct(sv_r_ultra, vol)),
            "z_real_ultra": float(z(vol, sv_r_ultra)),
            "sv_cons_ultra_m3": float(sv_c_ultra),
            "sv_cons_ultra_pct": float(pct(sv_c_ultra, vol)),
            "z_cons_ultra": float(z(vol, sv_c_ultra)),
            "sv_real_cons_m3": float(sv_r_cons),
            "sv_real_cons_pct": float(pct(sv_r_cons, vol)),
            "z_real_cons": float(z(vol, sv_r_cons)),
            "sv_cons_cons_m3": float(sv_c_cons),
            "sv_cons_cons_pct": float(pct(sv_c_cons, vol)),
            "z_cons_cons": float(z(vol, sv_c_cons)),
            "sv_real_real_m3": float(sv_r_real),
            "sv_real_real_pct": float(pct(sv_r_real, vol)),
            "z_real_real": float(z(vol, sv_r_real)),
            "sv_cons_real_m3": float(sv_c_real),
            "sv_cons_real_pct": float(pct(sv_c_real, vol)),
            "z_cons_real": float(z(vol, sv_c_real)),
        })

        print(f"\n  {year} ({var}): V = {vol/1e6:+.3f} × 10⁶ m³  "
              f"(NMAD_coreg = {nmad_px:.3f} m, area = {area:.0f} m²)")
        print(f"    Rango variograma: {rango_m if rango_m else 'n/a'} m")
        print(f"    N_eff: ultra={n_eff_ultra} | cons={n_eff_cons} | real={n_eff_real}")
        print(f"    σ_dH: realista={s_r:.3f} m | conservador={s_c:.3f} m")
        print(f"    σ_V realista  → ultra {pct(sv_r_ultra,vol):6.2f}% (z={z(vol,sv_r_ultra):5.1f}) "
              f"| cons {pct(sv_r_cons,vol):6.2f}% (z={z(vol,sv_r_cons):5.1f}) "
              f"| real {pct(sv_r_real,vol):6.2f}% (z={z(vol,sv_r_real):5.1f})")
        print(f"    σ_V conserv.  → ultra {pct(sv_c_ultra,vol):6.2f}% (z={z(vol,sv_c_ultra):5.1f}) "
              f"| cons {pct(sv_c_cons,vol):6.2f}% (z={z(vol,sv_c_cons):5.1f}) "
              f"| real {pct(sv_c_real,vol):6.2f}% (z={z(vol,sv_c_real):5.1f})")

    guardar_csv(filas, os.path.join(TABLES_DIR, "T10_confianza_volumen.csv"))
    return filas


# ==============================================================================
# TABLA D — literatura
# ==============================================================================

def tabla_d(tabla_c_rows):
    print("\n[TABLA D] Comparación con literatura")
    ref = [
        {"study": "Thota et al. (2026)", "region": "Ant. Peninsula",
         "source": "Fotogrametría 1989", "nmad_m": 5.83},
        {"study": "North & Barrows (2024)", "region": "Larsen B",
         "source": "Fotogrametría 1968", "nmad_m": 15.22},
        {"study": "Korsgaard et al. (2016)", "region": "Greenland",
         "source": "Fotogrametría 1978–87", "nmad_m": 8.8},
        {"study": "Fieber et al. (2018)", "region": "Northern AP",
         "source": "Fotogrametría 1956–57", "nmad_m": 7.3},
        {"study": "Llojeta (interno, 2026)", "region": "Llojeta",
         "source": "Fotogrametría 1956–97", "nmad_m": 2.39},
    ]
    for r in tabla_c_rows:
        ref.append({
            "study": "Este estudio", "region": "Glaciar Llojeta",
            "source": f"Dron 2017–2025 ({r['variant']})",
            "nmad_m": r["nmad_coreg_m"],
        })
    guardar_csv(ref, os.path.join(TABLES_DIR, "T11_confianza_literatura.csv"))
    print(f"  {len(ref)} entradas (5 literatura + {len(tabla_c_rows)} propias)")
    return ref


# ==============================================================================
# TABLA E — flag de extrapolación y guarda
# ==============================================================================

def tabla_e(ref_arr, ref_mask, glaciar_mask, elev):
    print("\n[TABLA E] Flag de extrapolación y guarda")
    filas = []

    sy, sx = np.nonzero(ref_mask)
    if sy.size == 0:
        return []
    rng = np.random.default_rng(42)
    if sy.size > 200_000:
        idx = rng.choice(sy.size, 200_000, replace=False)
        sy_s, sx_s = sy[idx], sx[idx]
    else:
        sy_s, sx_s = sy, sx
    try:
        hull = ConvexHull(np.column_stack([sx_s, sy_s]))
        hull_v = np.column_stack([sx_s, sy_s])[hull.vertices]
        hull_path = MplPath(hull_v)
    except Exception as e:
        print(f"  hull falló: {e}. Se omite Tabla E.")
        return []

    elev_stable = elev[ref_mask]
    elev_lo = float(np.nanpercentile(elev_stable, EXTRAP_PCT_LO))
    elev_hi = float(np.nanpercentile(elev_stable, EXTRAP_PCT_HI))

    for year in YEARS:
        var = VARIANT_FINAL[year]
        arr, _ = cargar_variante(year, var)
        nk, _ = cargar_variante(year, "NK")
        if arr is None or nk is None:
            continue
        corr = arr - nk

        corr_stable = corr[ref_mask]
        corr_stable = corr_stable[np.isfinite(corr_stable)]
        if corr_stable.size == 0:
            continue
        nmad_stable = nmad(corr_stable)
        guarda = max(EXTRAP_GUARD_MIN_M, EXTRAP_GUARD_FACTOR * nmad_stable)

        gy, gx = np.nonzero(glaciar_mask)
        if gy.size == 0:
            continue
        corr_g_full = corr[glaciar_mask]
        valid_g = np.isfinite(corr_g_full)
        if valid_g.sum() == 0:
            continue

        inside = hull_path.contains_points(np.column_stack([gx, gy]))
        elev_g = elev[glaciar_mask]
        inside_elev = (elev_g >= elev_lo) & (elev_g <= elev_hi)

        inside_valid = inside & valid_g
        inside_elev_valid = inside_elev & valid_g
        in_support = inside_valid & inside_elev_valid
        extrap_mask = valid_g & ~in_support

        corr_g = corr_g_full[valid_g]
        n_valid_glacier = int(valid_g.sum())
        n_in_hull = int(in_support.sum())

        max_extrap = 0.0
        if extrap_mask.any():
            extrap_idx = extrap_mask[valid_g]
            if extrap_idx.any():
                max_extrap = float(np.nanmax(np.abs(corr_g[extrap_idx])))

        filas.append({
            "year": year, "variant": var,
            "n_stable": int(ref_mask.sum()),
            "n_glacier": n_valid_glacier,
            "n_glacier_in_hull": n_in_hull,
            "frac_in_hull": float(n_in_hull / max(1, n_valid_glacier)),
            "nmad_stable_m": float(nmad_stable),
            "guarda_m": float(guarda),
            "max_extrap_glaciar_m": max_extrap,
            "extrap_ok": bool(max_extrap <= guarda),
        })
        print(f"  {year} ({var}): frac_in_hull={n_in_hull/max(1,n_valid_glacier):.3f}, "
              f"guarda={guarda:.2f} m, max_extrap={max_extrap:.2f} m, "
              f"ok={max_extrap <= guarda}")
    guardar_csv(filas, os.path.join(TABLES_DIR, "T12_confianza_extrap.csv"))
    return filas


# ==============================================================================
# TABLA F — consistencia temporal
# ==============================================================================

def tabla_f(tabla_c_rows):
    print("\n[TABLA F] Consistencia temporal (tasas anuales)")
    if len(tabla_c_rows) < 3:
        return []
    by_year = {r["year"]: r for r in tabla_c_rows}

    def tasa(year_a, year_b):
        if year_a not in by_year or year_b not in by_year:
            return np.nan
        va = by_year[year_a]["volume_m3"]
        vb = by_year[year_b]["volume_m3"]
        dt = int(year_b) - int(year_a)
        return (va - vb) / 1e6 / dt

    filas = []
    for a, b in [("2017", "2018"), ("2018", "2023"), ("2017", "2023")]:
        t = tasa(a, b)
        filas.append({
            "interval": f"{a}–{b}",
            "dt_years": int(b) - int(a),
            "tasa_10e6_m3_per_year": float(t) if not np.isnan(t) else "",
        })
        if not np.isnan(t):
            print(f"  {a}–{b}: {t:+.3f}×10⁶ m³/año")
        else:
            print(f"  {a}–{b}: n/a")

    if (len(filas) >= 2
            and filas[0]["tasa_10e6_m3_per_year"] != ""
            and filas[1]["tasa_10e6_m3_per_year"] != ""):
        t1 = filas[0]["tasa_10e6_m3_per_year"]
        t2 = filas[1]["tasa_10e6_m3_per_year"]
        if t2 != 0:
            ratio = abs(t1 / t2)
            print(f"  Ratio |tasa 2017-18 / tasa 2018-23| = {ratio:.2f}")
            if ratio > 2 or ratio < 0.5:
                print("  ADVERTENCIA: inconsistencia temporal (>×2 entre intervalos)")

    guardar_csv(filas, os.path.join(TABLES_DIR, "T13_confianza_temporal.csv"))
    return filas


# ==============================================================================
# FIGURAS
# ==============================================================================

def fig_nmad_slope(tabla_a_rows):
    fig, ax = plt.subplots(figsize=(8, 5))
    for year in YEARS:
        rows = [r for r in tabla_a_rows if r["year"] == year]
        if not rows:
            continue
        x = [SLOPE_LABELS.index(r["slope_bin"]) for r in rows]
        y = [r["nmad_m"] for r in rows]
        ax.plot(x, y, "o-", label=f"{year} ({VARIANT_FINAL[year]})")
    ax.set_xticks(range(len(SLOPE_LABELS)))
    ax.set_xticklabels(SLOPE_LABELS)
    ax.set_xlabel("Pendiente")
    ax.set_ylabel("NMAD (m)")
    ax.set_title("NMAD del residual por franja de pendiente")
    ax.legend(); ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "F10_nmad_vs_slope.png"), dpi=130)
    plt.close(fig)


def fig_r2(tabla_a2_rows):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    years = [r["year"] for r in tabla_a2_rows]
    x = np.arange(len(years))
    w = 0.35
    for i, metric in enumerate(["r2_aspect", "r2_z"]):
        ax = axes[i]
        before = [r[f"{metric}_before"] for r in tabla_a2_rows]
        after = [r[f"{metric}_after"] for r in tabla_a2_rows]
        ax.bar(x - w/2, before, w, label="antes", color="C0")
        ax.bar(x + w/2, after, w, label="después", color="C1")
        ax.set_xticks(x); ax.set_xticklabels(years)
        ax.set_ylabel(f"R²_{'aspecto' if metric == 'r2_aspect' else 'Z'}")
        ax.set_title("R² aspecto" if metric == "r2_aspect" else "R² Z")
        ax.legend(); ax.grid(alpha=0.3, axis="y")
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "F13_r2_antes_despues.png"), dpi=130)
    plt.close(fig)


def fig_variograma(tabla_b_rows):
    fig, ax = plt.subplots(figsize=(8, 5))
    xs, ys, labels = [], [], []
    for i, r in enumerate(tabla_b_rows):
        if r["rango_m"] != "":
            xs.append(float(r["rango_m"]))
            ys.append(i)
            labels.append(f"{r['year']} ({VARIANT_FINAL[r['year']]})")
    if not xs:
        plt.close(fig)
        return
    ax.barh(ys, xs, color=["C0", "C1", "C2"][:len(xs)])
    ax.set_yticks(ys); ax.set_yticklabels(labels)
    ax.set_xlabel("Rango de correlación (m)")
    ax.set_title("Rango de correlación del residual en zona estable")
    ax.grid(alpha=0.3, axis="x")
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "F11_variograma.png"), dpi=130)
    plt.close(fig)


def fig_propagacion(tabla_c_rows):
    fig, ax = plt.subplots(figsize=(11, 6))
    x = np.arange(len(tabla_c_rows))
    v = [r["volume_m3"] / 1e6 for r in tabla_c_rows]
    sv_ultra = [r["sv_real_ultra_m3"] / 1e6 for r in tabla_c_rows]
    sv_cons  = [r["sv_real_cons_m3"] / 1e6 for r in tabla_c_rows]
    sv_real  = [r["sv_real_real_m3"] / 1e6 for r in tabla_c_rows]

    w = 0.25
    ax.bar(x, v, w * 2.5, color="C0", alpha=0.7, label="Volumen")
    ax.errorbar(x - w, v, yerr=sv_ultra, fmt="none", ecolor="C3", capsize=6,
                elinewidth=2.5, label="σ ultra (N_eff=1)")
    ax.errorbar(x, v, yerr=sv_cons, fmt="none", ecolor="C1", capsize=5,
                elinewidth=2, label="σ cons (variograma)")
    ax.errorbar(x + w, v, yerr=sv_real, fmt="none", ecolor="C2", capsize=4,
                elinewidth=2, label="σ real (N_eff=200)")

    for i, r in enumerate(tabla_c_rows):
        ax.text(x[i], v[i] * 1.02,
                f"z ultra={r['z_real_ultra']:.0f}\nz real={r['z_real_real']:.0f}",
                ha="center", va="bottom", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels([f"{r['year']}\n({r['variant']})" for r in tabla_c_rows])
    ax.set_ylabel("Volumen (10⁶ m³)")
    ax.set_title("Propagación de error al volumen — 3 escenarios de N_eff")
    ax.legend(fontsize=9, loc="upper right")
    ax.grid(alpha=0.3, axis="y")
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "F12_propagacion_volumen.png"), dpi=130)
    plt.close(fig)


def fig_extrapolacion(tabla_e_rows):
    """F14: fracción de píxeles del glaciar dentro del hull de la zona estable,
    con la guarda y el max_extrap superpuestos."""
    fig, ax1 = plt.subplots(figsize=(9, 5))
    x = np.arange(len(tabla_e_rows))
    labels = [f"{r['year']}\n({r['variant']})" for r in tabla_e_rows]
    frac = [r["frac_in_hull"] for r in tabla_e_rows]
    guarda = [r["guarda_m"] for r in tabla_e_rows]
    max_ext = [r["max_extrap_glaciar_m"] for r in tabla_e_rows]

    ax1.bar(x, frac, 0.5, color="C0", alpha=0.7, label="Fracción en hull")
    ax1.set_ylim(0, 1.05)
    ax1.set_ylabel("Fracción de píxeles del glaciar dentro del hull")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels)
    ax1.grid(alpha=0.3, axis="y")

    ax2 = ax1.twinx()
    ax2.plot(x, guarda, "s--", color="C1", label="Guarda (m)")
    ax2.plot(x, max_ext, "o-", color="C3", label="max_extrap (m)")
    ax2.set_ylabel("Altura (m)")
    for i, r in enumerate(tabla_e_rows):
        mark = "OK" if r["extrap_ok"] else "FALLA"
        ax2.annotate(mark, (x[i], max_ext[i]),
                     textcoords="offset points", xytext=(0, 8),
                     ha="center", fontsize=8,
                     color="green" if r["extrap_ok"] else "red")

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, fontsize=9, loc="lower right")
    ax1.set_title("Control de extrapolación del deramp (hull + guarda)")
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "F14_flag_extrapolacion.png"), dpi=130)
    plt.close(fig)


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    os.makedirs(TABLES_DIR, exist_ok=True)
    os.makedirs(FIGURES_DIR, exist_ok=True)

    print("=" * 70)
    print("Paso 6 — Justificación formal de confianza (v6)")
    print("=" * 70)

    # ------------------------------------------------------------------
    # Cargar DEM de referencia y máscaras
    # ------------------------------------------------------------------
    print(f"\nCargando DEM de referencia: {REFERENCE_FILE}")
    ref_arr, transform, crs, ref_mask = cargar_dem_y_mascara(
        REFERENCE_FILE, STABLE_TERRAIN_PATH
    )
    pixel_size = abs(transform.a)
    print(f"  shape={ref_arr.shape}, pixel_size={pixel_size:.3f} m, CRS={crs}")
    print(f"  píxeles válidos en zona estable: {int(ref_mask.sum()):,}")

    # Máscara del glaciar (mismo grid que la referencia)
    with rasterio.open(REFERENCE_FILE) as src:
        gdf_glac = gpd.read_file(GLACIER_PATH)
        if gdf_glac.crs is None:
            raise ValueError(f"El polígono '{GLACIER_PATH}' no tiene CRS.")
        if gdf_glac.crs != src.crs:
            gdf_glac = gdf_glac.to_crs(src.crs)
        out_g = geometry_mask(
            gdf_glac.geometry, out_shape=ref_arr.shape,
            transform=src.transform, invert=False
        )
        glaciar_mask = (~out_g) & np.isfinite(ref_arr)

    # Área del polígono del glaciar (D4), en su CRS proyectado
    gdf_glac_proj = gdf_glac.to_crs("EPSG:32719")
    glaciar_area_m2 = float(gdf_glac_proj.geometry.area.sum())
    print(f"  área del polígono del glaciar: {glaciar_area_m2:,.0f} m²")

    # ------------------------------------------------------------------
    # Derivar pendiente, aspecto y elevación del DEM de referencia
    # ------------------------------------------------------------------
    print("\nDerivando pendiente, aspecto y elevación del DEM de referencia...")
    slope, aspect, elev = derivar_pendiente_aspecto_elevacion(ref_arr, pixel_size)
    print(f"  slope: rango [{np.nanmin(slope):.1f}, {np.nanmax(slope):.1f}]°")
    print(f"  aspect: rango [{np.nanmin(aspect):.1f}, {np.nanmax(aspect):.1f}]°")

    # ------------------------------------------------------------------
    # Tablas
    # ------------------------------------------------------------------
    tabla_a_rows  = tabla_a(ref_arr, ref_mask, slope)
    tabla_a2_rows = tabla_a2_r2(ref_arr, ref_mask, aspect, elev)
    tabla_b_rows  = tabla_b(ref_arr, ref_mask, glaciar_area_m2)
    tabla_c_rows  = tabla_c(tabla_b_rows, glaciar_area_m2)
    tabla_d_rows  = tabla_d(tabla_c_rows)
    tabla_e_rows  = tabla_e(ref_arr, ref_mask, glaciar_mask, elev)
    tabla_f_rows  = tabla_f(tabla_c_rows)

    # ------------------------------------------------------------------
    # Figuras
    # ------------------------------------------------------------------
    print("\nGenerando figuras F10–F14...")
    fig_nmad_slope(tabla_a_rows)
    fig_r2(tabla_a2_rows)
    fig_variograma(tabla_b_rows)
    fig_propagacion(tabla_c_rows)
    fig_extrapolacion(tabla_e_rows)
    print("  Figuras guardadas en", FIGURES_DIR)

    # ------------------------------------------------------------------
    # Resumen final y verificación de coherencia (N2)
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("RESUMEN Y VERIFICACIÓN DE COHERENCIA")
    print("=" * 70)

    ok_global = True

    # Check 1: rango del variograma entre 20 y 100 m
    for r in tabla_b_rows:
        rm = r.get("rango_m")
        if rm not in (None, "", "None"):
            try:
                rmv = float(rm)
            except (ValueError, TypeError):
                continue
            if 20 <= rmv <= 100:
                print(f"  [OK]   {r['year']}: rango={rmv:.1f} m (20–100 m)")
            else:
                print(f"  [WARN] {r['year']}: rango={rmv:.1f} m fuera de [20, 100]")
                ok_global = False
        else:
            print(f"  [WARN] {r['year']}: rango no disponible (fallback)")

    # Check 2: N_eff_glaciar entre 10 y 200
    for r in tabla_b_rows:
        n = r.get("n_eff_glaciar")
        if isinstance(n, (int, float)) and 10 <= n <= 200:
            print(f"  [OK]   {r['year']}: N_eff_glaciar={int(n)} (10–200)")
        else:
            print(f"  [WARN] {r['year']}: N_eff_glaciar={n} fuera de [10, 200]")
            ok_global = False

    # Check 3 y 4: σ_V ultraconservador 3–9% y z_ultra > 10
    for r in tabla_c_rows:
        p = r.get("sv_real_ultra_pct")
        z = r.get("z_real_ultra")
        if p is not None and 3 <= p <= 9:
            print(f"  [OK]   {r['year']}: σ_V ultra={p:.2f}% (3–9%)")
        else:
            print(f"  [WARN] {r['year']}: σ_V ultra={p}% fuera de [3, 9]")
            ok_global = False
        if z is not None and z > 10:
            print(f"  [OK]   {r['year']}: z_ultra={z:.1f} (> 10)")
        else:
            print(f"  [WARN] {r['year']}: z_ultra={z} ≤ 10")
            ok_global = False

    print("\n" + ("TODO OK" if ok_global else "HAY WARNINGS: revisar antes de redactar MARCO_CONFIANZA.md"))
    print("=" * 70)


if __name__ == "__main__":
    main()