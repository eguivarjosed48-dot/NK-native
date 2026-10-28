# NK-native

Co-registro y diferencia de elevación (DoD) de modelos digitales de elevación
(DEM) de un glaciar, usando el método de **Nuth & Kääb** con auto-ajuste
(deramp) y validación cruzada espacial. Proyecto académico de replicabilidad.

> ⚠️ Los rásteres fuente (DEMs crudos y derivados) **no se versionan** en este
> repositorio por su peso (~2.8 GB). Solo se versionan el código, la
> configuración, los polígomos de apoyo (`data/*.gpkg`) y los resultados
> ligeros (tablas y figuras del informe).

## Estructura

```
NK-native/
├── config.toml             # configuración portable (valores por defecto)
├── config.local.toml       # rutas locales de esta máquina (IGNORADO por git)
├── requirements.txt        # entorno Python replicable
├── README.md
├── LICENSE
├── .gitignore
├── .gitattributes
├── nkdem/                  # paquete de utilidades compartidas
│   ├── __init__.py
│   ├── config.py           # resolución de rutas y parámetros
│   ├── io.py               # lectura/escritura CSV
│   ├── raster.py           # lectura/máscara/escritura de GeoTIFF
│   └── stats.py            # NMAD, diferencias, polinomios, bloques CV
├── scripts/                # pipeline por pasos (00 → 04 + pruebas)
│   ├── 00-check-input.py
│   ├── 01-nuth-kaab.py
│   ├── 02-deramp-autotune.py
│   ├── 02-NK-Variantes.py
│   ├── 03-DoD.py
│   ├── 04-report.py
│   ├── 05-preinforme.py    # dossier PDF de revisión (auxiliar)
│   ├── test.py
│   └── test_glaciar_vs_estable.py
├── tests/                  # pruebas unitarias (21 tests)
│   ├── test_config.py
│   ├── test_stats.py
│   ├── test_cv_equivalence.py
│   ├── test_n_eff.py
│   └── test_validacion_poligono.py
├── data/                   # polígomos de apoyo (versionados, <1 MB)
│   ├── glaciar_2017.gpkg
│   └── stable_terrain.gpkg
├── docs/
│   └── memoria/            # archivos de auditoría y memoria del proyecto
│       ├── 00-AUDITORIA.md
│       └── ...
├── dems_alineados/         # generado (no se sube)
├── dems_nk/                # generado (no se sube)
├── dems_variants/          # generado (no se sube)
├── dod/                    # generado (no se sube)
├── test_outputs/           # generado (no se sube)
└── report/                 # generado (no se sube)
```

## Requisitos

Python 3.12 y las librerías de `requirements.txt`. El entorno de desarrollo
de este proyecto es `.venv/` (creado con `python -m venv .venv`).

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Datos fuente

Los DEMs crudos viven fuera del repositorio (ruta local en
`config.local.toml`):

```
data/raw/dems/<año>/<año>_DSM.tif     # p. ej. 2025_B/2025_B_DSM.tif
```

Define tus rutas en `config.local.toml` (ejemplo):

```toml
[input]
dem_dir = "/ruta/a/tus/dems"
reference_dem = "/ruta/a/tus/dems/2025_B/2025_B_DSM.tif"
```

O bien usa variables de entorno, p. ej. `NK_DEM_DIR`.

## Ejecutar el pipeline

Desde la raíz del repositorio, con el entorno activado:

```bash
python scripts/00-check-input.py   # Paso 0: alinea DEMs a la cuadrícula 2025
python scripts/01-nuth-kaab.py     # Paso 1: co-registro Nuth & Kääb
python scripts/02-NK-Variantes.py  # Paso 2: variantes (NK / deramp3 / deramp-CV)
python scripts/03-DoD.py           # Paso 3: DEM of Difference
python scripts/04-report.py        # Paso 4: figuras y tablas del informe
python scripts/05-preinforme.py    # Paso 5 (aux): dossier PDF de revisión
```

Los pasos 2 (`02-deramp-autotune.py`) y las pruebas (`test.py`,
`test_glaciar_vs_estable.py`) son opcionales / de diagnóstico. El Paso 5
requiere `reportlab` (incluido en `requirements.txt`) y debe lanzarse desde la
raíz del repo; genera `report/preinforme.pdf`.

Ejecutar pruebas unitarias:

```bash
pytest tests/
```

## Resultados y replicabilidad

- `coreg_variants_summary.csv` — comparación de variantes de co-registro.
- `dod_summary.csv` — métricas del DoD por año y opción (A/B).
- `report/tables/T6_report_main.md` — informe consolidado en Markdown.
- `report/figures/` — figuras F1–F9 del análisis.
- `report/dod_geotiffs/` — GeoTIFFs del DoD (copia local, no se sube).
- `report/preinforme.pdf` — dossier de revisión con tablas, figuras y pendientes
  (no es el informe final; tampoco se sube).

Todos los archivos de salida son **regenerables** ejecutando los scripts
desde cero; por eso no se versionan.

## Archivos de memoria / auditoría

Ver `docs/memoria/`:
- `00-AUDITORIA.md` — diagnóstico del estado inicial del proyecto.

## Licencia

MIT — véase `LICENSE`.
