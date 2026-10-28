# 🧠 MEMORIA DEL PROYECTO — NK-native

> Archivo de contexto para retomar este proyecto con un LLM en una sesión futura.  
> Úsalo como "system prompt" o léelo al inicio de cada nueva conversación sobre este repo.

---

## 1. Visión general

**Nombre:** NK-native  
**Autor:** Jose Mauricio Eguivar Duran (eguivar.jose.d48@gmail.com)  
**Fecha de creación:** 2026-10-27  
**Última actualización:** 2026-10-28  
**Ubicación:** `/Users/eguivar/Documents/dev/NK-native`  
**Estado:** Pipeline 00→05 completo, reproducible y verificado de extremo a extremo; resultados regenerados el 2026-10-28 e informe final redactado (`report/report_final.md`). Pendiente: publicar en GitHub.

**Qué hace:** Co-registro y diferencia de elevación (DoD) de modelos digitales de elevación (DEM) de un glaciar.  
**Método principal:** Nuth & Kääb (NK) con auto-ajuste (deramp, polinomio grado 3) y validación cruzada espacial bloqueada (CV vectorizada con numpy).  
**Objetivo:** Estimar volúmenes de cambio glaciar 2017/2018/2023 vs referencia 2025 sobre el polígono del glaciar 2017.

---

## 2. Estructura del repositorio

```
NK-native/
├── config.toml              # Config portable (valores por defecto). VERSIONADO.
├── config.local.toml        # Rutas absolutas de ESTA máquina. IGNORADO por git.
├── requirements.txt         # Entorno Python replicable (pip freeze del .venv).
├── README.md
├── LICENSE
├── .gitignore               # Ignora .venv, rásteres derivados, CSVs de salida, config.local.toml
├── .gitattributes
├── nkdem/                   # Paquete de utilidades compartidas (versión 0.1.0)
│   ├── __init__.py
│   ├── config.py            # load_config(): resuelve rutas y parámetros
│   ├── io.py                # leer_csv / write_csv
│   ├── raster.py            # lectura/máscara por polígono/escritura GeoTIFF
│   ├── deramp.py            # deramp polinómico por bloques (memoria acotada)
│   └── stats.py             # nmad(), diferencia_stats(), polinomios, bloques CV
├── scripts/                 # Pipeline por pasos (ejecutar en orden)
│   ├── 00-check-input.py    # Paso 0: alinea DEMs a cuadrícula 2025 -> dems_alineados/
│   ├── 01-nuth-kaab.py      # Paso 1: co-registro NK -> dems_nk/ + coreg_nk_summary.csv
│   ├── 02-deramp-autotune.py# Paso 2 (alt): deramp auto-tune -> dems_deramped/
│   ├── 02-NK-Variantes.py   # Paso 2 (principal): NK | deramp3 | deramp-CV -> dems_variants/ + coreg_variants_summary.csv
│   ├── 03-DoD.py            # Paso 3: DEM of Difference -> dod/ + dod_summary.csv + dod_figures/
│   ├── 04-report.py         # Paso 4: figuras F1-F9 + tablas T3-T6 -> report/
│   ├── 05-preinforme.py     # Paso 5 (auxiliar): dossier PDF de revisión -> report/preinforme.pdf
│   ├── test.py              # Crea data/glaciar_2017.gpkg desde shapefile fuente local
│   └── test_glaciar_vs_estable.py # Diagnóstico glaciar vs zona estable -> test_outputs/
├── conftest.py              # pytest: añade la raíz del repo a sys.path
├── tests/                   # Pruebas unitarias (pytest) — 28 tests
│   ├── test_config.py               # load_config(): rutas y parámetros
│   ├── test_stats.py                # nmad(), diferencia_stats(), polinomios
│   ├── test_cv_equivalence.py       # equivalencia CV numpy vs xdem.coreg.Deramp
│   ├── test_n_eff.py                # estimar_n_eff() y ajuste de variograma
│   ├── test_validacion_poligono.py  # validar_poligono(): CRS de polígonos
│   ├── test_deramp.py               # ajuste/aplicación del deramp por bloques
│   └── test_deramp_semantics.py     # semántica de Deramp.fit(ref, dem) vs fit(dem, dem)
├── data/                    # Polígonos de apoyo (pequeños, VERSIONADOS)
│   ├── glaciar_2017.gpkg
│   └── stable_terrain.gpkg
├── docs/memoria/            # Archivos de memoria para LLM / auditoría
│   ├── PROJECT_MEMORY.md    # este archivo
│   ├── 00-AUDITORIA.md      # diagnóstico del estado inicial y hallazgos
│   └── 01-PLAN-GITHUB.md    # pasos para publicar en GitHub
└── (directorios generados, NO se suben a git)
    ├── dems_alineados/
    ├── dems_nk/
    ├── dems_variants/
    ├── dod/
    ├── dod_figures/
    ├── test_outputs/
    └── report/  (figures/, tables/, dod_geotiffs/, preinforme.pdf)
```

