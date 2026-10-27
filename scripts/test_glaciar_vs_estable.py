"""
Chequeo: relación espacial entre el polígono del glaciar 2017 y la zona
de terreno estable usada para el co-registro.

Objetivo: determinar si el deramp3 aplicado en 2018 está extrapolando
el polinomio hacia el glaciar, lo cual podría introducir un sesgo espurio.

Salidas:
  - Consola: métricas de distancia, cobertura, hull.
  - PNG: mapa de glaciar, zona estable y convex hull.
  - CSV: test_outputs/test_glaciar_vs_estable.csv
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
import geopandas as gpd
import rasterio
from rasterio.features import geometry_mask
from scipy.spatial import ConvexHull, cKDTree
from matplotlib.path import Path as MatPath
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nkdem.config import load_config, require_files  # noqa: E402
from nkdem.io import write_csv  # noqa: E402
from nkdem.raster import load_dem_with_mask  # noqa: E402

OUTPUT_DIR_NAME = "test_outputs"
CSV_OUTPUT_NAME = "test_glaciar_vs_estable.csv"
PNG_OUTPUT_NAME = "test_glaciar_vs_estable.png"

MAX_GLACIER_SAMPLES = 200_000
MAX_STABLE_SAMPLES = 500_000
RANDOM_SEED = 42


def muestrear(mask, max_samples, seed):
    rows, cols = np.nonzero(mask)
    if rows.size == 0:
        return rows, cols
    if rows.size > max_samples:
        rng = np.random.default_rng(seed)
        idx = rng.choice(rows.size, size=max_samples, replace=False)
        rows, cols = rows[idx], cols[idx]
    return rows, cols


def a_xy(transform, rows, cols):
    x = transform.c + cols * transform.a + rows * transform.b
    y = transform.f + cols * transform.d + rows * transform.e
    return x, y


def main() -> None:
    cfg = load_config()
    output_dir = Path(cfg.root / OUTPUT_DIR_NAME)
    output_dir.mkdir(parents=True, exist_ok=True)

    require_files(
        {
            "DEM de referencia": cfg.reference_dem,
            "Polígono terreno estable": cfg.stable_terrain,
            "Polígono glaciar 2017": cfg.glacier_polygon,
        }
    )

    print("=" * 78)
    print("CHEQUEO: glaciar 2017 vs zona de terreno estable")
    print("=" * 78)

    print("\nCargando máscaras...")
    _, transform, crs, stable_mask = load_dem_with_mask(
        cfg.reference_dem, cfg.stable_terrain
    )
    _, _, _, glacier_mask = load_dem_with_mask(
        cfg.reference_dem, cfg.glacier_polygon
    )

    pixel_size_x = abs(transform.a)
    pixel_size_y = abs(transform.e)
    pixel_area = pixel_size_x * pixel_size_y
    print(f"  CRS: {crs}")
    print(f"  Pixel size: {pixel_size_x:.3f} m × {pixel_size_y:.3f} m")
    print(f"  Píxeles zona estable: {int(stable_mask.sum()):,} "
          f"({int(stable_mask.sum())*pixel_area/1e6:.3f} km²)")
    print(f"  Píxeles glaciar:      {int(glacier_mask.sum()):,} "
          f"({int(glacier_mask.sum())*pixel_area/1e6:.3f} km²)")

    if stable_mask.sum() == 0:
        raise ValueError("La máscara de zona estable está vacía.")
    if glacier_mask.sum() == 0:
        raise ValueError("La máscara del glaciar está vacía.")

    print(
        f"\nMuestreando para eficiencia (máx {MAX_GLACIER_SAMPLES:,} glaciar, "
        f"{MAX_STABLE_SAMPLES:,} estable)..."
    )
    gy, gx = muestrear(glacier_mask, MAX_GLACIER_SAMPLES, RANDOM_SEED)
    sy, sx = muestrear(stable_mask, MAX_STABLE_SAMPLES, RANDOM_SEED)
    print(f"  Muestras glaciar: {gy.size:,} | Muestras estable: {sy.size:,}")

    gx_xy, gy_xy = a_xy(transform, gy, gx)
    sx_xy, sy_xy = a_xy(transform, sy, sx)

    print("\nCalculando convex hull de la zona estable...")
    stable_points = np.column_stack([sx_xy, sy_xy])
    try:
        hull = ConvexHull(stable_points)
        hull_vertices = stable_points[hull.vertices]
        hull_path = MatPath(hull_vertices)
        hull_area_m2 = hull.volume  # en 2D, ConvexHull.volume es el área
        print(f"  Vértices del hull: {len(hull_vertices)}")
        print(f"  Área del hull: {hull_area_m2/1e6:.3f} km²")
    except Exception as error:  # noqa: BLE001
        print(f"  ERROR calculando hull: {error}")
        hull_path = None
        hull_area_m2 = np.nan

    print("\nCobertura del glaciar por el convex hull:")
    glacier_points = np.column_stack([gx_xy, gy_xy])
    if hull_path is not None:
        inside = hull_path.contains_points(glacier_points)
        frac_inside = float(inside.mean())
        n_inside = int(inside.sum())
        print(f"  Píxeles del glaciar dentro del hull: {n_inside:,} / "
              f"{glacier_points.shape[0]:,} ({100*frac_inside:.1f}%)")

        centroid = (gx_xy.mean(), gy_xy.mean())
        centroide_dentro = bool(hull_path.contains_point(centroid))
        print(f"  Centroide del glaciar dentro del hull: {centroide_dentro}")
    else:
        frac_inside = np.nan
        n_inside = 0
        centroide_dentro = False

    print("\nDistancias glaciar–zona estable (con muestreo):")
    tree = cKDTree(stable_points)
    d_min_per_glacier, _ = tree.query(glacier_points)
    d_min = float(d_min_per_glacier.min())
    d_p5 = float(np.percentile(d_min_per_glacier, 5))
    d_p25 = float(np.percentile(d_min_per_glacier, 25))
    d_median = float(np.median(d_min_per_glacier))
    d_p75 = float(np.percentile(d_min_per_glacier, 75))
    d_p95 = float(np.percentile(d_min_per_glacier, 95))
    d_max = float(d_min_per_glacier.max())

    print(f"  Mínima:   {d_min:.1f} m")
    print(f"  P5:       {d_p5:.1f} m")
    print(f"  P25:      {d_p25:.1f} m")
    print(f"  Mediana:  {d_median:.1f} m")
    print(f"  P75:      {d_p75:.1f} m")
    print(f"  P95:      {d_p95:.1f} m")
    print(f"  Máxima:   {d_max:.1f} m")

    print("\n" + "=" * 78)
    print("INTERPRETACIÓN")
    print("=" * 78)

    if hull_path is None:
        print("  No se pudo evaluar el hull.")
    else:
        if centroide_dentro and frac_inside > 0.9:
            print("  El glaciar está MAYORITARIAMENTE dentro del hull de la zona estable.")
            print("  La extrapolación del deramp3 al glaciar es DEFENDIBLE.")
        elif centroide_dentro and frac_inside > 0.5:
            print("  El glaciar está PARCIALMENTE dentro del hull.")
            print("  La extrapolación del deramp3 es ARRIESGADA en la parte fuera del hull.")
        else:
            print("  El glaciar está MAYORITARIAMENTE fuera del hull de la zona estable.")
            print("  La extrapolación del deramp3 al glaciar NO es fiable.")
            print("  Recomendación: usar NK (Opción B) para el DoD principal.")

    if d_median > 500:
        print(f"\n  La distancia mediana ({d_median:.0f} m) es grande (>500 m).")
        print("  El polinomio del deramp3 estaría extrapolando lejos de sus datos de ajuste.")
    elif d_median > 200:
        print(f"\n  La distancia mediana ({d_median:.0f} m) es moderada (200–500 m).")
        print("  La extrapolación es posible pero debe vigilarse.")
    else:
        print(f"\n  La distancia mediana ({d_median:.0f} m) es pequeña (<200 m).")
        print("  La extrapolación del polinomio es razonablemente segura.")

    fila = {
        "stable_pixels": int(stable_mask.sum()),
        "glacier_pixels": int(glacier_mask.sum()),
        "stable_area_km2": int(stable_mask.sum()) * pixel_area / 1e6,
        "glacier_area_km2": int(glacier_mask.sum()) * pixel_area / 1e6,
        "hull_area_km2": hull_area_m2 / 1e6 if not np.isnan(hull_area_m2) else np.nan,
        "glacier_frac_inside_hull": frac_inside,
        "glacier_centroid_inside_hull": centroide_dentro,
        "dist_min_m": d_min,
        "dist_p5_m": d_p5,
        "dist_p25_m": d_p25,
        "dist_median_m": d_median,
        "dist_p75_m": d_p75,
        "dist_p95_m": d_p95,
        "dist_max_m": d_max,
    }
    csv_path = Path(cfg.root / CSV_OUTPUT_NAME)
    write_csv([fila], csv_path)
    print(f"\nCSV guardado: {csv_path.resolve()}")

    print("\nGenerando figura de inspección...")
    fig, ax = plt.subplots(1, 1, figsize=(12, 10))

    with rasterio.open(cfg.reference_dem) as src:
        b = src.bounds
    ax.set_xlim(b.left, b.right)
    ax.set_ylim(b.bottom, b.top)

    ax.scatter(sx_xy, sy_xy, s=0.2, c="green", alpha=0.3, label="Zona estable")

    if hull_path is not None:
        hv = np.vstack([hull_vertices, hull_vertices[0]])
        ax.plot(hv[:, 0], hv[:, 1], "g--", lw=2, label="Convex hull estable")

    ax.scatter(gx_xy, gy_xy, s=0.5, c="red", alpha=0.5, label="Glaciar 2017")

    ax.plot(gx_xy.mean(), gy_xy.mean(), "r*", ms=18, markeredgecolor="k",
            label="Centroide glaciar")

    ax.set_aspect("equal")
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_title(f"Glaciar 2017 vs zona estable\n"
                 f"Dentro del hull: {100*frac_inside:.1f}% | "
                 f"d_mediana = {d_median:.0f} m")
    ax.legend(loc="upper right", markerscale=10, fontsize=9)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    png_path = Path(cfg.root / PNG_OUTPUT_NAME)
    plt.savefig(png_path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"Figura guardada: {png_path.resolve()}")

    print("\n" + "=" * 78)
    print("Chequeo completado.")
    print("=" * 78)


if __name__ == "__main__":
    main()
