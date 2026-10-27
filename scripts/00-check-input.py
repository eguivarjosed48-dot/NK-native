"""
Paso 0: Verificación y homogeneización de cuadrícula y CRS de los DEMs.
Asegura que todos los DEMs compartan CRS, resolución, bounds y shape
con el DEM de referencia, reproyectando los que no cumplan.

Resultado: dems_alineados/dem_<year>_aligned.tif (misma cuadrícula que la referencia 2025).
"""

from __future__ import annotations

import os
from pathlib import Path

import xdem

# Las rutas absolutas de esta Mac viven en config.local.toml (ignorado por git).
# config.toml tiene los valores por defecto portables.
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nkdem.config import load_config, require_files  # noqa: E402

OUTPUT_DIR_NAME = "dems_alineados"


def main() -> None:
    cfg = load_config()
    output_dir = Path(cfg.root / OUTPUT_DIR_NAME)
    require_files(
        {
            "DEM de referencia (2025)": cfg.reference_dem,
            **{f"DEM {year}": cfg.dem(year) for year in cfg.years if year != cfg.reference_year},
        }
    )

    print("=" * 60)
    print("PASO 0: Verificando cuadrícula y sistema de referencia...")
    print("=" * 60)

    if not output_dir.exists():
        output_dir.mkdir(parents=True)

    ref_dem = xdem.DEM(cfg.reference_dem)
    ref_crs = ref_dem.crs
    ref_res = ref_dem.res
    ref_bounds = ref_dem.bounds
    ref_shape = ref_dem.shape

    processed = {year: cfg.dem(year) for year in cfg.years}

    for year in cfg.years:
        if year == cfg.reference_year:
            print(f"  [{year}] -> Referencia. Sin cambios.")
            continue

        filepath = processed[year]
        try:
            current_dem = xdem.DEM(filepath)

            crs_ok = current_dem.crs == ref_crs
            res_ok = all(
                abs(current_dem.res[i] - ref_res[i]) < 1e-6 for i in range(2)
            )
            bounds_ok = all(
                abs(current_dem.bounds[i] - ref_bounds[i]) < 1e-3 for i in range(4)
            )
            shape_ok = current_dem.shape == ref_shape

            if crs_ok and res_ok and bounds_ok and shape_ok:
                print(f"  [{year}] -> Cuadrícula compatible.")
                continue

            print(
                f"  [{year}] -> Incompatibilidad detectada "
                f"(CRS: {crs_ok}, Res: {res_ok}, Bounds: {bounds_ok}, Shape: {shape_ok})."
            )
            print("           Reproyectando para coincidir con la referencia...")

            aligned_dem = current_dem.reproject(ref=ref_dem, resampling="bilinear")

            output_path = output_dir / f"dem_{year}_aligned.tif"
            aligned_dem.save(output_path)

            processed[year] = output_path.resolve()
            print(f"           Guardado en: {output_path}")

        except Exception as error:  # noqa: BLE001
            print(f"  [{year}] -> ERROR al procesar: {error}")

    print("PASO 0 completado.")
    print("=" * 60 + "\n")
    print("Rutas finales (listas para el Paso 1):")
    for year, path in processed.items():
        print(f"  {year}: {path}")


if __name__ == "__main__":
    main()
