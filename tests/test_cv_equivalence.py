import os
import tempfile

import numpy as np
import pytest
import rasterio
from affine import Affine

from nkdem.stats import polynomial_matrix

xdem = pytest.importorskip("xdem")


def _escribir_geotiff_tmp(ruta, array, transform, crs="EPSG:32719"):
    profile = {
        "driver": "GTiff",
        "height": array.shape[0],
        "width": array.shape[1],
        "count": 1,
        "dtype": "float32",
        "crs": crs,
        "transform": transform,
        "nodata": -9999.0,
    }
    with rasterio.open(ruta, "w", **profile) as dst:
        dst.write(array.astype(np.float32), 1)


def test_coeficientes_lstsq_equivalentes_a_xdem_deramp():
    """Los coeficientes de np.linalg.lstsq son equivalentes (con cambio de
    signo, por dirección de la diferencia) a los de xdem.coreg.Deramp.

    xdem ajusta (ref - dem); este módulo ajusta (dem - ref). Por tanto los
    coeficientes difieren en signo pero no en magnitud.

    Se usan índices de píxel (0 .. w-1, 0 .. h-1) como coordenadas, que es
    lo que xdem utiliza internamente para el deramp polinómico.
    """
    h, w = 25, 30
    transform = Affine(0.1, 0, 575000.0, 0, -0.1, 8225000.0)

    # Grid de índices de píxel, shape (h, w). Default indexing="xy" da
    # (h, w): XX varía por columnas (x), YY por filas (y).
    XX, YY = np.meshgrid(np.arange(w), np.arange(h))

    # DEM de referencia plano y DEM con tendencia polinómica conocida.
    arr_ref = np.zeros((h, w), dtype=np.float32)
    tendencia = 0.5 + 0.1 * XX + 0.05 * YY + 0.01 * XX**2
    arr_dem = (tendencia).astype(np.float32)

    tmpdir = tempfile.mkdtemp()
    ref_path = os.path.join(tmpdir, "ref.tif")
    dem_path = os.path.join(tmpdir, "dem.tif")
    _escribir_geotiff_tmp(ref_path, arr_ref, transform)
    _escribir_geotiff_tmp(dem_path, arr_dem, transform)

    ref = xdem.DEM(ref_path)
    dem = xdem.DEM(dem_path)
    mask = np.ones((h, w), dtype=bool)

    # --- Ajuste con xdem (modela ref - dem) ---
    deramp = xdem.coreg.Deramp(poly_order=3)
    deramp.fit(ref, dem, inlier_mask=mask)
    coef_xdem = deramp.meta["outputs"]["fitorbin"]["fit_params"].astype(float)

    # --- Ajuste con numpy.linalg.lstsq (modela dem - ref) ---
    # Mismo orden de términos y mismas coordenadas que xdem.
    x_coords = XX.ravel()
    y_coords = YY.ravel()
    A = polynomial_matrix(x_coords, y_coords, order=3)
    dH = arr_dem.ravel() - arr_ref.ravel()  # = tendencia
    coef_lstsq, *_ = np.linalg.lstsq(A, dH, rcond=None)

    # Equivalencia de coeficientes (xdem usa signo opuesto).
    assert coef_xdem.shape == coef_lstsq.shape
    np.testing.assert_allclose(coef_xdem, -coef_lstsq, rtol=1e-6, atol=1e-6)


def test_predicciones_equivalentes_en_grid():
    """Las predicciones del polinomio son equivalentes en un grid de puntos."""
    h, w = 25, 30
    transform = Affine(0.1, 0, 575000.0, 0, -0.1, 8225000.0)

    XX, YY = np.meshgrid(np.arange(w), np.arange(h))
    arr_ref = np.zeros((h, w), dtype=np.float32)
    tendencia = 0.5 + 0.1 * XX + 0.05 * YY + 0.01 * XX**2
    arr_dem = (tendencia).astype(np.float32)

    tmpdir = tempfile.mkdtemp()
    ref_path = os.path.join(tmpdir, "ref.tif")
    dem_path = os.path.join(tmpdir, "dem.tif")
    _escribir_geotiff_tmp(ref_path, arr_ref, transform)
    _escribir_geotiff_tmp(dem_path, arr_dem, transform)

    ref = xdem.DEM(ref_path)
    dem = xdem.DEM(dem_path)
    mask = np.ones((h, w), dtype=bool)

    deramp = xdem.coreg.Deramp(poly_order=3)
    deramp.fit(ref, dem, inlier_mask=mask)
    dem_corregido = deramp.apply(dem)

    # Predicción manual con numpy.linalg.lstsq sobre el grid completo.
    x_coords = XX.ravel()
    y_coords = YY.ravel()
    A = polynomial_matrix(x_coords, y_coords, order=3)
    dH = arr_dem.ravel() - arr_ref.ravel()
    coef_lstsq, *_ = np.linalg.lstsq(A, dH, rcond=None)
    prediccion_manual = (A @ coef_lstsq).reshape(h, w)

    # xdem corrige restando la tendencia estimada (ref - dem = -tendencia).
    # Al aplicar, devuelve aproximadamente el DEM de referencia.
    np.testing.assert_allclose(
        dem_corregido.data, arr_ref, rtol=1e-4, atol=1e-4
    )
    # La predicción manual de la tendencia debe aproximar la tendencia real.
    np.testing.assert_allclose(
        prediccion_manual, tendencia, rtol=1e-4, atol=1e-4
    )
