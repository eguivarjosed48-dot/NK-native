# Auditoría del proyecto NK-native

**Fecha:** 2026-10-27 (última revisión: 2026-10-28)  
**Autor:** Jose Mauricio Eguivar Duran  
**Estado inicial:** proyecto funcional pero atado a una máquina y sin control de versiones.  
**Estado actual (2026-10-28):** pipeline 00→05 reproducible, 28 pruebas, resultados
regenerados e informe final redactado. Ver «Actualización 2026-10-28» al final.

## 1. Resumen ejecutivo

El proyecto implementa un pipeline de co-registro y DoD (DEM of Difference) de
DEMs glaciares con Python, `xdem`, `rasterio`, `geopandas` y `numpy`. Funciona
y ya tiene productos generados (DEMs alineados, co-registrados con NK, variantes
con deramp, DoD, figuras y tablas del informe), pero:

- Los scripts usan **rutas absolutas** de esta Mac
  (`/Users/eguivar/Documents/2-2026/...`), por lo que no son portables.
- Hay **lógica duplicada** (carga de DEM + máscara, NMAD, evaluación de
  diferencia) repetida en casi todos los scripts.
- No hay **entorno declarativo** ni `requirements.txt` actualizado.
- No hay **pruebas automatizadas**.
- No hay **control de versiones** (no existía repositorio git).
- Los rásteres pesan ~2.8 GB y no deben subirse a GitHub (límite 100 MB por
  archivo; LFS gratuito solo da 1 GB).

## 2. Hallazgos por componente

| Componente | Estado | Observación |
|------------|--------|-------------|
| `scripts/00-check-input.py` | Funcional | Rutas absolutas hardcodeadas. |
| `scripts/01-nuth-kaab.py` | Funcional | Rutas absolutas; duplica carga de DEM/máscara. |
| `scripts/02-deramp-autotune.py` | Legacy | Versión anterior del Paso 2 (sin CV); se conserva como referencia. |
| `scripts/02-NK-Variantes.py` | Funcional | Variantes NK/deramp3/derampCV; CV espacial vectorizada con numpy. |
| `scripts/03-DoD.py` | Funcional | DoD en tres opciones: B (todo NK), A (según CV) y C (deramp3 forzado). |
| `scripts/04-report.py` | Funcional | Figuras F1–F9 y tablas T3–T6. |
| `scripts/test.py` | Utilidad | Crea `data/glaciar_2017.gpkg` desde shapefile local. |
| `scripts/test_glaciar_vs_estable.py` | Diagnóstico | Hull convex, distancias glaciar–estable. |
| `data/*.gpkg` | Versionables | `stable_terrain.gpkg` y `glaciar_2017.gpkg` (~200 KB). |
| Rásteres derivados | No versionar | `dems_*`, `dod/`, `report/dod_geotiffs/` (~2.8 GB). |
| Resultados CSV | Generados | `coreg_variants_summary.csv`, `dod_summary.csv`. |

## 3. Métricas clave (regeneradas el 2026-10-28)

DoD (glaciar 2017 vs referencia 2025), volumen de cambio:

| Año | Opción B (todo NK) | Opción A (según CV) | Opción C (deramp3 forzado) | ΔV C−B |
|-----|--------------------|---------------------|----------------------------|--------|
| 2017 | +1.751 × 10⁶ m³ | +1.751 × 10⁶ m³ | +1.660 × 10⁶ m³ | −5.2 % |
| 2018 | +1.572 × 10⁶ m³ | +1.572 × 10⁶ m³ | +1.375 × 10⁶ m³ | −12.5 % |
| 2023 | +0.738 × 10⁶ m³ | +0.738 × 10⁶ m³ | +0.699 × 10⁶ m³ | −5.3 % |

Co-registro (NMAD en zona estable):
- 2017: NK = 0.471 m; deramp3 in-sample 0.411 m; CV 0.486 vs 0.449 → **rechazado**
- 2018: NK = 0.372 m; deramp3 in-sample 0.321 m; CV 0.359 vs 0.359 → **rechazado**
- 2023: NK = 0.143 m; deramp3 in-sample 0.211 m; CV 0.251 vs 0.143 → **rechazado**

