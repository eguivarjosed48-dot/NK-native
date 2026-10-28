"""
Genera data/glaciar_2017.gpkg a partir del shapefile fuente (ruta local).

La ruta del shapefile no se versiona. Se resuelve, por orden:

1. el primer argumento de la línea de comandos;
2. la variable de entorno ``NK_GLACIER_SHP``;
3. el candidato por defecto dentro de la carpeta de DEMs configurada
   (``<dem_dir>/poligono_glaciar_v3/glaciar_contorno_2017.shp``), que es la
   disposición habitual del conjunto de datos de origen.

Uso:
    python scripts/test.py [ruta/al/glaciar_contorno_2017.shp]
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import geopandas as gpd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nkdem.config import load_config  # noqa: E402

CRS_PROYECTO = "EPSG:32719"
NOMBRE_SHAPEFILE = "glaciar_contorno_2017.shp"


def resolver_shapefile(cfg) -> Path | None:
    """Devuelve la ruta del shapefile fuente o ``None`` si no hay candidato."""
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).expanduser()

    desde_entorno = os.environ.get("NK_GLACIER_SHP")
    if desde_entorno:
        return Path(desde_entorno).expanduser()

    candidato = cfg.dem_dir / "poligono_glaciar_v3" / NOMBRE_SHAPEFILE
    return candidato if candidato.exists() else None


def main() -> None:
    cfg = load_config()

    source_shp = resolver_shapefile(cfg)
    if source_shp is None or not source_shp.exists():
        print("No se encontró el shapefile fuente del glaciar.")
        if source_shp is not None:
            print(f"  Ruta probada: {source_shp}")
        print(
            "Indica la ruta de una de estas formas:\n"
            "  python scripts/test.py ruta/al/glaciar_contorno_2017.shp\n"
            "  NK_GLACIER_SHP=ruta/al/glaciar_contorno_2017.shp python scripts/test.py"
        )
        print(
            "Alternativamente, crea data/glaciar_2017.gpkg manualmente con CRS "
            f"{CRS_PROYECTO}."
        )
        raise SystemExit(0)

    gdf = gpd.read_file(source_shp)
    gdf = gdf.set_crs(CRS_PROYECTO, allow_override=True)
    gdf.to_file(cfg.glacier_polygon, driver="GPKG")
    print(f"Guardado con CRS {gdf.crs}: {cfg.glacier_polygon}")


if __name__ == "__main__":
    main()
