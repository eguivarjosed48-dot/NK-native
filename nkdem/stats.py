"""Funciones estadísticas, de diseño polinomial y propagación de error.

Se mantienen con dependencias mínimas (numpy; scipy solo dentro de las
funciones que lo necesitan) para poder testear la mayoría en CI.
"""

from __future__ import annotations

import numpy as np


def nmad(values: np.ndarray) -> float:
    """Normalized Median Absolute Deviation (1.4826 · MAD)."""
    values = np.asarray(values, dtype=float)
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return float("nan")
    median = np.median(finite)
    return float(1.4826 * np.median(np.abs(finite - median)))


def difference_stats(
    diff: np.ndarray,
    mask: np.ndarray | None = None,
) -> tuple[float, float, int]:
    """Mediana, NMAD y número de píxeles válidos de una diferencia de DEMs."""
    values = np.asarray(diff, dtype=float)
    if mask is not None:
        values = values[np.asarray(mask, dtype=bool)]
    values = values[np.isfinite(values)]
    if values.size == 0:
        return float("nan"), float("nan"), 0
    return float(np.median(values)), nmad(values), int(values.size)


def poly_terms(order: int) -> list[tuple[int, int]]:
    """Exponentes (i, j) de los términos x^i · y^j de un polinomio de grado ``order``.

    Se genera la base tensor-producto: todas las combinaciones con
    ``0 <= i <= order`` y ``0 <= j <= order`` (``(order + 1)**2`` términos),
    ordenadas con ``i`` en el bucle exterior y ``j`` en el interior:
    [(0,0), (0,1), ..., (0,order), (1,0), (1,1), ..., (order,order)].

    Este es el mismo orden y alcance de términos que usa internamente
    ``xdem.coreg.Deramp`` para el deramp polinómico, lo permite comparar
    coeficientes directamente.
    """
    return [(i, j) for i in range(order + 1) for j in range(order + 1)]


