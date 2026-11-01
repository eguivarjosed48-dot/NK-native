# LLM_CONTEXT — NK-native

Archivo de contexto rápido para retomar el proyecto con un LLM.  
Contenido completo en: `docs/memoria/PROJECT_MEMORY.md`.

---

## 1. Qué es este proyecto

**NK-native** es un pipeline en Python 3.12 para cuantificar el cambio de elevación y volumen de un glaciar de montaña (Glaciar Llojeta, 0.184 km², Coordillera Real, EPSG:32719, resolución 0.1 m) a partir de cuatro DEMs de dron (2017, 2018, 2023, 2025).

El DEM de 2025 es la referencia. Se aplica co-registro Nuth & Kääb (NK) sobre una máscara de terreno estable periglaciar (0.041 km²), con una corrección polinómica opcional (deramp3) que se acepta o rechaza mediante validación cruzada espacial. El resultado es el DEM of Difference (DoD) sobre el polígono del glaciar 2017, con propagación de error al volumen.

**Autor:** Jose Mauricio Eguivar Duran  
**Ubicación:** `/Users/eguivar/Documents/dev/NK-native`  
**Repositorio:** https://github.com/eguivarjosed48-dot/NK-native (público, rama `main`, tag `v0.1.0`, CI en verde)

---

## 2. Estado actual (2026-11-01)

- **Pipeline:** `00` → `06` completo y verificado de extremo a extremo.
- **Informe final:** redactado (`report/report_final.md`, formato de artículo científico).
- **Marco de confianza:** redactado (`report/MARCO_CONFIANZA.md`, autocontenido).
- **Tests:** 28 pasando en 7 archivos (`pytest tests/`).
- **Hecho:** Paso 6, marco de confianza e informe final están commiteados y pusheados (`6120657`, `2d75ae0`). Árbol de trabajo limpio.
- **Pendiente:** redactar el Apéndice A del informe con sus metadatos (afiliación, topónimo del glaciar, fechas/sensor de los vuelos, licencia); aún no existe esa sección en `report/report_final.md`.

---

## 3. Estructura del repositorio

```text
NK-native/
├── config.toml                 # Parámetros por defecto (VERSIONADO)
├── config.local.toml           # Rutas absolutas de esta máquina (IGNORADO por git)
├── requirements.txt            # Dependencias (pip freeze)
├── conftest.py                 # pytest: añade la raíz a sys.path
├── nkdem/                      # Paquete compartido
│   ├── config.py               # load_config()
│   ├── raster.py               # validar_poligono(), lectura/escritura
│   ├── stats.py                # nmad(), estimar_n_eff()
│   ├── deramp.py               # deramp polinómico por bloques
│   └── io.py                   # leer_csv / write_csv
├── scripts/                    # Pipeline
│   ├── 00-check-input.py       # Homogeneización de cuadrícula y CRS
│   ├── 01-nuth-kaab.py         # Co-registro NK
│   ├── 02-NK-Variantes.py      # Variantes NK / deramp3 / deramp-CV con CV espacial
│   ├── 03-DoD.py               # DEM of Difference
│   ├── 04-report.py            # Figuras F1–F9 + tablas T3–T6 + sección de confianza
│   ├── 05-preinforme.py        # Dossier PDF de revisión (auxiliar)
│   ├── 06-confianza.py         # Figuras F10–F14 + tablas T8–T13 (confianza)
│   ├── 02-deramp-autotune.py   # Legacy (deramp sin CV)
│   ├── test.py                 # Utilidad de diagnóstico
│   └── test_glaciar_vs_estable.py # Utilidad de diagnóstico
├── tests/                      # 28 tests en 7 archivos
├── data/                       # Polígonos de apoyo (VERSIONADOS, <1 MB)
│   ├── glaciar_2017.gpkg
│   └── stable_terrain.gpkg
├── docs/memoria/               # PROJECT_MEMORY.md, 00-AUDITORIA.md, 01-PLAN-GITHUB.md
├── report/                     # Solo report_final.md y MARCO_CONFIANZA.md se versionan
└── (directorios generados, NO versionados)
    ├── dems_alineados/
    ├── dems_nk/
    ├── dems_variants/
    ├── dod/
    ├── test_outputs/
    └── report/                 # figures/, tables/, dod_geotiffs/, preinforme.pdf
```

