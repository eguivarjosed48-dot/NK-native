"""
Genera data/glaciar_2017.gpkg a partir del shapefile fuente de este equipo.

La ruta del shapefile fuente es local (config.local.toml) y no se versiona.
"""

from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nkdem.config import load_config  # noqa: E402

cfg = load_config()

source_shp = Path(
    "/Users/eguivar/Documents/2-2026/dron_ortofoto_dem_v4_completo/"
    "poligono_glaciar_v3/glaciar_contorno_2017.shp"
)

if not source_shp.exists():
    print(f"No se encontró el shapefile fuente: {source_shp}")
    print("Puedes crear data/glaciar_2017.gpkg manualmente con CRS EPSG:32719.")
    raise SystemExit(0)

gdf = gpd.read_file(source_shp)
gdf = gdf.set_crs("EPSG:32719", allow_override=True)
gdf.to_file(cfg.glacier_polygon, driver="GPKG")
print(f"Guardado con CRS: {gdf.crs} -> {cfg.glacier_polygon}")
