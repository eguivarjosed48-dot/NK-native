"""
Paso 1: Co-registro con Nuth y Kääb (NK) de los DEMs alineados
respecto al DEM de referencia (2025), usando un polígono de terreno
estable como máscara. Calcula Mediana y NMAD antes/después del ajuste
y reporta los shifts en X, Y, Z.

Salidas:
  - dems_nk/dem_<year>_nk.tif
  - coreg_nk_summary.csv (resumen por año)
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import geometry_mask
import xdem

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nkdem.config import load_config, require_files  # noqa: E402
from nkdem.io import write_csv  # noqa: E402
from nkdem.raster import read_raster  # noqa: E402
from nkdem.stats import difference_stats  # noqa: E402

OUTPUT_DIR_NAME = "dems_nk"
CSV_OUTPUT_NAME = "coreg_nk_summary.csv"


def nmad(values: np.ndarray) -> float:
    from nkdem.stats import nmad as _nmad

    return _nmad(values)


def load_dem_and_mask(
    dem_path: str | Path, polygon_path: str | Path
) -> tuple[xdem.DEM, np.ndarray]:
    array, transform, crs, nodata = read_raster(dem_path)
    if nodata is not None:
        array[array == nodata] = np.nan

    gdf = gpd.read_file(polygon_path)
    if gdf.crs is None:
        raise ValueError(f"El polígono '{polygon_path}' no tiene CRS definido.")
    if gdf.crs != crs:
        gdf = gdf.to_crs(crs)

    outside = geometry_mask(
        gdf.geometry, out_shape=array.shape, transform=transform, invert=False
    )
    stable_mask = (~outside) & np.isfinite(array)

    dem = xdem.DEM(str(dem_path))
    return dem, stable_mask


def evaluate_difference(dem_a, dem_b, stable_mask):
    return difference_stats(dem_a.data - dem_b.data, stable_mask)


def main() -> None:
    cfg = load_config()
    output_dir = Path(cfg.root / OUTPUT_DIR_NAME)
    output_dir.mkdir(parents=True, exist_ok=True)

    require_files(
        {
            "DEM de referencia": cfg.reference_dem,
            "Polígono terreno estable": cfg.stable_terrain,
            **{f"DEM alineado {year}": cfg.aligned_dem(year) for year in cfg.years if year != cfg.reference_year},
        }
    )

    print("=" * 72)
    print("PASO 1: CO-REGISTRO NUTH & KÄÄB")
    print(f"Referencia: {cfg.reference_year}")
    print("=" * 72)

    print(f"\nCargando referencia {cfg.reference_year}...")
    ref_dem, ref_stable_mask = load_dem_and_mask(
        cfg.reference_dem, cfg.stable_terrain
    )
    print(f"  Píxeles válidos en zona estable: {int(ref_stable_mask.sum()):,}")

    resultados = []

    for year in [y for y in cfg.years if y != cfg.reference_year]:
        path = cfg.aligned_dem(year)
        print(f"\n--- DEM {year} ---")
        try:
            dem, dem_stable_mask = load_dem_and_mask(path, cfg.stable_terrain)
            stable_mask = ref_stable_mask & dem_stable_mask
            n_valid = int(stable_mask.sum())
            print(f"  Píxeles válidos en zona estable común: {n_valid:,}")

            if n_valid < 1000:
                print(
                    "  ADVERTENCIA: muy pocos píxeles válidos. "
                    "Revisa solape del polígono con este DEM."
                )

            med_before, nmad_before, _ = evaluate_difference(dem, ref_dem, stable_mask)
            print(f"  [Antes NK]   Mediana: {med_before:+.3f} m | NMAD: {nmad_before:.3f} m")

            nk = xdem.coreg.NuthKaab(subsample=cfg.nk_subsample if hasattr(cfg, "nk_subsample") else 0.2)
            nk.fit(ref_dem, dem, inlier_mask=stable_mask)

            meta_out = nk.meta.get("outputs", {}).get("affine", {})
            shift_x = meta_out.get("shift_x", np.nan)
            shift_y = meta_out.get("shift_y", np.nan)
            shift_z = meta_out.get("shift_z", np.nan)

            dem_nk = nk.apply(dem)

            med_after, nmad_after, _ = evaluate_difference(dem_nk, ref_dem, stable_mask)
            print(f"  [Después NK] Mediana: {med_after:+.3f} m | NMAD: {nmad_after:.3f} m")
            print(f"  Shifts: X={shift_x:+.3f} m | Y={shift_y:+.3f} m | Z={shift_z:+.3f} m")

            out_path = output_dir / f"dem_{year}_nk.tif"
            dem_nk.to_file(str(out_path))
            print(f"  Guardado: {out_path}")

            resultados.append(
                {
                    "year": year,
                    "n_valid": n_valid,
                    "med_before": med_before,
                    "nmad_before": nmad_before,
                    "shift_x": shift_x,
                    "shift_y": shift_y,
                    "shift_z": shift_z,
                    "med_after": med_after,
                    "nmad_after": nmad_after,
                    "output": str(out_path.resolve()),
                }
            )

        except Exception as error:  # noqa: BLE001
            print(f"  ERROR procesando {year}: {error}")

    print("\n" + "=" * 72)
    print("RESUMEN PASO 1 (NUTH & KÄÄB)")
    print("=" * 72)
    header = (f"{'Year':<6} {'N_valid':>9} {'Med_bef':>9} {'NMAD_bef':>9} "
              f"{'dX':>8} {'dY':>8} {'dZ':>8} {'Med_aft':>9} {'NMAD_aft':>9}")
    print(header)
    print("-" * len(header))
    for r in resultados:
        print(
            f"{r['year']:<6} {r['n_valid']:>9,} "
            f"{r['med_before']:>+9.3f} {r['nmad_before']:>9.3f} "
            f"{r['shift_x']:>+8.3f} {r['shift_y']:>+8.3f} {r['shift_z']:>+8.3f} "
            f"{r['med_after']:>+9.3f} {r['nmad_after']:>9.3f}"
        )
    print("=" * 72)

    csv_path = Path(cfg.root / CSV_OUTPUT_NAME)
    if resultados:
        write_csv(resultados, csv_path)
        print(f"CSV guardado: {csv_path.resolve()}")


if __name__ == "__main__":
    main()