**Regla de oro:** los `.tif`, los CSVs de resultados, las figuras y el `preinforme.pdf` **no se versionan**. Solo el código, `config.toml`, `requirements.txt`, `tests/`, `docs/`, `data/*.gpkg`, `report/report_final.md` y `report/MARCO_CONFIANZA.md`.

---

## 4. Cómo ejecutar

```bash
cd /Users/eguivar/Documents/dev/NK-native
source .venv/bin/activate

python scripts/00-check-input.py
python scripts/01-nuth-kaab.py
python scripts/02-NK-Variantes.py
python scripts/03-DoD.py
python scripts/04-report.py
python scripts/05-preinforme.py    # opcional: dossier PDF
python scripts/06-confianza.py     # marco de confianza (F10–F14, T8–T13)

pytest tests/
```

**Nota sobre el Paso 6:** el variograma con `max_lag_pixels=2000` sobre 94M de píxeles tarda ~30 min/año y entra en swap en equipos de 8 GB. La versión actual lo corrige: enmascara fuera de la zona estable (`diff[~ref_mask] = np.nan`) y submuestrea a ~1M de píxeles. Tarda ~2–3 min en total.

**Nota sobre el Paso 2:** la CV espacial rechaza el deramp en los tres años (mejora *in-sample* pero no fuera de muestra). Por eso la Opción A (mixta) coincide con la Opción B (todo NK).

---

## 5. Resultados de referencia (2026-11-01)

### Co-registro (NMAD en zona estable)

| Año | NK | deramp3 (in-sample) | CV deramp3 | CV NK | CV acepta | NMAD final |
|---:|---:|---:|---:|---:|:---:|---:|
| 2017 | 0.471 m | 0.411 m | 0.486 m | 0.449 m | No | 0.471 m |
| 2018 | 0.372 m | 0.321 m | 0.359 m | 0.359 m | No | 0.372 m |
| 2023 | 0.143 m | 0.211 m | 0.251 m | 0.143 m | No | 0.143 m |

La CV rechaza el deramp en los tres años. Opción A = Opción B. Sensibilidad con deramp3 forzado (Opción C): −5.2 % / −12.5 % / −5.3 %.

### DoD y volúmenes (Opción B, todo NK)

| Año | dH medio (m) | dH mediana (m) | NMAD (m) | Volumen (10⁶ m³) |
|---:|---:|---:|---:|---:|
| 2017 | +9.756 | +9.472 | 3.237 | +1.751 |
| 2018 | +8.933 | +8.799 | 3.214 | +1.572 |
| 2023 | +4.007 | +4.417 | 1.725 | +0.738 |

- **Tasas:** 1.22 / 1.28 / 2.00 m a⁻¹ (Δt = 8 / 7 / 2 a).
- **Balance específico:** 1.04 / 1.09 / 1.70 m w.e. a⁻¹ (ρ = 850 kg m⁻³).

**Convención de signo:** `dH = DEM_año − DEM_2025`; volumen positivo = pérdida de masa.

### Confianza en la señal (Paso 6, tres escenarios de N_eff)

| Año | V (10⁶ m³) | σ_V ultra (%) | z ultra | σ_V real (%) | z real |
|---:|---:|---:|---:|---:|---:|
| 2017 | +1.751 | 4.60 % | 21.7 | 0.32 % | 310.6 |
| 2018 | +1.572 | 4.25 % | 23.5 | 0.30 % | 336.1 |
| 2023 | +0.738 | 7.49 % | 13.3 | 0.52 % | 190.6 |

- **Ultraconservador (`N_eff=1`):** σ_V = 4.2–7.5 % del volumen, z = 13.3–23.5.
- **Conservador (N_eff del variograma):** igual al ultra (rango 1115–2012 m > glaciar).
- **Realista (`N_eff=200`, correlación a 30 m):** σ_V = 0.3–0.5 %, z > 190.

En todos los escenarios, la señal es significativa con z > 13.

### Control de extrapolación (Tabla 12)