def polynomial_matrix(x: np.ndarray, y: np.ndarray, order: int) -> np.ndarray:
    """Matriz de diseño [1, x, y, x², xy, y², …] para ``order``."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    terms = poly_terms(order)
    matrix = np.empty((x.size, len(terms)), dtype=np.float64)
    for column, (i, j) in enumerate(terms):
        matrix[:, column] = (x**i) * (y**j)
    return matrix


def assign_blocks(mask: np.ndarray, n_blocks: int) -> np.ndarray:
    """Asigna cada píxel de ``mask`` a una celda de una grilla ``n_blocks × n_blocks``.

    Devuelve un array int32 con -1 fuera de la máscara. Se usa para la
    validación cruzada espacial bloqueada.
    """
    if n_blocks < 1:
        raise ValueError("n_blocks debe ser >= 1")

    block_id = np.full(mask.shape, -1, dtype=np.int32)
    rows, cols = np.nonzero(mask)
    if rows.size == 0:
        return block_id

    r_min, r_max = rows.min(), rows.max() + 1
    c_min, c_max = cols.min(), cols.max() + 1
    r_idx = np.clip(((rows - r_min) * n_blocks) // (r_max - r_min), 0, n_blocks - 1)
    c_idx = np.clip(((cols - c_min) * n_blocks) // (c_max - c_min), 0, n_blocks - 1)
    block_id[rows, cols] = (r_idx * n_blocks + c_idx).astype(np.int32)
    return block_id


def _variograma_experimental(
    dh: np.ndarray, max_lag_pixels: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Calcula el variograma experimental de ``dh`` usando desplazamientos.

    Para cada lag h (en píxeles, distancia euclidiana diagonal),
    semivarianza = 0.5 * mean((z(s) - z(s+h))^2) sobre pares válidos.

    Devuelve (lags, semivarianzas, conteos_pares).
    """
    work = np.where(np.isfinite(dh), dh, np.nan)
    finitos = np.isfinite(dh)

    lags: list[float] = []
    semivarianzas: list[float] = []
    conteos: list[int] = []

    max_lag = min(max_lag_pixels, min(dh.shape) // 2)
    if max_lag < 1:
        return np.array(lags), np.array(semivarianzas), np.array(conteos)

    for lag in range(1, max_lag + 1):
        # Desplazamiento diagonal (lag, lag) para aproximar distancia euclidiana.
        shifted = np.roll(np.roll(work, -lag, axis=1), -lag, axis=0)
        mask = finitos & np.roll(np.roll(finitos, -lag, axis=1), -lag, axis=0)
        # np.roll hace wrap-around en los bordes; excluir esas columnas/filas.
        mask[:, -lag:] = False
        mask[-lag:, :] = False

        if int(mask.sum()) < 5:
            continue

        diff = work[mask] - shifted[mask]
        semivar = float(0.5 * np.nanmean(diff**2))

        # Distancia euclidiana del desplazamiento diagonal (lag, lag).
        distancia = lag * np.sqrt(2.0)

        lags.append(distancia)
        semivarianzas.append(semivar)
        conteos.append(int(mask.sum()))

    return np.array(lags), np.array(semivarianzas), np.array(conteos)


def _modelo_exponencial(h: np.ndarray, nugget: float, sill: float, a: float) -> np.ndarray:
    """Modelo de variograma exponencial: gamma(h) = nugget + sill*(1 - exp(-h/a))."""
    return nugget + sill * (1.0 - np.exp(-h / np.maximum(a, 1e-9)))


def _modelo_esferico(h: np.ndarray, nugget: float, sill: float, a: float) -> np.ndarray:
    """Modelo de variograma esférico."""
    h = np.asarray(h, dtype=float)
    resultado = np.full_like(h, nugget + sill)
    dentro = h <= a
    resultado[dentro] = nugget + sill * (
        1.5 * h[dentro] / a - 0.5 * (h[dentro] / a) ** 3
    )
    return resultado


def estimar_n_eff(
    dh: np.ndarray,
    pixel_size: float,
    max_lag_pixels: int = 50,
) -> dict:
    """Estima el número efectivo de píxeles independientes usando variograma.

    Calcula el variograma experimental del residual ``dh``, ajusta un modelo
    esférico o exponencial con ``scipy.optimize.curve_fit`` para estimar el
    rango de correlación (en píxeles) y devuelve::

        n_eff = area_valida / (rango * pixel_size)^2
              = n_validos / rango_px^2

    Donde ``area_valida = n_validos * pixel_size^2``.

    Parámetros
    ----------
    dh : np.ndarray
        Array 2D de residuales (puede contener NaN).
    pixel_size : float
        Tamaño del píxel en metros (asumido cuadrado).
    max_lag_pixels : int
        Lag máximo en píxeles para calcular el variograma.

    Devuelve
    -------
    dict con:
        - ``n_eff`` : número efectivo de píxeles independientes (int).
        - ``rango_correlacion_px`` : rango de correlación en píxeles (float o None).
        - ``rango_correlacion_m`` : rango de correlación en metros (float o None).
        - ``n_validos`` : número de píxeles válidos (int).
        - ``modelo`` : "exponencial", "esferico" o "fallback".
        - ``usando_fallback`` : True si se usó la fracción arbitraria por falta de convergencia.
    """
    finitos = np.isfinite(dh)
    n_validos = int(finitos.sum())

    if n_validos < 10:
        return {
            "n_eff": max(1, int(n_validos * 0.05)),
            "rango_correlacion_px": None,
            "rango_correlacion_m": None,
            "n_validos": n_validos,
            "modelo": "fallback",
            "usando_fallback": True,
            "motivo": "pocos píxeles válidos",
        }

    lags, semivarianzas, _ = _variograma_experimental(dh, max_lag_pixels)

    if len(lags) < 3:
        return {
            "n_eff": max(1, int(n_validos * 0.05)),
            "rango_correlacion_px": None,
            "rango_correlacion_m": None,
            "n_validos": n_validos,
            "modelo": "fallback",
            "usando_fallback": True,
            "motivo": "insuficientes lags para variograma",
        }

    rango_estimado: float | None = None
    modelo_usado: str | None = None

    # 1) Intentar ajuste exponencial (rango práctico = 3 * a).
    try:
        from scipy.optimize import curve_fit

        p0 = [
            float(semivarianzas.min()),
            float(semivarianzas.max() - semivarianzas.min()),
            float(lags.mean()),
        ]
        popt, _ = curve_fit(
            _modelo_exponencial, lags, semivarianzas, p0=p0, maxfev=20000
        )
        _, _, a = popt
        if a is not None and a > 0:
            rango_estimado = float(3.0 * a)
            modelo_usado = "exponencial"
    except Exception:
        pass

    # 2) Si falló, intentar esférico (rango = a).
    if rango_estimado is None or rango_estimado <= 0:
        try:
            from scipy.optimize import curve_fit

            p0 = [
                float(semivarianzas.min()),
                float(semivarianzas.max() - semivarianzas.min()),
                float(lags.mean()),
            ]
            popt, _ = curve_fit(
                _modelo_esferico, lags, semivarianzas, p0=p0, maxfev=20000
            )
            _, _, a = popt
            if a is not None and a > 0:
                rango_estimado = float(a)
                modelo_usado = "esferico"
        except Exception:
            pass

    # 3) Fallback: fracción arbitraria (documentada explícitamente).
    if rango_estimado is None or rango_estimado <= 0:
        n_eff_fallback = max(1, int(n_validos * 0.05))
        return {
            "n_eff": n_eff_fallback,
            "rango_correlacion_px": None,
            "rango_correlacion_m": None,
            "n_validos": n_validos,
            "modelo": "fallback",
            "usando_fallback": True,
            "motivo": "variograma no convergió",
        }

    # n_eff = n_validos / rango_px^2 (el pixel_size se cancela en el cociente).
    n_eff = max(1, int(n_validos / (rango_estimado**2)))

    return {
        "n_eff": n_eff,
        "rango_correlacion_px": float(rango_estimado),
        "rango_correlacion_m": float(rango_estimado * pixel_size),
        "n_validos": n_validos,
        "modelo": modelo_usado,
        "usando_fallback": False,
    }
