"""Semántica de ``xdem.coreg.Deramp`` (regresión del bug de ``scripts/02``).

``Deramp.fit(referencia, dem)`` ajusta el polinomio sobre la diferencia
``referencia - dem``. Si se le pasa dos veces el mismo DEM, la diferencia es
cero y la corrección aplicada también (≈0), de modo que la variante "deramp3"
saldría idéntica a "NK" y la validación cruzada nunca aceptaría el deramp.

Estos tests fijan la semántica correcta con DEMs sintéticos para que una
regresión de ese tipo falle en CI.
"""

from __future__ import annotations

import numpy as np
import pytest
import rasterio
import xdem
from affine import Affine

N = 120
TRANSFORM = Affine(1.0, 0.0, 0.0, 0.0, -1.0, N)
CRS = "EPSG:32719"


def _nmad(values: np.ndarray) -> float:
    values = values[np.isfinite(values)]
    return float(1.4826 * np.median(np.abs(values - np.median(values))))


def _write_dem(array: np.ndarray, path) -> xdem.DEM:
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=array.shape[0],
        width=array.shape[1],
        count=1,
        dtype="float64",
        crs=CRS,
        transform=TRANSFORM,
    ) as dst:
        dst.write(array, 1)
    return xdem.DEM(str(path))


@pytest.fixture()
def dems(tmp_path):
    """Referencia plana/inclinada y DEM con un sesgo suave (tipo deriva)."""
    yy, xx = np.meshgrid(np.arange(N), np.arange(N), indexing="ij")
    referencia = 1000.0 + 0.05 * xx + 0.02 * yy
    sesgo = 0.8 * xx / N + 0.4 * yy / N - 0.1  # campo suave de error
    dem = referencia + sesgo
    mask = np.ones((N, N), dtype=bool)
    return {
        "ref": _write_dem(referencia, tmp_path / "ref.tif"),
        "dem": _write_dem(dem, tmp_path / "dem.tif"),
        "mask": mask,
    }


def test_deramp_con_referencia_reduce_el_sesgo(dems):
    """``fit(ref, dem)`` corrige el residuo medido en la máscara."""
    deramp = xdem.coreg.Deramp(poly_order=3)
    deramp.fit(dems["ref"], dems["dem"], inlier_mask=dems["mask"])
    corregido = deramp.apply(dems["dem"])

    antes = _nmad(dems["dem"].data - dems["ref"].data)
    despues = _nmad(corregido.data - dems["ref"].data)

    assert antes > 0.1, "el caso sintético debe tener un sesgo apreciable"
    assert despues < 0.05 * antes, (
        f"el deramp contra la referencia debe reducir el NMAD: "
        f"{antes:.4f} m -> {despues:.4f} m"
    )


def test_deramp_contra_si_mismo_no_corrige(dems):
    """``fit(dem, dem)`` no aplica corrección: documenta el bug del paso 02.

    Si algún día se cambiara el código a ``fit(dem, dem)``, la variante
    deramp3 sería idéntica a NK; este test deja constancia del porqué.
    """
    deramp = xdem.coreg.Deramp(poly_order=3)
    deramp.fit(dems["dem"], dems["dem"], inlier_mask=dems["mask"])
    corregido = deramp.apply(dems["dem"])

    cambio_maximo = float(np.nanmax(np.abs(corregido.data - dems["dem"].data)))
    assert cambio_maximo < 1e-2, (
        "fit(dem, dem) ajusta la diferencia nula y no debe corregir nada "
        f"(cambio máximo {cambio_maximo:.3e} m)"
    )