**Regla de oro:** los rásteres (.tif) y los CSVs de resultados no se versionan. Tamaño estimado del repo versionable: < 5 MB.

---

## 3. Stack tecnológico

- **Python:** 3.12.1 (entorno `.venv/` creado con `python -m venv .venv`)
- **Gestor de paquetes:** pip + `requirements.txt` (generado con `pip freeze`)
- **Librerías clave y versiones:**
  - `numpy==2.5.4`, `rasterio==1.5.2`, `geopandas==1.2.0`, `xdem==0.2.3`
  - `geoutils==0.2.5`, `rioxarray==0.23.0`, `scipy==1.18.1`, `matplotlib==3.11.2`
  - `pandas==2.3.3`, `shapely==2.2.0`, `pyproj==3.8.0`, `pillow==13.0.0`
  - `reportlab==5.1.0` — solo para el Paso 5 (dossier PDF de revisión)
- **Pruebas:** `pytest>=8.0`

---

## 4. Configuración y rutas (importante)

Las rutas absolutas de esta máquina viven **únicamente** en `config.local.toml` (ignorado por git):

```toml
[input]
dem_dir = "/Users/eguivar/Documents/2-2026/dron_ortofoto_dem_v4_completo"
reference_dem = "/Users/eguivar/Documents/2-2026/dron_ortofoto_dem_v4_completo/2025_B/2025_B_DSM.tif"
```

En cualquier otra máquina:
1. Crear `config.local.toml` con las rutas propias.
2. O usar variables de entorno: `NK_DEM_DIR`, `NK_REFERENCE_DEM`, `NK_STABLE_TERRAIN`, `NK_GLACIER_POLYGON`.
3. Los valores por defecto portables están en `config.toml`.

