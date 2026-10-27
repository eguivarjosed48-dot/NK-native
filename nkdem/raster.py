"""Utilidades ráster: lectura, máscaras por polígono, escritura y agregación."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from affine import Affine
from rasterio.crs import CRS
from rasterio.features import geometry_mask

DEFAULT_NODATA = -9999.0


def read_raster(path: str | Path) -> tuple[np.ndarray, Affine, CRS, float | None]:
    """Lee la banda 1 como float32 y convierte el nodata declarado a NaN."""
    with rasterio.open(path) as src:
        array = src.read(1).astype(np.float32)
        nodata = src.nodata
        if nodata is not None:
            array[array == nodata] = np.nan
        return array, src.transform, src.crs, nodata


def read_xdem(path: str | Path):
    """Carga un DEM de xdem (import perezoso para no exigir xdem en tests)."""
    import xdem

    return xdem.DEM(str(path))


def polygon_mask(
    polygon_path: str | Path,
    shape: tuple[int, int],
    transform: Affine,
    crs: CRS | None,
) -> np.ndarray:
    """Máscara booleana True dentro de los polígonos (reproyectados si hace falta)."""
    polygons = gpd.read_file(polygon_path)
    if polygons.crs is None:
        raise ValueError(f"El polígono '{polygon_path}' no tiene CRS definido.")
    if crs is not None and polygons.crs != crs:
        polygons = polygons.to_crs(crs)

    outside = geometry_mask(
        polygons.geometry,
        out_shape=shape,
        transform=transform,
        invert=False,
    )
    return ~outside


def load_dem_with_mask(
    dem_path: str | Path,
    polygon_path: str | Path,
) -> tuple[np.ndarray, Affine, CRS, np.ndarray]:
    """Carga un DEM y devuelve (array, transform, crs, máscara válida dentro del polígono)."""
    array, transform, crs, _ = read_raster(dem_path)
    inside = polygon_mask(polygon_path, array.shape, transform, crs)
    return array, transform, crs, inside & np.isfinite(array)


def write_geotiff(
    path: str | Path,
    array: np.ndarray,
    transform: Affine,
    crs: CRS,
    nodata: float = DEFAULT_NODATA,
    compress: str = "deflate",
) -> None:
    """Escribe un GeoTIFF float32 con compresión y nodata explícito."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    height, width = array.shape
    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": "float32",
        "crs": crs,
        "transform": transform,
        "nodata": nodata,
        "compress": compress,
    }
    output = np.where(np.isfinite(array), array, nodata).astype(np.float32)
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(output, 1)


def downsample_mean(array: np.ndarray, factor: int) -> np.ndarray:
    """Promedio por bloques de ``factor × factor`` (recorta el borde sobrante)."""
    if factor <= 1:
        return array
    height, width = array.shape
    new_h, new_w = (height // factor) * factor, (width // factor) * factor
    return array[:new_h, :new_w].reshape(
        new_h // factor, factor, new_w // factor, factor
    ).mean(axis=(1, 3))
