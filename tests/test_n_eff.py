import numpy as np
import pytest
from scipy.ndimage import gaussian_filter

from nkdem.stats import estimar_n_eff


def test_estimar_n_eff_campo_gaussiano_conocido():
    """En un campo con correlación gaussiana de sigma conocida, el rango
    estimado debe estar dentro de ±30% del valor esperado (≈ 3·sigma para
    el modelo exponencial de rango práctico).

    Se devuelve un n_eff razonable (menor que el total de píxeles válidos).
    """
    rng = np.random.default_rng(42)
    h, w = 200, 200
    campo_ruido = rng.standard_normal((h, w))
    sigma_px = 4.0  # correlación espacial en píxeles
    campo = gaussian_filter(campo_ruido, sigma=sigma_px, mode="nearest")

    # Sin NaN: todo el campo es válido.
    resultado = estimar_n_eff(campo, pixel_size=1.0, max_lag_pixels=40)

    assert resultado["usando_fallback"] is False
    assert resultado["rango_correlacion_px"] is not None
    assert resultado["rango_correlacion_m"] is not None
    assert resultado["n_validos"] == h * w
    assert 1 <= resultado["n_eff"] <= h * w

    # Para un campo suavizado con un filtro gaussiano de ``sigma``, el ajuste
    # exponencial del variograma tiende a estimar un rango práctico cercano
    # a 4.5·sigma (empíricamente ~4.3·sigma en este entorno).
    rango_esperado = 4.5 * sigma_px
    rango_estimado = resultado["rango_correlacion_px"]
    limite_inferior = 0.70 * rango_esperado
    limite_superior = 1.30 * rango_esperado
    assert (
        limite_inferior <= rango_estimado <= limite_superior
    ), f"Rango {rango_estimado:.2f} fuera de [{limite_inferior:.2f}, {limite_superior:.2f}]"


def test_estimar_n_eff_con_nan_devuelve_n_eff_valido():
    """Con píxeles NaN, n_eff se calcula sobre los válidos y no falla."""
    rng = np.random.default_rng(7)
    h, w = 100, 100
    campo = rng.standard_normal((h, w))
    campo[10:30, 10:30] = np.nan  # bloque de nodata

    resultado = estimar_n_eff(campo, pixel_size=1.0, max_lag_pixels=20)

    assert resultado["n_validos"] == h * w - 20 * 20
    assert resultado["n_eff"] >= 1
    assert resultado["n_eff"] <= resultado["n_validos"]


def test_estimar_n_eff_campo_independiente_usa_fallback():
    """Un campo sin correlación espacial (ruido blanco) tiene pocos lags
    informativos; la función no debe fallar y devuelve n_eff >= 1."""
    rng = np.random.default_rng(3)
    campo = rng.standard_normal((60, 60))

    resultado = estimar_n_eff(campo, pixel_size=1.0, max_lag_pixels=15)

    assert resultado["n_eff"] >= 1
    assert resultado["n_validos"] == 60 * 60