En el código, nunca usar rutas absolutas hardcodeadas. Siempre:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nkdem.config import load_config
cfg = load_config()
# rutas resueltas:
cfg.reference_dem
cfg.dem("2017")
cfg.nk_dem("2018")
cfg.variant_dem("2023", "NK")
cfg.dod_dir
cfg.stable_terrain
cfg.glacier_polygon
```

---

## 5. Pipeline (orden de ejecución recomendado)

Desde la raíz con el entorno activado (`source .venv/bin/activate`):

| Paso | Script | Entrada clave | Salida |
|------|--------|---------------|--------|
| 0 | `scripts/00-check-input.py` | DEMs crudos (`data/raw/dems/`) | `dems_alineados/dem_<year>_aligned.tif` |
| 1 | `scripts/01-nuth-kaab.py` | `dems_alineados/`, `data/stable_terrain.gpkg` | `dems_nk/dem_<year>_nk.tif` |
| 2 | `scripts/02-NK-Variantes.py` | `dems_nk/` | `dems_variants/<year>_{NK,deramp3,derampCV}.tif` + `coreg_variants_summary.csv` |
| 3 | `scripts/03-DoD.py` | `dems_variants/`, `data/glaciar_2017.gpkg` | `dod/<year>_vs_2025_{A,B,C}.tif` + `dod_summary.csv` |
| 4 | `scripts/04-report.py` | salidas anteriores | `report/figures/F1-F9.png`, `report/tables/T3-T6.md/csv` |
| 5 (aux) | `scripts/05-preinforme.py` | `report/tables/T3-T5.csv`, `report/figures/F1-F9.png` | `report/preinforme.pdf` (dossier de revisión) |

Scripts opcionales/diagnóstico: `scripts/02-deramp-autotune.py`, `scripts/test.py`, `scripts/test_glaciar_vs_estable.py`.

El Paso 5 es **auxiliar**: no produce resultados científicos nuevos, solo empaqueta lo ya
generado por 00→04 en un PDF revisable. Requiere `reportlab` y debe ejecutarse desde la raíz
del repo (usa rutas relativas `report/`, `report/tables/`, `report/figures/`; no usa `load_config`).

El Paso 3 calcula tres opciones de DoD: **B** (principal, todo NK), **A** (variante aceptada por
la CV del Paso 2, leída de `coreg_variants_summary.csv`) y **C** (deramp3 forzado en todos los
años, usada como análisis de sensibilidad).

Nota sobre scripts legacy: `scripts/02-deramp-autotune.py` es la versión anterior del Paso 2
(deramp polinómico sin validación cruzada espacial ni variantes NK/deramp3/derampCV). Se conserva
como referencia histórica y para experimentos que no requieran CV. El pipeline principal usa
`scripts/02-NK-Variantes.py`. Los scripts `scripts/test.py` y
`scripts/test_glaciar_vs_estable.py` son utilidades de diagnóstico, no forman parte del
pipeline principal.

Pruebas unitarias: `pytest tests/`

---

## 6. Parámetros metodológicos clave

Definidos en `config.toml` sección `[params]`:

| Parámetro | Valor | Uso |
|-----------|-------|-----|
| `reference_year` | `"2025"` | DEM de referencia / cuadrícula maestra |
| `years` | `["2017", "2018", "2023"]` | Años a comparar vs 2025 |
| `nk_subsample` | `0.2` | Submuestreo Nuth & Kääb (ahorra RAM) |
| `poly_order` | `3` | Grado del polinomio deramp |
| `cv_n_blocks` | `4` | CV espacial 4×4 (leave-one-block-out) |
| `cv_min_pixels_per_block` | `2000` | Mínimo píxeles por bloque test |
| `cv_max_train_pixels` | `200000` | Máximo píxeles de entrenamiento por fold |
| `random_seed` | `42` | Semilla aleatoria |
| `n_eff_fraction` | `0.05` | Fracción de píxeles efectivos para σ_V |
| `map_downsample` | `4` | Factor de downsample para figuras |
| `vmin_pct` / `vmax_pct` | `2` / `98` | Recorte visual de mapas |
| `n_hyps_bins` | `20` | Franjas altitudinales hipsometría |

CRS de todo el proyecto: **EPSG:32719** (UTM zona 19S). Resolución DEM: **0.1 m**.

---

## 7. Resultados ya generados (métricas clave)

DoD — Volumen de cambio (glaciar 2017 vs 2025):

| Año | Opción B (todo NK) | Opción A (según CV) | Opción C (deramp3 forzado) | ΔV C−B |
|-----|--------------------|---------------------|-----------------------------|--------|
| 2017 | +1.751 × 10⁶ m³ | +1.751 × 10⁶ m³ | +1.660 × 10⁶ m³ | −0.091 × 10⁶ m³ (−5,2 %) |
| 2018 | +1.572 × 10⁶ m³ | +1.572 × 10⁶ m³ | +1.375 × 10⁶ m³ | −0.197 × 10⁶ m³ (−12,5 %) |
| 2023 | +0.738 × 10⁶ m³ | +0.738 × 10⁶ m³ | +0.699 × 10⁶ m³ | −0.039 × 10⁶ m³ (−5,3 %) |

Tasas (Δt = 8 / 7 / 2 años): adelgazamiento medio 1.22 / 1.28 / 2.00 m a⁻¹; balance específico
1.04 / 1.09 / 1.70 m w.e. a⁻¹ con ρ = 850 kg m⁻³ (Huss, 2013).

NMAD en zona estable (co-registro):

| Año | NK | deramp3 (*in-sample*) | CV deramp3 | CV NK | CV acepta | NMAD final |
|-----|-----|------------------------|------------|-------|-----------|------------|
| 2017 | 0.471 m | 0.411 m | 0.486 m | 0.449 m | No | 0.471 m |
| 2018 | 0.372 m | 0.321 m | 0.359 m | 0.359 m | No | 0.372 m |
| 2023 | 0.143 m | 0.211 m | 0.251 m | 0.143 m | No | 0.143 m |

La CV **rechaza el deramp en los tres años**: mejora el ajuste *in-sample* (2017 y 2018) pero no
generaliza fuera de muestra. En consecuencia, la Opción A coincide con la B y el análisis de
sensibilidad se apoya en la Opción C (deramp3 forzado): ΔV = −5,2 % (2017), −12,5 % (2018) y
−5,3 % (2023).

Diagnóstico glaciar vs zona estable: distancia mediana 128 m, 96,9 % del glaciar dentro del convex hull
del terreno estable. Ese diagnóstico respalda conceptualmente el deramp (el glaciar está en gran
parte dentro del dominio de control), pero la CV muestra que, pese a ello, la corrección
extrapolada no generaliza: en 2018 es ≈+0,13 m sobre el terreno estable y ≈−1,12 m sobre el
glaciar. Es una extrapolación, no una deformación observada.

Incertidumbre del volumen (ruido del co-registro): σ_V = 1.651 / 618 / 437 m³ (0,09 / 0,04 /
0,06 %); la incertidumbre total, dominada por términos sistemáticos, se estima en 10–15 %.

Todos estos resultados están en `coreg_variants_summary.csv` y `dod_summary.csv` (no versionados, regenerables).

---

## 7.5. Informe y dossier de revisión

- `report/preinforme.pdf` — **dossier de revisión** generado por `scripts/05-preinforme.py`
  (portada, propósito, tablas T3–T5, las 9 figuras con pies y lista de pendientes).
  **No** es el informe científico final.
- `report/report_final.md` — **informe final** en formato de artículo científico (redactado el
  2026-10-28 con los resultados regenerados; ver §7). Es el único archivo de `report/` que se
  versiona.
- `report/tables/T6_report_main.md` — tablas consolidadas T3–T5 en markdown.
- `report/figures/F1–F9` — figuras generadas por `scripts/04-report.py`.

Tanto `report/preinforme.pdf` como las figuras y tablas son **regenerables** y están ignorados
por git (`report/figures/`, `report/tables/`, `report/dod_geotiffs/`, `report/*.pdf`).

---

## 8. Estado de Git y despliegue a GitHub

- **Rama:** `main`
- **Último commit:** ver `git log --oneline -1` (esta memoria se actualiza en el mismo commit que
  los resultados regenerados del 2026-10-28).
- **Historial relevante:**
  - `c2a1822` — "docs: cerrar PROJECT_MEMORY y LLM_CONTEXT (paso 05, tests y estado git)"
  - `75aadaf` — "docs: sincronizar memoria, renumerar secciones, sección de informe y versiones"
  - `f17ceff` — "fix: validación defensiva CRS, equivalencia CV con numpy y variograma N_eff"
  - `797f88d` — "docs: añadir archivos de memoria para retomar el proyecto con LLM"
  - `f1e6069` — "chore: proyecto base NK-native listo para GitHub"
- **Working tree:** limpio tras la regeneración; solo quedan directorios de salida ignorados.
- **Tests:** `pytest tests/` → **28 tests pasando** (7 archivos).
- **Remoto:** aún no configurado (pendiente crear repo en GitHub)

Cuando exista el repositorio en GitHub (cuenta `eguivarjosed48-dot`, nombre `NK-native`, **vacío**, sin README/.gitignore/LICENSE):

```bash
cd /Users/eguivar/Documents/dev/NK-native
git remote add origin git@github.com:eguivarjosed48-dot/NK-native.git
git branch -M main
git push -u origin main
```

**Qué NO debe subirse jamás:** `.venv/`, `dems_*/`, `dod/`, `report/`, `test_outputs/`, `data/raw/`, `config.local.toml`, `*.csv` de resultados, `report/*.pdf`, `.DS_Store`.  
**Qué SÍ se sube:** código Python, `config.toml`, `requirements.txt`, `README.md`, `LICENSE`, `.gitignore`, `.gitattributes`, `tests/`, `docs/memoria/`, `data/*.gpkg`.

---

## 9. Decisiones de diseño

### CV espacial con `numpy.linalg.lstsq` (en lugar de `xdem.coreg.Deramp` por fold)

En `scripts/02-NK-Variantes.py`, la función `cv_espacial_nmad_numpy` implementa la validación
cruzada espacial bloqueada con `numpy.linalg.lstsq` sobre una matriz de diseño polinómica
construida a mano (`construir_matriz_polinomio`), en lugar de llamar a
`xdem.coreg.Deramp.apply` dentro de cada fold.

**Motivo (rendimiento/memoria):** aplicar `Deramp` sobre el DEM completo por cada fold
genera copias temporales grandes y provocó uso de swap en equipos con 8 GB de RAM.
Trabajar solo sobre los píxeles de la máscara estable elimina esa presión de memoria.

**Equivalencia matemática documentada:**
- `construir_matriz_polinomio` reproduce la misma base de términos
  [1, y, x, y², xy, x², ...] que usa `xdem` internamente para el deramp polinómico.
- La normalización de coordenadas (`x_n`, `y_n`) es solo para estabilidad numérica
  (coordenadas UTM grandes); no altera el subespacio ajustado ni el resultado.
- `np.linalg.lstsq` resuelve los mismos mínimos cuadrados ordinarios que `xdem`
  resuelve internamente.
- Los tests en `tests/test_cv_equivalence.py` verifican ejecutablemente que los
  coeficientes (con cambio de signo por dirección de la diferencia) y las
  predicciones son equivalentes a los de `xdem.coreg.Deramp(poly_order=3)`.

### Propagación de error por variograma (en lugar de fracción arbitraria)

En `scripts/03-DoD.py`, `sigma_volume_m3` se calculaba con
`n_eff = 0.05 * n_pixels` (5% arbitrario), lo que subestimaba el error por un
factor de ~1000. Ahora se usa `nkdem.stats.estimar_n_eff`, que:

- Calcula el variograma experimental del residual DoD con desplazamientos (`np.roll`).
- Ajusta un modelo esférico o exponencial con `scipy.optimize.curve_fit` para
  estimar el rango de correlación (en píxeles).
- Devuelve `n_eff = n_validos / rango_px^2` (equivalente a
  `area_valida / (rango * pixel_size)^2`).

Si el variograma no converge, se mantiene el fallback a `N_EFF_FRACTION` (0.05),
marcado explícitamente como `usando_fallback=True` en el CSV de salida.
El CSV ahora incluye `rango_correlacion_px`, `rango_correlacion_m`,
`n_eff_calculado`, `modelo_variograma`, `usando_fallback`, `sigma_volume_m3`
y `sigma_volume_pct`.

### Dossier PDF de pre-informe (en lugar de redactar directamente el informe final)

`scripts/05-preinforme.py` genera `report/preinforme.pdf` con `reportlab`: reúne en un solo
documento la portada, el propósito, las tablas T3–T5 (leídas de `report/tables/*.csv`), las 9
figuras F1–F9 con sus pies y la lista explícita de pendientes para el informe final.

**Motivo:** permitir una revisión visual y numérica rápida de todos los insumos antes de
comprometer la redacción del informe científico, sin duplicar cifras a mano en un markdown.

**Alcance:** el PDF es un *dossier de revisión*, no un resultado del pipeline. Por eso:
- no usa `load_config()` (trabaja con rutas relativas a `report/`, por lo que debe lanzarse
  desde la raíz del repo);
- no se versiona (§8);
- cualquier cifra que aparezca en él proviene de los CSV generados por los pasos 02–03, de modo
  que al regenerar el pipeline el dossier se reconstruye sin editar cifras a mano.

### Deramp implementado por bloques (`nkdem.deramp`) en lugar de `Deramp.apply` global

`scripts/02-NK-Variantes.py` ajusta el polinomio con `nkdem.deramp.ajustar_deramp` (MCO sobre
los píxeles de terreno estable) y lo aplica con `nkdem.deramp.aplicar_deramp` en bloques de 256
filas.

**Motivo:** `xdem.coreg.Deramp.apply` materializa varias copias del DEM completo (94 millones de
píxeles); con 8 GB de RAM el proceso entraba en *swap* y no terminaba. La evaluación por bloques
produce el mismo resultado con memoria acotada.

**Equivalencia:** la base de 16 términos y los MCO son los mismos que usa `xdem`; verificado en
`tests/test_deramp.py` (ajuste sintético y comparación con `xdem.coreg.Deramp`).

### Corrección de dos errores que impedían reproducir los resultados

El 2026-10-28 se detectó que la versión commiteada del Paso 2 **no se podía ejecutar** y que los
resultados previos provenían de una versión anterior del script:

1. `dem_nk, dem_mask, _, dem_crs = load_dem_with_mask(...)` desempacaba mal: la segunda salida es
   la `transform`, no la máscara (`ufunc 'bitwise_and' not supported`).
2. `deramp3.fit(dem_nk_xdem, dem_nk_xdem, ...)` ajustaba el polinomio contra el propio DEM. Como
   `Deramp` modela `referencia − DEM`, el ajuste resultante es nulo (comprobado: corrección
   ≈3 × 10⁻⁵ m). La línea correcta es `fit(referencia, dem)`.

Ambos errores están cubiertos por `tests/test_deramp_semantics.py`. Con el código corregido, la
CV **no acepta** el deramp en ningún año, por lo que el resultado previo («CV acepta 2018») era
un artefacto de la versión anterior.

### Incertidumbre del volumen a partir del ruido en terreno estable

`scripts/03-DoD.py` propaga σ_V = σ_ruido · A / √N_eff, con σ_ruido = NMAD del residual de
co-registro en terreno estable y N_eff = A / L², donde L es la longitud de correlación estimada
con el variograma del mismo residual (`nkdem.stats.estimar_n_eff`).

**Motivo:** aplicar el variograma al DoD del glaciar confunde señal con ruido: como el rango de
correlación resulta mayor que el dominio, N_eff → 1 y σ_V llegaba a ≈40 % del volumen (dominado
por la variabilidad real del adelgazamiento). Con el ruido del terreno estable, σ_V = 0,04–0,09 %
(1.651, 618 y 437 m³). Los términos sistemáticos (variante, densidad, máscara) se discuten
cualitativamente en el informe y llevan la incertidumbre total al 10–15 %.

---

## 10. Reglas para futuras modificaciones (LLM / colaborador)

1. **Nunca hardcodear rutas absolutas.** Usar `nkdem.config.load_config()` y las propiedades `cfg.*`.
   Única excepción documentada: `scripts/05-preinforme.py`, que trabaja con rutas relativas a
   `report/` (ver §5 y §9).
2. **No versionar rásteres ni outputs.** Todo lo que sea `.tif` o CSV de resultados se ignora con `.gitignore`.
3. **Mantener outputs regenerables.** Cualquier cambio de metodología debe poder reproducirse ejecutando `00` → `04` desde cero.
4. **Antes de cambios, ejecutar:** `pytest tests/` y verificar que pase.
5. **Si se agrega un script nuevo:** ponerlo en `scripts/` y documentarlo en este archivo y en `README.md` (incluida su entrada en la tabla del §5 y sus dependencias en `requirements.txt`).
6. **Si se cambia un parámetro metodológico:** actualizar `config.toml` sección `[params]` y este archivo.
7. **Las pruebas unitarias viven en `tests/`** (5 archivos, 21 tests). Cubren `nkdem.config`,
   `nkdem.stats` (`nmad`, polinomios, `estimar_n_eff`), la equivalencia de la CV con
   `xdem.coreg.Deramp` y la validación de CRS de polígonos; los tests geoespaciales usan
   `geopandas`/`rasterio`, que ya están en `requirements.txt`.

---

## 11. Archivos de memoria relacionados (en este mismo repo)

- `docs/memoria/00-AUDITORIA.md` — diagnóstico del estado inicial del proyecto (hallazgos, métricas, cambios aplicados).
- `docs/memoria/01-PLAN-GITHUB.md` — checklist para crear el repo en GitHub y hacer el push.

---

## 12. Cómo retomar con un LLM en una sesión futura

Al iniciar una nueva conversación sobre este proyecto, proporcionar este archivo (`PROJECT_MEMORY.md`) y, opcionalmente, `00-AUDITORIA.md`. Con eso el LLM tendrá:
- Estructura completa del repo.
- Cómo configurar rutas en una máquina nueva.
- Orden de ejecución del pipeline.
- Parámetros metodológicos y resultados de referencia.
- Reglas de estilo y convención de código.
- Estado de git y cómo publicar en GitHub.

Si el LLM necesita modificar o ejecutar código, pedirle que use la venv de Python 3.12 en `.venv/` y que respete `config.local.toml` para las rutas de datos fuente.
