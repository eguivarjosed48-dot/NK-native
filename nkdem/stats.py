"""Funciones estadísticas y de diseño polinomial (solo numpy).

Se mantienen sin dependencias geoespaciales para poder testearlas en CI
sin instalar rasterio/geopandas/xdem.
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
    """Exponentes (i, j) de los términos x^i · y^j de un polinomio de grado ``order``."""
    return [(i, j) for i in range(order + 1) for j in range(order + 1 - i)]


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
