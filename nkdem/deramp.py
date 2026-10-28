"""Deramp polinómico 2D de memoria acotada.

El deramp (Nuth & Kääb, 2011) modela el sesgo de largo periodo de un DEM como
un polinomio bidimensional ajustado sobre terreno estable:

    dH(x, y) = DEM_ref(x, y) - DEM(x, y) = P(x, y)

Este módulo implementa el ajuste con ``numpy.linalg.lstsq`` sobre los píxeles de
la máscara y la aplicación del polinomio **por bloques de filas**, de modo que
nunca se materializan varias copias del DEM completo (94 millones de píxeles en
este proyecto). La base de términos es la misma que usa ``xdem`` para el deramp
polinómico (producto tensorial ``x^i · y^j`` con ``0 <= i, j <= order``), por lo
que el resultado es equivalente a ``xdem.coreg.Deramp(poly_order=order)``; la
equivalencia está verificada en ``tests/test_cv_equivalence.py`` y en
``tests/test_deramp_semantics.py``.
"""

from __future__ import annotations

import numpy as np
from affine import Affine

from .stats import polynomial_matrix

# Bloque de filas usado al aplicar el polinomio: 256 filas ≈ 2,4 M píxeles,
# suficiente para mantener el uso de memoria por debajo de ~100 MB.
FILAS_POR_BLOQUE = 256


def _xy_desde_filas_columnas(
    transform: Affine, filas: np.ndarray, columnas: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Coordenadas del centro de píxel (x, y) a partir de filas y columnas."""
    x = transform.c + columnas * transform.a + filas * transform.b
    y = transform.f + columnas * transform.d + filas * transform.e
    return x, y


def _normalizar(
    x: np.ndarray, y: np.ndarray, modelo: dict | None = None
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Centra y escala las coordenadas (estabilidad numérica en UTM).

    La normalización es afín y no altera el subespacio ajustado; los parámetros
    se guardan en el modelo para poder reutilizarlos al aplicar el polinomio.
    """
    if modelo is None:
        x_mean, x_std = float(np.mean(x)), float(np.std(x)) or 1.0
        y_mean, y_std = float(np.mean(y)), float(np.std(y)) or 1.0
    else:
        x_mean, x_std = modelo["x_mean"], modelo["x_std"]
        y_mean, y_std = modelo["y_mean"], modelo["y_std"]
    x_n = (x - x_mean) / x_std
    y_n = (y - y_mean) / y_std
    return x_n, y_n, {
        "x_mean": x_mean,
        "x_std": x_std,
        "y_mean": y_mean,
        "y_std": y_std,
    }


def ajustar_deramp(
    dem_ref: np.ndarray,
    dem: np.ndarray,
    mask: np.ndarray,
    transform: Affine,
    order: int = 3,
) -> dict:
    """Ajusta el polinomio de deramp sobre los píxeles de ``mask``.

    Parameters
    ----------
    dem_ref : np.ndarray
        DEM de referencia (el que define la corrección).
    dem : np.ndarray
        DEM a corregir, en la misma cuadrícula.
    mask : np.ndarray
        Máscara booleana de terreno estable (y píxeles finitos).
    transform : Affine
        Transformación de la cuadrícula.
    order : int
        Grado del polinomio (por defecto 3).

    Returns
    -------
    dict
        ``{"coef": (order+1)**2 coeficientes, "order": order, ...normalización}``.
    """
    filas, columnas = np.nonzero(np.asarray(mask, dtype=bool))
    if filas.size == 0:
        raise ValueError("La máscara de deramp no contiene ningún píxel.")

    x, y = _xy_desde_filas_columnas(transform, filas, columnas)
    dH = dem_ref[filas, columnas].astype("float64") - dem[filas, columnas].astype(
        "float64"
    )
    valido = np.isfinite(dH) & np.isfinite(x) & np.isfinite(y)
    if valido.sum() < (order + 1) ** 2:
        raise ValueError(
            "Píxeles válidos insuficientes para ajustar el deramp "
            f"({int(valido.sum())} para {(order + 1) ** 2} parámetros)."
        )

    x_n, y_n, norm = _normalizar(x[valido], y[valido])
    matriz = polynomial_matrix(x_n, y_n, order)
    coef, *_ = np.linalg.lstsq(matriz, dH[valido], rcond=None)

    return {"coef": coef, "order": int(order), **norm}


def aplicar_deramp(
    dem: np.ndarray,
    transform: Affine,
    modelo: dict,
    filas_por_bloque: int = FILAS_POR_BLOQUE,
) -> np.ndarray:
    """Aplica el polinomio del deramp al DEM completo, por bloques de filas.

    Devuelve un array float32 de la misma forma que ``dem`` con la corrección
    sumada. Los píxeles no finitos se mantienen como NaN.
    """
    coef = np.asarray(modelo["coef"], dtype="float64")
    order = int(modelo["order"])
    # ``polynomial_matrix`` ordena los términos con i en el bucle exterior y j
    # en el interior, igual que ``c[i, j] * x**i * y**j`` de polyval2d.
    c = coef.reshape((order + 1, order + 1))

    alto, ancho = dem.shape
    salida = np.empty((alto, ancho), dtype="float32")
    columnas = np.arange(ancho)

    for inicio in range(0, alto, filas_por_bloque):
        fin = min(inicio + filas_por_bloque, alto)
        filas = np.arange(inicio, fin)
        xx, yy = np.meshgrid(columnas, filas)
        x, y = _xy_desde_filas_columnas(transform, yy, xx)
        x_n, y_n, _ = _normalizar(x, y, modelo)
        correccion = np.polynomial.polynomial.polyval2d(x_n, y_n, c)
        bloque = dem[inicio:fin].astype("float64") + correccion
        salida[inicio:fin] = bloque.astype("float32")

    return salida
