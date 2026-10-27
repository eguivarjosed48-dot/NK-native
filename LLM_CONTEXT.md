# LLM_CONTEXT — NK-native

Este archivo es una copia de contexto rápido para retomar el proyecto con un LLM.  
Contenido completo en: `docs/memoria/PROJECT_MEMORY.md`.

## Resumen ejecutivo
- **Proyecto:** co-registro Nuth & Kääb + deramp + DoD de DEMs glaciares (Python 3.12).
- **Estado:** pipeline 00→04 funcional, resultados generados, listo para GitHub.
- **Ubicación:** `/Users/eguivar/Documents/dev/NK-native`
- **Rama git:** `main`, commit `f1e6069`, sin remoto configurado aún.

## Estructura clave
- `nkdem/` — paquete compartido (config, raster, stats, io).
- `scripts/` — pipeline 00-check-input → 04-report.
- `config.toml` — parámetros por defecto (versionado).
- `config.local.toml` — rutas absolutas de esta MAC (IGNORADO por git).
- `data/*.gpkg` — polígonos de apoyo (versionados, <1 MB).
- Rásteres `.tif` y CSVs de salida: **NO se versionan**.

## Cómo ejecutar
```bash
source .venv/bin/activate
python scripts/00-check-input.py
python scripts/01-nuth-kaab.py
python scripts/02-NK-Variantes.py
python scripts/03-DoD.py
python scripts/04-report.py
pytest tests/
```

## Regla de oro
Nunca hardcodear rutas absolutas. Usar siempre:
```python
from nkdem.config import load_config
cfg = load_config()
cfg.reference_dem, cfg.dem("2017"), cfg.nk_dem("2018"), cfg.dod_dir, ...
```

## Push a GitHub (pendiente)
```bash
git remote add origin https://github.com/eguivar/NK-native.git
git branch -M main
git push -u origin main
```

## Archivo completo
Ver `docs/memoria/PROJECT_MEMORY.md` (parámetros, métricas, reglas, estructura de directorios, stack).
