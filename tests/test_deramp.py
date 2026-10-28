"""Pruebas del deramp polinómico de memoria acotada (``nkdem.deramp``)."""

from __future__ import annotations

import numpy as np
import pytest
import rasterio
import xdem
from affine import Affine

from nkdem.deramp import ajustar_deramp, aplicar_deramp

N = 150
TRANSFORM = Affine(0.5, 0.0, 574000.0, 0.0, -0.5, 8225000.0)
CRS = "EPSG:32719"


def _nmad(values: np.ndarray) -> float:
    values = np.asarray(values)[np.isfinite(values)]
    return float(1.4826 * np.median(np.abs(values - np.median(values))))


def _campo_sintetico():
    filas, columnas = np.meshgrid(np.arange(N), np.arange(N), indexing="ij")
    x, y = np.meshgrid(np.arange(N), np.arange(N), indexing="ij")
    # Superficie de referencia con relieve suave.
    ref = 5100.0 + 0.30 * x + 0.15 * y + 0.05 * x * y / N
    # Sesgo polinómico conocido (lo que el deramp debe recuperar).
    sesgo = (
        0.40
        + 0.25 * (x - N / 2) / N
        - 0.18 * (y - N / 2) / N
        + 0.30 * ((x - N / 2) / N) ** 2
        - 0.20 * ((x - N / 2) / N) ** 3
    )
    return ref, ref + sesgo, filas, columnas


def test_ajustar_deramp_recupera_el_polinomio():
    ref, dem, _, _ = _campo_sintetico()
    mask = np.ones((N, N), dtype=bool)

    modelo = ajustar_deramp(ref, dem, mask, TRANSFORM, order=3)
    corregido = aplicar_deramp(dem, TRANSFORM, modelo)

    # El resultado se escribe en float32 (≈5×10⁻⁴ m de cuantización a 5.100 m).
    residuo = corregido - ref
    assert _nmad(residuo) < 1e-3
    assert np.nanmax(np.abs(residuo)) < 5e-3


def test_aplicar_deramp_es_independiente_del_bloque():
    ref, dem, _, _ = _campo_sintetico()
    modelo = ajustar_deramp(ref, dem, np.ones((N, N), dtype=bool), TRANSFORM, order=3)

    por_defecto = aplicar_deramp(dem, TRANSFORM, modelo)
    bloques_pequenos = aplicar_deramp(dem, TRANSFORM, modelo, filas_por_bloque=7)

    assert np.allclose(por_defecto, bloques_pequenos, atol=1e-5)
    assert np.allclose(por_defecto.ravel()[:N], bloques_pequenos.ravel()[:N])


def test_deramp_equivalente_a_xdem(tmp_path):
    """La corrección coincide con ``xdem.coreg.Deramp`` (misma base y MCO)."""
    ref, dem, _, _ = _campo_sintetico()

    def escribir(array, ruta):
        with rasterio.open(
            ruta,
            "w",
            driver="GTiff",
            height=N,
            width=N,
            count=1,
            dtype="float32",
            crs=CRS,
            transform=TRANSFORM,
        ) as dst:
            dst.write(array.astype("float32"), 1)

    escribir(ref, tmp_path / "ref.tif")
    escribir(dem, tmp_path / "dem.tif")

    modelo = ajustar_deramp(ref, dem, np.ones((N, N), dtype=bool), TRANSFORM, order=3)
    propio = aplicar_deramp(dem, TRANSFORM, modelo)

    deramp = xdem.coreg.Deramp(poly_order=3)
    deramp.fit(
        xdem.DEM(str(tmp_path / "ref.tif")),
        xdem.DEM(str(tmp_path / "dem.tif")),
        inlier_mask=np.ones((N, N), dtype=bool),
    )
    xdem_out = deramp.apply(xdem.DEM(str(tmp_path / "dem.tif"))).data

    diferencia = np.abs(np.asarray(propio, dtype=float) - np.asarray(xdem_out, dtype=float))
    assert np.nanmean(diferencia) < 1e-3


def test_aplicar_deramp_preserva_nan():
    ref, dem, _, _ = _campo_sintetico()
    dem = dem.copy()
    dem[10:20, 10:20] = np.nan
    modelo = ajustar_deramp(ref, dem, np.ones((N, N), dtype=bool), TRANSFORM, order=3)
    salida = aplicar_deramp(dem, TRANSFORM, modelo)
    assert np.all(np.isnan(salida[10:20, 10:20]))
    assert np.isfinite(salida[0, 0])


def test_ajustar_deramp_sin_pixeles_falla():
    ref, dem, _, _ = _campo_sintetico()
    with pytest.raises(ValueError):
        ajustar_deramp(ref, dem, np.zeros((N, N), dtype=bool), TRANSFORM, order=3)
