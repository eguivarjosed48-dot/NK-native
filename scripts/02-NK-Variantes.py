"""
Paso 2 (variantes): NK | NK+deramp3 | NK+deramp-CV
CV espacial reimplementada con numpy.linalg.lstsq: sin crear DEMs por fold,
sin presión de memoria, sin swap. Equivalente matemático a Deramp(poly_order=3).

Salidas:
  - dems_variants/<year>_NK.tif, _deramp3.tif, _derampCV.tif
  - coreg_variants_summary.csv
"""

from __future__ import annotations

import csv
import gc
import os
import sys
import warnings
from pathlib import Path

import numpy as np
import xdem

warnings.filterwarnings("ignore", message=".*partition.*MaskedArray.*")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nkdem.config import load_config, require_files  # noqa: E402
from nkdem.io import write_csv  # noqa: E402
from nkdem.raster import load_dem_with_mask  # noqa: E402
from nkdem.stats import (  # noqa: E402
    assign_blocks,
    difference_stats,
    nmad,
    polynomial_matrix,
)

OUTPUT_DIR_NAME = "dems_variants"
CSV_OUTPUT_NAME = "coreg_variants_summary.csv"

POLY_ORDER = 3
CV_N_BLOCKS = 4
CV_MIN_PIXELS_PER_BLOCK = 2000
CV_MAX_TRAIN_PIXELS = 200_000
RANDOM_SEED = 42


