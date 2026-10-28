# LLM_CONTEXT — NK-native

Este archivo es una copia de contexto rápido para retomar el proyecto con un LLM.  
Contenido completo en: `docs/memoria/PROJECT_MEMORY.md`.

## Estado actual
- **Proyecto:** co-registro Nuth & Kääb + deramp + DoD de DEMs glaciares (Python 3.12).
- **Pipeline:** `00`→`05` completo y verificado de extremo a extremo; resultados regenerados el 2026-10-28 e **informe final redactado** (`report/report_final.md`, formato de artículo científico).
- **Salvedades resueltas:**
  1. Validación defensiva de CRS de polígonos en `nkdem/raster.py` (`validar_poligono`) y comprobación de máscara vacía en `scripts/03-DoD.py`.
  2. CV espacial vectorizada con `numpy.linalg.lstsq` en `scripts/02-NK-Variantes.py`, con test de equivalencia ejecutable vs `xdem.coreg.Deramp` (`tests/test_cv_equivalence.py`).
  3. Propagación de error por variograma (`nkdem/stats.py::estimar_n_eff`), ahora aplicada al **residual de terreno estable** y no al DoD del glaciar.
  4. **Bug corregido (2026-10-28):** el Paso 2 no era ejecutable (desempaquetado erróneo de `load_dem_with_mask`) y `deramp3.fit(dem, dem)` ajustaba el polinomio contra sí mismo (corrección nula). Cubierto por `tests/test_deramp_semantics.py`. El deramp se ajusta siempre como `fit(referencia, dem)`.
- **Pendientes:** publicar en GitHub y completar los metadatos del Apéndice A del informe (afiliación, topónimo del glaciar, fechas/sensor de los vuelos, licencia).
- **Ubicación:** `/Users/eguivar/Documents/dev/NK-native`
- **Rama git:** `main`; remoto `origin` = `git@github.com:eguivarjosed48-dot/NK-native.git` (público, CI en verde, tag `v0.1.0`).
- **Tests:** **28 tests pasando** en 7 archivos (`pytest tests/`). `py_compile` OK.

## Estructura clave
- `nkdem/` — paquete compartido: `config.py`, `raster.py` (`validar_poligono`), `stats.py` (`nmad`, `estimar_n_eff`), `deramp.py` (deramp polinómico por bloques), `io.py`.
- `scripts/` — pipeline `00-check-input` → `04-report`, más `05-preinforme` (auxiliar, requiere `reportlab`).
- `tests/` — `test_config.py`, `test_stats.py`, `test_cv_equivalence.py`, `test_n_eff.py`, `test_validacion_poligono.py`, `test_deramp.py`, `test_deramp_semantics.py`.
- `report/report_final.md` — informe final (único archivo versionado de `report/`).
- `config.toml` — parámetros por defecto (versionado).
- `config.local.toml` — rutas absolutas de esta MAC (IGNORADO por git).
- `data/*.gpkg` — polígonos de apoyo (versionados, <1 MB).
- Rásteres `.tif`, CSVs de resultados y el resto de `report/` (figuras, tablas, `preinforme.pdf`): **NO se versionan**.

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
- `report/report_final.md` — informe final en formato de artículo (resumen, métodos, resultados, discusión, conclusiones, referencias, apéndice de metadatos pendientes).
- `report/preinforme.pdf` — dossier de revisión generado por `05-preinforme.py`. No es el informe final y no se versiona.
- `report/tables/T6_report_main.md` — tablas T3–T5 consolidadas en markdown.

## Resultados de referencia (regenerados el 2026-10-28)
- Volumen glaciar vs 2025 — Opción B (todo NK): 2017 **+1,751×10⁶ m³**, 2018 **+1,572×10⁶ m³**, 2023 **+0,738×10⁶ m³** (pérdida de masa).
- Tasas: **1,22 / 1,28 / 2,00 m a⁻¹** (Δt = 8 / 7 / 2 a); balance específico 1,04 / 1,09 / 1,70 m w.e. a⁻¹ (ρ = 850 kg m⁻³).
- NMAD final en terreno estable: **0,471 / 0,372 / 0,143 m**.
- **La CV rechaza el deramp en los tres años** (mejora *in-sample* pero no fuera de muestra) → Opción A = Opción B. Sensibilidad con deramp3 forzado (Opción C): **−5,2 % / −12,5 % / −5,3 %**.
- σ_V (ruido del co-registro): 1.651 / 618 / 437 m³ (0,04–0,09 %); incertidumbre total estimada 10–15 %.
- Convención de signo: `dH = DEM_año − DEM_2025`; volumen positivo = pérdida de masa.

## Regla de oro
Nunca hardcodear rutas absolutas. Usar siempre:
```python
from nkdem.config import load_config
cfg = load_config()
cfg.reference_dem, cfg.dem("2017"), cfg.nk_dem("2018"), cfg.dod_dir, ...
```
(Excepción documentada: `scripts/05-preinforme.py` usa rutas relativas a `report/` y debe lanzarse desde la raíz del repo.)

Además: el deramp se ajusta **siempre** contra la referencia (`fit(ref, dem)`); `fit(dem, dem)` produce una corrección nula (ver `tests/test_deramp_semantics.py`).

## GitHub (publicado el 2026-10-28)
Repositorio público: <https://github.com/eguivarjosed48-dot/NK-native>  
Rama `main` + tag `v0.1.0`; CI (pytest) en verde.
```bash
git push origin main          # futuros cambios
git push origin --tags
```

## Archivo completo
Ver `docs/memoria/PROJECT_MEMORY.md` (parámetros, métricas, reglas, estructura de directorios, stack, sección "Decisiones de diseño") y `docs/memoria/00-AUDITORIA.md`.
