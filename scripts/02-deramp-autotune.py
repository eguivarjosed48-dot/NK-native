"""
Paso 2: Deramp con auto-tune.
Sobre los DEMs ya co-registrados con Nuth & Kääb (dems_nk/), prueba
órdenes de polinomio [1, 2, 3] y selecciona el que minimice el NMAD
en la zona de terreno estable. Si ningún orden mejora el NMAD respecto
al DEM de NK, se rechaza el deramp y se conserva el DEM de NK.

Salidas: dems_deramped/dem_<year>_final.tif o dem_<year>_deramp<N>.tif
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import warnings

import numpy as np
import xdem

warnings.filterwarnings("ignore", message=".*partition.*MaskedArray.*")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nkdem.config import load_config, require_files  # noqa: E402
from nkdem.io import write_csv  # noqa: E402
from nkdem.raster import load_dem_with_mask  # noqa: E402
from nkdem.stats import difference_stats  # noqa: E402

OUTPUT_DIR_NAME = "dems_deramped"
CSV_OUTPUT_NAME = "deramp_autotune_summary.csv"

POLY_ORDERS_TO_TEST = [1, 2, 3]


def main() -> None:
    cfg = load_config()
    output_dir = Path(cfg.root / OUTPUT_DIR_NAME)
    output_dir.mkdir(parents=True, exist_ok=True)

    require_files(
        {
            "DEM de referencia": cfg.reference_dem,
            "Polígono terreno estable": cfg.stable_terrain,
            **{
                f"DEM NK {year}": cfg.nk_dem(year)
                for year in cfg.years
                if year != cfg.reference_year
            },
        }
    )

    print("=" * 78)
    print("PASO 2: DERAMP CON AUTO-TUNE")
    print(f"Referencia: {cfg.reference_year}")
    print(f"Órdenes a probar: {POLY_ORDERS_TO_TEST}")
    print("=" * 78)

    ref_arr, _, ref_crs, ref_stable_mask = load_dem_with_mask(
        cfg.reference_dem, cfg.stable_terrain
    )

    resultados = []

    for year in [y for y in cfg.years if y != cfg.reference_year]:
        path = cfg.nk_dem(year)
        print(f"\n--- DEM {year} (base: NK) ---")
        try:
            dem_nk_arr, _, _, dem_stable_mask = load_dem_with_mask(
                path, cfg.stable_terrain
            )
            stable_mask = ref_stable_mask & dem_stable_mask
            n_valid = int(stable_mask.sum())
            print(f"  Píxeles válidos en zona estable: {n_valid:,}")

            med_nk, nmad_nk, _ = difference_stats(
                dem_nk_arr - ref_arr, stable_mask
            )
            print(f"  [NK sin deramp]     Mediana: {med_nk:+.3f} m | NMAD: {nmad_nk:.3f} m")

            best = {
                "order": None,
                "dem": dem_nk_arr,
                "med": med_nk,
                "nmad": nmad_nk,
                "rejected": True,
            }

            for order in POLY_ORDERS_TO_TEST:
                try:
                    deramp = xdem.coreg.Deramp(poly_order=order)
                    dem_nk_xdem = xdem.DEM(str(path))
                    deramp.fit(dem_nk_xdem, dem_nk_xdem, inlier_mask=stable_mask)
                    dem_dr = deramp.apply(dem_nk_xdem)

                    med_dr, nmad_dr, _ = difference_stats(
                        dem_dr.data - ref_arr, stable_mask
                    )
                    print(
                        f"  [Deramp orden {order}]     "
                        f"Mediana: {med_dr:+.3f} m | NMAD: {nmad_dr:.3f} m"
                    )

                    if nmad_dr < best["nmad"]:
                        best = {
                            "order": order,
                            "dem": dem_dr.data,
                            "med": med_dr,
                            "nmad": nmad_dr,
                            "rejected": False,
                        }
                except Exception as error:  # noqa: BLE001
                    print(f"  [Deramp orden {order}]     ERROR: {error}")

            transform = None
            crs = ref_crs

            if best["rejected"]:
                print(
                    f"  -> DERAMP RECHAZADO. Se conserva el DEM de NK "
                    f"(NMAD {nmad_nk:.3f} m)."
                )
                out_path = output_dir / f"dem_{year}_final.tif"
                selected_order = "None (NK)"
            else:
                print(
                    f"  -> SELECCIONADO: poly_order={best['order']} "
                    f"(NMAD {best['nmad']:.3f} m, mejora "
                    f"{nmad_nk - best['nmad']:+.3f} m)."
                )
                out_path = output_dir / f"dem_{year}_deramp{best['order']}.tif"
                selected_order = str(best["order"])

            import rasterio
            from affine import Affine

            if transform is None:
                with rasterio.open(path) as src:
                    transform = src.transform
                    crs = src.crs

            from nkdem.raster import write_geotiff  # noqa: E402

            write_geotiff(out_path, best["dem"], transform, crs)
            print(f"  Guardado: {out_path}")

            resultados.append(
                {
                    "year": year,
                    "n_valid": n_valid,
                    "nmad_nk": nmad_nk,
                    "med_nk": med_nk,
                    "order": selected_order,
                    "med_final": best["med"],
                    "nmad_final": best["nmad"],
                    "mejora_nmad": (
                        nmad_nk - best["nmad"] if not best["rejected"] else 0.0
                    ),
                    "output": str(out_path.resolve()),
                }
            )

        except Exception as error:  # noqa: BLE001
            print(f"  ERROR procesando {year}: {error}")

    print("\n" + "=" * 78)
    print("RESUMEN PASO 2 (DERAMP AUTO-TUNE)")
    print("=" * 78)
    header = (f"{'Year':<6} {'N_valid':>9} {'NMAD_NK':>9} {'Orden':>10} "
              f"{'Med_fin':>9} {'NMAD_fin':>9} {'Mejora':>9}")
    print(header)
    print("-" * len(header))
    for r in resultados:
        print(
            f"{r['year']:<6} {r['n_valid']:>9,} "
            f"{r['nmad_nk']:>9.3f} {r['order']:>10} "
            f"{r['med_final']:>+9.3f} {r['nmad_final']:>9.3f} "
            f"{r['mejora_nmad']:>+9.3f}"
        )
    print("=" * 78)

    print("\nArchivos finales (para análisis o Etapa 3):")
    for r in resultados:
        print(f"  {r['year']}: {r['output']}")

    csv_path = Path(cfg.root / CSV_OUTPUT_NAME)
    if resultados:
        write_csv(resultados, csv_path)
        print(f"CSV guardado: {csv_path.resolve()}")


if __name__ == "__main__":
    main()