| Año | Fracción en hull | Guarda (m) | Máx. extrap. (m) | OK |
|---:|---:|---:|---:|:---:|
| 2017 | 0.995 | 3.00 | 0.00 | ✅ |
| 2018 | 0.975 | 3.00 | 0.00 | ✅ |
| 2023 | 0.969 | 3.00 | 0.00 | ✅ |

### Consistencia temporal (Tabla 13)

| Intervalo | Δt (años) | Tasa (10⁶ m³/año) |
|:---|---:|---:|
| 2017–2018 | 1 | +0.179 |
| 2018–2023 | 5 | +0.167 |
| 2017–2023 | 6 | +0.169 |
| **Ratio** | — | **1.08** |

No hay evento anómalo en 2018.

---

## 6. Reglas de oro

1. **Nunca hardcodear rutas absolutas.** Usar siempre:

   ```python
   from nkdem.config import load_config

   cfg = load_config()
   cfg.reference_dem
   cfg.dem("2017")
   cfg.nk_dem("2018")
   cfg.dod_dir
   # ...
   ```

   Excepción documentada: `scripts/05-preinforme.py` usa rutas relativas a `report/` y debe lanzarse desde la raíz del repositorio.

2. **El deramp se ajusta siempre contra la referencia:** `fit(ref, dem)`. Nunca `fit(dem, dem)` (produce corrección nula; ver `tests/test_deramp_semantics.py`).

3. **El variograma del Paso 6 se calcula sobre el residual en zona estable enmascarado**, no sobre el DoD del glaciar (que mezcla error con señal).

4. **No versionar outputs.** Los `.tif`, CSVs de resultados, figuras y `preinforme.pdf` van en `.gitignore`.

5. **Antes de cualquier cambio, ejecutar `pytest tests/`** y verificar que los 28 tests pasan.

---

## 7. Informe y marco de confianza

- `report/report_final.md` — informe final en formato de artículo (resumen, introducción, métodos, resultados, discusión, conclusiones, referencias). Versionado.
- `report/MARCO_CONFIANZA.md` — marco de confianza autocontenido. Explica cada métrica del Paso 6 (NMAD por pendiente, R²_aspecto, R²_Z, variograma, N_eff, σ_V, z, guarda de extrapolación, consistencia temporal) con valores reales, referencias a los CSVs y limitaciones. Versionado.
- `report/preinforme.pdf` — dossier de revisión generado por `05-preinforme.py`. No es el informe final. No versionado.
- `report/tables/T6_report_main.md` — tablas T3–T5 + T8–T13 + conclusión de confianza, en Markdown. Regenerable.

---

## 8. Decisiones de diseño (resumen)

- **CV espacial con `numpy.linalg.lstsq` en lugar de `xdem.coreg.Deramp` por fold:** evita el uso de swap con 8 GB de RAM. Equivalencia verificada en `tests/test_cv_equivalence.py`.
- **Deramp por bloques (`nkdem/deramp.py`) en lugar de `Deramp.apply` global:** misma razón (memoria acotada). Equivalencia verificada en `tests/test_deramp.py`.
- **Variograma en zona estable enmascarada en el Paso 6:** evita mezclar error con señal del glaciar.
- **Tres escenarios de N_eff (ultra, conservador, realista):** el rango del variograma es una cota inferior (mayor que el glaciar), así que no se puede medir un N_eff central. Se reportan los tres y se muestra que la conclusión es robusta a la elección.
- **Propagación de error con NMAD del co-registro y área del polígono**, no con NMAD del DoD y área del DoD.

---

## 9. Historial de commits recientes (2026-11-01)

El Paso 6, el marco de confianza y el informe final ya están commiteados y
pusheados. No hay cambios pendientes de commit; el árbol de trabajo está limpio.

- `6120657` — feat: Paso 6 (confianza en la señal) + actualización de report y preinforme
  - `scripts/06-confianza.py` (nuevo), `scripts/04-report.py`, `scripts/05-preinforme.py`
- `2d75ae0` — docs: informe final, marco de confianza y actualización de memoria
  - `report/report_final.md`, `report/MARCO_CONFIANZA.md`, `docs/memoria/PROJECT_MEMORY.md`, `LLM_CONTEXT.md`

Para verificar el estado en cualquier momento:

```bash
git status            # árbol de trabajo
git log --oneline -5  # últimos commits
```