> Nota: la auditoría del 2026-10-27 registraba «2018: CV aceptó el deramp». Ese
> resultado provenía de una versión del Paso 2 que no era reproducible (ver
> «Actualización 2026-10-28»).

Diagnóstico glaciar vs zona estable: distancia mediana 128 m, 96.9 % del glaciar
dentro del convex hull del terreno estable → deramp3 al glaciar defendible pero
con cierta extrapolación.

## 4. Cambios aplicados en esta sesión

1. **Paquete común `nkdem/`**:
   - `config.py` — resolución central de rutas y parámetros (`config.toml` +
     `config.local.toml` ignorado + variables de entorno `NK_*`).
   - `raster.py` — lectura/máscara por polígono/escritura de GeoTIFF.
   - `stats.py` — NMAD, diferencias, polinomios, bloques de CV espacial.
   - `io.py` — lectura/escritura de CSV.
2. **Refactor de scripts** `00` → `04` y `test_*` para usar `nkdem` y rutas
   relativas a la raíz del repositorio.
3. **Pruebas unitarias** en `tests/` (`test_config.py`, `test_stats.py`).
4. **Archivos de repositorio**: `.gitignore`, `.gitattributes`, `requirements.txt`,
   `README.md`, `LICENSE`, `config.toml`, `config.local.toml` (local, ignorado).
5. **Archivos de memoria**: `docs/memoria/00-AUDITORIA.md` (este archivo).

## 5. Decisiones de datos para GitHub

- **NO se suben:** `.venv/`, `dems_*/`, `dod/`, `dod_figures/`,
  `test_outputs/`, `report/figures/`, `report/dod_geotiffs/`, `report/tables/`,
  CSVs de resultados, `config.local.toml`, `data/raw/`.
- **SÍ se suben:** código Python, `config.toml`, `requirements.txt`,
  `README.md`, `LICENSE`, `.gitignore`, `.gitattributes`, `tests/`,
  `docs/memoria/`, `data/stable_terrain.gpkg`, `data/glaciar_2017.gpkg`.

Tamaño estimado del repositorio versionable: < 5 MB.

## 6. Próximos pasos (pendientes)

- [x] Crear repositorio local con git y primer commit.
- [x] Crear el repositorio vacío en GitHub (cuenta: `eguivarjosed48-dot`).
- [x] Conectar remoto y hacer push (`main` + tag `v0.1.0`):
      ```bash
      git remote add origin git@github.com:eguivarjosed48-dot/NK-native.git
      git branch -M main
      git push -u origin main
      ```
- [x] Badge de CI (GitHub Actions) que corre `pytest tests/` en cada push
  (las pruebas unitarias no necesitan los datos fuente).
- [x] Documentar en `docs/` el significado de cada variante y la decisión de CV.

## 7. Actualización 2026-10-28

Durante la redacción del informe final se detectó que la versión commiteada del
Paso 2 **no se podía ejecutar** y que sus salidas provenían de una versión
anterior del script:

1. Desempaquetado erróneo de `load_dem_with_mask` (`dem_mask` recibía la
   `transform`, no la máscara → `ufunc 'bitwise_and' not supported`).
2. `deramp3.fit(dem_nk_xdem, dem_nk_xdem)`: al ajustar el polinomio contra el
   propio DEM, la corrección resultante era nula (≈3 × 10⁻⁵ m).

Correcciones aplicadas:

- `scripts/02-NK-Variantes.py` desempaqueta bien la máscara y ajusta el deramp
  contra la referencia (`fit(ref, dem)`).
- Nuevo `nkdem/deramp.py`: deramp polinómico por bloques de filas, que evita las
  copias del DEM completo y el *swap* con 94 millones de píxeles.
- `scripts/03-DoD.py` propaga σ_V desde el ruido del co-registro en terreno
  estable y su longitud de correlación (no desde el DoD del glaciar, donde el
  rango supera el dominio y σ_V llegaba al ≈40 %).
- Pruebas nuevas: `tests/test_deramp.py` y `tests/test_deramp_semantics.py`
  (28 pruebas en total); CI en `.github/workflows/tests.yml`.
- Resultados e informe regenerados; `report/report_final.md` es el documento de
  referencia.
