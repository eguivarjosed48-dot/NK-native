"""Utilidades ráster: lectura, máscaras por polígono, escritura y agregación."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from affine import Affine
from rasterio.crs import CRS
from rasterio.features import geometry_mask
from shapely.geometry import box

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


def validar_poligono(
    gdf: gpd.GeoDataFrame,
    crs_raster: CRS | None,
    ruta: str | Path,
    bounds_raster: tuple[float, float, float, float] | None = None,
) -> gpd.GeoDataFrame:
    """Valida defensivamente un polígono antes de usarlo como máscara.

    Comprueba:
      1. Que ``gdf.crs`` no sea ``None``.
      2. Que el CRS del polígono sea compatible con el del ráster (se
         reproyecta si es necesario).
      3. Que, tras reproyectar, los bounds del polígono intersecten los
         bounds del ráster de referencia. Si la intersección es vacía se
         lanza ``ValueError`` con ambos bounds y la ruta.

    Devuelve el GeoDataFrame (reproyectado al CRS del ráster si aplicaba).
    """
    ruta_str = str(ruta)

    if gdf.crs is None:
        raise ValueError(
            f"El polígono '{ruta_str}' no tiene CRS definido. "
            f"Asigne un CRS (p. ej. EPSG:32719) antes de usarlo."
        )

    gdf_valido = gdf
    if crs_raster is not None and gdf.crs != crs_raster:
        try:
            gdf_valido = gdf.to_crs(crs_raster)
        except Exception as error:  # noqa: BLE001
            raise ValueError(
                f"No se pudo reproyectar el polígono '{ruta_str}' "
                f"de {gdf.crs} a {crs_raster}: {error}"
            ) from error

    if bounds_raster is not None:
        # Bounds del polígono en el CRS del ráster (ya reproyectado si hizo falta).
        minx, miny, maxx, maxy = gdf_valido.total_bounds
        r_left, r_bottom, r_right, r_top = bounds_raster

        # Comprobación de intersección de rectángulos.
        intersecta = not (
            maxx < r_left or minx > r_right or maxy < r_bottom or miny > r_top
        )
        if not intersecta:
            raise ValueError(
                f"El polígono '{ruta_str}' no intersecta el ráster de referencia.\n"
                f"  Bounds del polígono ({gdf_valido.crs}): "
                f"({minx:.3f}, {miny:.3f}, {maxx:.3f}, {maxy:.3f})\n"
                f"  Bounds del ráster ({crs_raster}): "
                f"({r_left:.3f}, {r_bottom:.3f}, {r_right:.3f}, {r_top:.3f})"
            )

    return gdf_valido


def bounds_raster_desde_transform(
    transform: Affine, shape: tuple[int, int]
) -> tuple[float, float, float, float]:
    """Devuelve (left, bottom, right, top) de un ráster desde su transform y shape."""
    left = transform.c
    top = transform.f
    right = left + shape[1] * transform.a
    bottom = top + shape[0] * transform.e  # e suele ser negativo (norte arriba)
    return (left, bottom, right, top)


def polygon_mask(
    polygon_path: str | Path,
    shape: tuple[int, int],
    transform: Affine,
    crs: CRS | None,
    bounds_raster: tuple[float, float, float, float] | None = None,
) -> np.ndarray:
    """Máscara booleana True dentro de los polígonos (reproyectados si hace falta).

    Valida defensivamente el polígono (CRS e intersección con el ráster)
    antes de calcular la máscara.
    """
    polygons = gpd.read_file(polygon_path)

    if bounds_raster is None:
        bounds_raster = bounds_raster_desde_transform(transform, shape)

    polygons = validar_poligono(polygons, crs, polygon_path, bounds_raster)

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