def cv_espacial_nmad_numpy(
    ref_arr,
    nk_arr,
    stable_mask,
    transform,
    order,
    n_blocks,
    min_pix,
    max_train,
    seed,
):
    """CV espacial leave-one-block-out con numpy.linalg.lstsq.

    Nota de diseño: esta función NO usa ``xdem.coreg.Deramp`` dentro del
    bucle de folds. El motivo es de rendimiento: llamar a
    ``Deramp.apply`` sobre el DEM completo por cada fold genera copias
    temporales grandes y provocó uso de swap en equipos con 8 GB de RAM.
    En su lugar, se ajusta el polinomio únicamente sobre los píxeles de
    entrenamiento de cada fold con ``np.linalg.lstsq`` sobre una matriz de
    diseño polinómica construida a mano (``construir_matriz_polinomio``).

    Esta reimplementación es matemáticamente equivalente a
    ``xdem.coreg.Deramp(poly_order=N)`` porque:

    * ``construir_matriz_polinomio`` reproduce exactamente la misma base de
      términos [1, x, y, x², xy, y², ...] que usa xdem internamente para el
      deramp polinómico.
    * La normalización de coordenadas (``x_n``, ``y_n``) es únicamente para
      estabilidad numérica (evita mal condicionamiento cuando las coordenadas
      son grandes en metros UTM); no altera el subespacio ajustado y, por lo
      tanto, no cambia el resultado del polinomio ajustado.
    * El ajuste con ``np.linalg.lstsq`` resuelve los mismos mínimos cuadrados
      ordinarios que xdem resuelve internamente para el deramp polinómico.

    Por tanto, el NMAD de validación cruzada obtenido aquí es directamente
    comparable con el que daría xdem, pero sin el coste de memoria de crear
    un DEM por fold.
    """
    rows, cols = np.nonzero(stable_mask)
    n = rows.size
    if n == 0:
        return np.nan, 0, np.nan

    x = transform.c + cols * transform.a + rows * transform.b
    y = transform.f + cols * transform.d + rows * transform.e

    x_mean, x_std = x.mean(), x.std()
    y_mean, y_std = y.mean(), y.std()
    x_n = (x - x_mean) / (x_std if x_std > 0 else 1.0)
    y_n = (y - y_mean) / (y_std if y_std > 0 else 1.0)

    dH = nk_arr[rows, cols] - ref_arr[rows, cols]
    valid = np.isfinite(dH)
    if valid.sum() == 0:
        return np.nan, 0, np.nan

    block_full = assign_blocks(stable_mask, n_blocks)
    block = block_full[rows, cols]

    A_full = polynomial_matrix(x_n[valid], y_n[valid], order)
    dH_valid = dH[valid]
    block_valid = block[valid]

    rng = np.random.default_rng(seed)

    nmads_cv = []
    nmads_nk_test = []

    for b in np.unique(block_valid):
        if b < 0:
            continue
        is_test = block_valid == b
        n_test = is_test.sum()
        if n_test < min_pix:
            continue
        train_idx = np.nonzero(~is_test)[0]
        if train_idx.size > max_train:
            train_idx = rng.choice(train_idx, size=max_train, replace=False)

        A_train = A_full[train_idx]
        dH_train = dH_valid[train_idx]

        try:
            coef, *_ = np.linalg.lstsq(A_train, dH_train, rcond=None)
        except np.linalg.LinAlgError:
            continue

        A_test = A_full[is_test]
        pred_test = A_test @ coef
        residual_test = dH_valid[is_test] - pred_test
        residual_test = residual_test[np.isfinite(residual_test)]

        if residual_test.size > 0:
            nmads_cv.append(float(nmad(residual_test)))

        nk_test = dH_valid[is_test]
        nk_test = nk_test[np.isfinite(nk_test)]
        if nk_test.size > 0:
            nmads_nk_test.append(float(nmad(nk_test)))

    if not nmads_cv:
        return np.nan, 0, np.nan
    return float(np.mean(nmads_cv)), len(nmads_cv), float(np.mean(nmads_nk_test))


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

    print("=" * 82)
    print(
        "PASO 2 (VARIANTES): NK | NK+deramp3 | NK+deramp-CV  [CV vectorizada]"
    )
    print(
        f"Referencia: {cfg.reference_year} | poly_order={POLY_ORDER} | "
        f"CV {CV_N_BLOCKS}x{CV_N_BLOCKS}"
    )
    print("=" * 82)

    ref_arr, transform, ref_crs, ref_mask = load_dem_with_mask(
        cfg.reference_dem, cfg.stable_terrain
    )

    filas = []

    for year in [y for y in cfg.years if y != cfg.reference_year]:
        path = cfg.nk_dem(year)
        print(f"\n--- DEM {year} ---")
        try:
            dem_nk, dem_mask, _, dem_crs = load_dem_with_mask(
                path, cfg.stable_terrain
            )
            stable_mask = ref_mask & dem_mask
            n_valid = int(stable_mask.sum())
            print(f"  Píxeles válidos en zona estable: {n_valid:,}")

            diff_nk = dem_nk - ref_arr
            med_nk, nmad_nk, _ = difference_stats(diff_nk, stable_mask)
            print(f"  [NK]            Mediana: {med_nk:+.3f} m | NMAD: {nmad_nk:.3f} m")
            out_nk = output_dir / f"{year}_NK.tif"
            import rasterio

            with rasterio.open(path) as src:
                variant_transform = src.transform
                variant_crs = src.crs

            from nkdem.raster import write_geotiff  # noqa: E402

            write_geotiff(out_nk, dem_nk, variant_transform, variant_crs)

            # deramp3 in-sample con xdem (1 vez por año, aceptable)
            deramp3 = xdem.coreg.Deramp(poly_order=POLY_ORDER)
            dem_nk_xdem = xdem.DEM(str(path))
            deramp3.fit(
                dem_nk_xdem, dem_nk_xdem, inlier_mask=stable_mask
            )
            dem_d3 = deramp3.apply(dem_nk_xdem)
            diff_d3 = dem_d3.data - ref_arr
            med_d3, nmad_d3, _ = difference_stats(diff_d3, stable_mask)
            print(
                f"  [NK+deramp3]    Mediana: {med_d3:+.3f} m | NMAD: {nmad_d3:.3f} m"
            )
            out_d3 = output_dir / f"{year}_deramp3.tif"
            write_geotiff(out_d3, dem_d3.data, variant_transform, variant_crs)
            del diff_d3, dem_d3; gc.collect()

            # CV espacial con numpy (rápida)
            print(
                f"  CV espacial ({CV_N_BLOCKS}x{CV_N_BLOCKS}, numpy)..."
            )
            nmad_cv, n_folds, nmad_nk_cv = cv_espacial_nmad_numpy(
                ref_arr,
                dem_nk,
                stable_mask,
                variant_transform,
                POLY_ORDER,
                CV_N_BLOCKS,
                CV_MIN_PIXELS_PER_BLOCK,
                CV_MAX_TRAIN_PIXELS,
                RANDOM_SEED,
            )
            print(
                f"  [CV] folds: {n_folds} | NMAD_CV: {nmad_cv:.3f} | "
                f"NMAD_NK(en folds): {nmad_nk_cv:.3f}"
            )

            cv_acepta = (not np.isnan(nmad_cv)) and (
                nmad_cv < nmad_nk_cv
            )
            if cv_acepta:
                dem_cv, med_cv, nmad_cv_final = dem_d3.data, med_d3, nmad_d3
                print(
                    f"  [NK+deramp-CV]  ACEPTADO  -> se guarda como deramp3."
                )
            else:
                dem_cv, med_cv, nmad_cv_final = dem_nk, med_nk, nmad_nk
                print(
                    f"  [NK+deramp-CV]  RECHAZADO -> se guarda como NK."
                )
            out_cv = output_dir / f"{year}_derampCV.tif"
            write_geotiff(out_cv, dem_cv, variant_transform, variant_crs)
            del dem_cv; gc.collect()

            filas.append(
                {
                    "year": year,
                    "n_valid": n_valid,
                    "nmad_nk": nmad_nk,
                    "med_nk": med_nk,
                    "nmad_deramp3": nmad_d3,
                    "med_deramp3": med_d3,
                    "cv_n_folds": n_folds,
                    "nmad_cv": nmad_cv,
                    "nmad_nk_cv": nmad_nk_cv,
                    "cv_acepta": bool(cv_acepta),
                    "nmad_derampCV": nmad_cv_final,
                    "med_derampCV": med_cv,
                }
            )

        except Exception as error:  # noqa: BLE001
            print(f"  ERROR procesando {year}: {error}")

    print("\n" + "=" * 82)
    print("RESUMEN VARIANTES")
    print("=" * 82)
    header = (f"{'Year':<6} {'N_valid':>9} {'NMAD_NK':>9} {'NMAD_d3':>9} "
              f"{'NMAD_CV':>9} {'NMAD_NKcv':>10} {'CV?':>5} {'NMAD_CVfin':>11}")
    print(header)
    print("-" * len(header))
    for r in filas:
        print(
            f"{r['year']:<6} {r['n_valid']:>9,} "
            f"{r['nmad_nk']:>9.3f} {r['nmad_deramp3']:>9.3f} "
            f"{r['nmad_cv']:>9.3f} {r['nmad_nk_cv']:>10.3f} "
            f"{'Sí' if r['cv_acepta'] else 'No':>5} "
            f"{r['nmad_derampCV']:>11.3f}"
        )
    print("=" * 82)

    if filas:
        csv_path = Path(cfg.root / CSV_OUTPUT_NAME)
        write_csv(filas, csv_path)
        print(f"\nCSV guardado: {csv_path.resolve()}")


if __name__ == "__main__":
    main()
