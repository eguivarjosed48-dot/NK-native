import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon

from nkdem.raster import validar_poligono

CRS_RASTER = "EPSG:32719"
RUTA_EJEMPLO = "data/glaciar_2017.gpkg"

# Bounds del ráster de referencia (sintéticos, en metros UTM 32719).
BOUNDS_RASTER = (574800.0, 8224800.0, 575450.0, 8225250.0)


def _gdf_crs_none():
    """GeoDataFrame sin CRS (debe lanzar ValueError)."""
    poly = Polygon([(575000, 8225000), (575010, 8225000),
                    (575010, 8225010), (575000, 8225010)])
    gdf = gpd.GeoDataFrame(geometry=[poly], crs=None)
    return gdf


def _gdf_dentro_bounds():
    """GeoDataFrame con CRS correcto y dentro de los bounds del ráster."""
    poly = Polygon([(575000, 8225000), (575010, 8225000),
                    (575010, 8225010), (575000, 8225010)])
    gdf = gpd.GeoDataFrame(geometry=[poly], crs=CRS_RASTER)
    return gdf


def _gdf_fuera_bounds():
    """GeoDataFrame con CRS correcto pero fuera de los bounds del ráster."""
    poly = Polygon([(600000, 8250000), (600010, 8250000),
                    (600010, 8250010), (600000, 8250010)])
    gdf = gpd.GeoDataFrame(geometry=[poly], crs=CRS_RASTER)
    return gdf


def test_crs_none_lanza_valueerror():
    gdf = _gdf_crs_none()
    try:
        validar_poligono(gdf, CRS_RASTER, RUTA_EJEMPLO, BOUNDS_RASTER)
    except ValueError as error:
        assert "no tiene CRS definido" in str(error)
        assert RUTA_EJEMPLO in str(error)
    else:  # pragma: no cover
        raise AssertionError("Se esperaba ValueError por CRS None")


def test_poligono_dentro_bounds_pasa():
    gdf = _gdf_dentro_bounds()
    resultado = validar_poligono(gdf, CRS_RASTER, RUTA_EJEMPLO, BOUNDS_RASTER)
    assert resultado.crs == CRS_RASTER


def test_poligono_fuera_bounds_lanza_valueerror():
    gdf = _gdf_fuera_bounds()
    try:
        validar_poligono(gdf, CRS_RASTER, RUTA_EJEMPLO, BOUNDS_RASTER)
    except ValueError as error:
        assert "no intersecta el ráster de referencia" in str(error)
        assert RUTA_EJEMPLO in str(error)
        assert "Bounds del polígono" in str(error)
        assert "Bounds del ráster" in str(error)
    else:  # pragma: no cover
        raise AssertionError("Se esperaba ValueError por polígono fuera de bounds")


def test_reproyeccion_si_crs_diferente():
    """Un polígono en EPSG:4326 dentro del área se reproyecta y valida."""
    # Un pequeño polígono en grados cercanísimo al área (aprox. 575000 E, 8225000 N).
    # Como 4326 es grados, usamos un punto que tras reproyectar caiga dentro.
    from pyproj import Transformer

    transformer = Transformer.from_crs("EPSG:4326", CRS_RASTER, always_xy=True)
    # Tomamos un punto conocido dentro del bounds y lo convertimos a 4326.
    x_utm, y_utm = 575005.0, 8225005.0
    lon, lat = transformer.transform(x_utm, y_utm, direction="INVERSE")
    poly = Polygon([(lon, lat), (lon + 1e-5, lat),
                    (lon + 1e-5, lat + 1e-5), (lon, lat + 1e-5)])
    gdf = gpd.GeoDataFrame(geometry=[poly], crs="EPSG:4326")
    resultado = validar_poligono(gdf, CRS_RASTER, RUTA_EJEMPLO, BOUNDS_RASTER)
    assert resultado.crs == CRS_RASTER
