# LLM_CONTEXT — NK-native

Este archivo es una copia de contexto rápido para retomar el proyecto con un LLM.  
Contenido completo en: `docs/memoria/PROJECT_MEMORY.md`.

## Estado actual
- **Proyecto:** co-registro Nuth & Kääb + deramp + DoD de DEMs glaciares (Python 3.12).
- **Pipeline:** `00`→`04` funcional, más `05-preinforme` (dossier PDF de revisión). Resultados generados y documentación cerrada; listo para GitHub.
- **Salvedades resueltas:**
  1. Validación defensiva de CRS de polígonos en `nkdem/raster.py` (`validar_poligono`) y comprobación `glaciar_mask.sum() > 0` en `scripts/03-DoD.py`.
  2. Docstring extendido de la CV espacial con `numpy.linalg.lstsq` en `scripts/02-NK-Variantes.py` y test de equivalencia ejecutable vs `xdem.coreg.Deramp` (`tests/test_cv_equivalence.py`).
  3. Propagación de error por variograma en `nkdem/stats.py` (`estimar_n_eff`), usada en `scripts/03-DoD.py` con fallback documentado a `n_eff_fraction`.
- **Pendientes:**
  1. Redactar el informe final `report/report_final.md` (insumos ya reunidos en `report/preinforme.pdf`).
  2. Crear el repo en GitHub y hacer el push (ver más abajo).
- **Ubicación:** `/Users/eguivar/Documents/dev/NK-native`
- **Rama git:** `main`, último commit `75aadaf`; árbol limpio (solo quedan directorios de salida ignorados). Remoto sin configurar.
- **Tests:** **21 tests pasando** en 5 archivos (`pytest tests/`). `py_compile` OK.

## Estructura clave
- `nkdem/` — paquete compartido: `config.py`, `raster.py` (incluye `validar_poligono`), `stats.py` (incluye `nmad` y `estimar_n_eff`), `io.py`.
- `scripts/` — pipeline `00-check-input` → `04-report`, más `05-preinforme` (auxiliar, requiere `reportlab`).
- `tests/` — `test_config.py`, `test_stats.py`, `test_cv_equivalence.py`, `test_n_eff.py`, `test_validacion_poligono.py`.
- `config.toml` — parámetros por defecto (versionado).
- `config.local.toml` — rutas absolutas de esta MAC (IGNORADO por git).
- `data/*.gpkg` — polígonos de apoyo (versionados, <1 MB).
- Rásteres `.tif`, CSVs de resultados y `report/` (figuras, tablas, `preinforme.pdf`): **NO se versionan**.

## Cómo ejecutar
```bash
source .venv/bin/activate
python scripts/00-check-input.py
python scripts/01-nuth-kaab.py
python scripts/02-NK-Variantes.py
python scripts/03-DoD.py
python scripts/04-report.py
python scripts/05-preinforme.py   # opcional/auxiliar: dossier PDF de revisión
pytest tests/
```

## Informe
- `report/preinforme.pdf` — dossier de revisión generado por `05-preinforme.py` (tablas T3–T5, figuras F1–F9, pendientes). **No** es el informe final y no se versiona.
- `report/report_final.md` — **pendiente de redacción**.
- `report/tables/T6_report_main.md` — tablas T3–T5 consolidadas en markdown.

## Resultados de referencia
- Volumen glaciar vs 2025 — Opción B (todo NK): 2017 **+1.751×10⁶ m³**, 2018 **+1.572×10⁶ m³**, 2023 **+0.738×10⁶ m³**. Opción A (mixta, 2018 con deramp3): 2018 **+1.375×10⁶ m³** (−12,5 %).
- NMAD final en zona estable: 2017 **0.471 m** (NK), 2018 **0.321 m** (deramp3, CV lo acepta), 2023 **0.143 m** (NK).
- Convención de signo: `dH = DEM_año − DEM_2025`; volumen positivo = pérdida de masa.

## Regla de oro
Nunca hardcodear rutas absolutas. Usar siempre:
```python
from nkdem.config import load_config
cfg = load_config()
cfg.reference_dem, cfg.dem("2017"), cfg.nk_dem("2018"), cfg.dod_dir, ...
```
(Excepción documentada: `scripts/05-preinforme.py` usa rutas relativas a `report/` y debe lanzarse desde la raíz del repo.)

## Push a GitHub (pendiente)
```bash
git remote add origin https://github.com/eguivar/NK-native.git
git branch -M main
git push -u origin main
```

## Archivo completo
Ver `docs/memoria/PROJECT_MEMORY.md` (parámetros, métricas, reglas, estructura de directorios, stack, sección "Decisiones de diseño") y `docs/memoria/00-AUDITORIA.md`.
