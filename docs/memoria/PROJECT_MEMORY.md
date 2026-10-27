# 🧠 MEMORIA DEL PROYECTO — NK-native

> Archivo de contexto para retomar este proyecto con un LLM en una sesión futura.  
> Úsalo como "system prompt" o léelo al inicio de cada nueva conversación sobre este repo.

---

## 1. Visión general

**Nombre:** NK-native  
**Autor:** Jose Mauricio Eguivar Duran (eguivar.jose.d48@gmail.com)  
**Fecha:** 2026-10-27  
**Ubicación:** `/Users/eguivar/Documents/dev/NK-native`  
**Estado:** Pipeline completo funcional, resultados generados, listo para subir a GitHub.

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
│   └── stats.py             # nmad(), diferencia_stats(), polinomios, bloques CV
├── scripts/                 # Pipeline por pasos (ejecutar en orden)
│   ├── 00-check-input.py    # Paso 0: alinea DEMs a cuadrícula 2025 -> dems_alineados/
│   ├── 01-nuth-kaab.py      # Paso 1: co-registro NK -> dems_nk/ + coreg_nk_summary.csv
│   ├── 02-deramp-autotune.py# Paso 2 (alt): deramp auto-tune -> dems_deramped/
│   ├── 02-NK-Variantes.py   # Paso 2 (principal): NK | deramp3 | deramp-CV -> dems_variants/ + coreg_variants_summary.csv
│   ├── 03-DoD.py            # Paso 3: DEM of Difference -> dod/ + dod_summary.csv + dod_figures/
│   ├── 04-report.py         # Paso 4: figuras F1-F9 + tablas T3-T6 -> report/
│   ├── test.py              # Crea data/glaciar_2017.gpkg desde shapefile fuente local
│   └── test_glaciar_vs_estable.py # Diagnóstico glaciar vs zona estable -> test_outputs/
├── tests/                   # Pruebas unitarias (pytest)
│   ├── test_config.py
│   └── test_stats.py
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
    └── report/  (figures/, tables/, dod_geotiffs/)
```

**Regla de oro:** los rásteres (.tif) y los CSVs de resultados no se versionan. Tamaño estimado del repo versionable: < 5 MB.

---

## 3. Stack tecnológico

- **Python:** 3.12.1 (entorno `.venv/` creado con `python -m venv .venv`)
- **Gestor de paquetes:** pip + `requirements.txt` (generado con `pip freeze`)
- **Librerías clave y versiones:**
  - `numpy==2.5.4`, `rasterio==1.5.2`, `geopandas==1.2.0`, `xdem==0.2.3`
  - `geoutils==0.2.5`, `rioxarray==0.23.0`, `scipy==1.18.1`, `matplotlib==3.11.2`
  - `pandas==2.3.3`, `shapely==2.2.0`, `pyproj==3.8.0`
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
| 3 | `scripts/03-DoD.py` | `dems_variants/`, `data/glaciar_2017.gpkg` | `dod/<year>_vs_2025_{A,B}.tif` + `dod_summary.csv` |
| 4 | `scripts/04-report.py` | salidas anteriores | `report/figures/F1-F9.png`, `report/tables/T3-T6.md/csv` |

Scripts opcionales/diagnóstico: `scripts/02-deramp-autotune.py`, `scripts/test.py`, `scripts/test_glaciar_vs_estable.py`.

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

| Año | Opción B (todo NK) | Opción A (mixta) | ΔVolumen |
|-----|--------------------|------------------|----------|
| 2017 | +1.751 × 10⁶ m³ | +1.751 × 10⁶ m³ | 0 |
| 2018 | +1.572 × 10⁶ m³ | +1.375 × 10⁶ m³ | −0.197 × 10⁶ m³ (−12,5 %) |
| 2023 | +0.738 × 10⁶ m³ | +0.738 × 10⁶ m³ | 0 |

NMAD en zona estable (co-registro):

| Año | NK | deramp3 | CV acepta deramp | NMAD final |
|-----|-----|---------|------------------|------------|
| 2017 | 0.471 m | 0.412 m | No | 0.471 m |
| 2018 | 0.372 m | 0.321 m | Sí | 0.321 m |
| 2023 | 0.143 m | 0.212 m | No | 0.143 m |

Diagnóstico glaciar vs zona estable: distancia mediana 128 m, 96,9 % del glaciar dentro del convex hull del terreno estable → deramp3 al glaciar defendible pero con cierta extrapolación.

Todos estos resultados están en `coreg_variants_summary.csv` y `dod_summary.csv` (no versionados, regenerables).

---

## 7.5. Informe

- `report/report_final.md` — informe final del análisis (pendiente de redacción).
- `report/tables/T6_report_main.md` — tablas consolidadas T3–T5 en markdown.
- `report/figures/F1–F9` — figuras generadas por `scripts/04-report.py`.

---

## 8. Estado de Git y despliegue a GitHub

- **Rama:** `main`
- **Último commit:** `797f88d` — "docs: añadir archivos de memoria para retomar el proyecto con LLM"
- **Working tree:** cambios pendientes (ver `git status`).
- **Remoto:** aún no configurado (pendiente crear repo en GitHub)

Cuando exista el repositorio en GitHub (usuario `eguivar`, nombre `NK-native`, **vacío**, sin README/.gitignore/LICENSE):

```bash
cd /Users/eguivar/Documents/dev/NK-native
git remote add origin https://github.com/eguivar/NK-native.git
git branch -M main
git push -u origin main
```

**Qué NO debe subirse jamás:** `.venv/`, `dems_*/`, `dod/`, `report/`, `test_outputs/`, `data/raw/`, `config.local.toml`, `*.csv` de resultados, `.DS_Store`.  
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

---

## 10. Reglas para futuras modificaciones (LLM / colaborador)

1. **Nunca hardcodear rutas absolutas.** Usar `nkdem.config.load_config()` y las propiedades `cfg.*`.
2. **No versionar rásteres ni outputs.** Todo lo que sea `.tif` o CSV de resultados se ignora con `.gitignore`.
3. **Mantener outputs regenerables.** Cualquier cambio de metodología debe poder reproducirse ejecutando `00` → `04` desde cero.
4. **Antes de cambios, ejecutar:** `pytest tests/` y verificar que pase.
5. **Si se agrega un script nuevo:** ponerlo en `scripts/` y documentarlo en este archivo y en `README.md`.
6. **Si se cambia un parámetro metodológico:** actualizar `config.toml` sección `[params]` y este archivo.
7. **Las pruebas unitarias viven en `tests/`** y prueban `nkdem.config` y `nkdem.stats` (sin dependencias geoespaciales pesadas).

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
