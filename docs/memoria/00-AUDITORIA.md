# Auditoría del proyecto NK-native

**Fecha:** 2026-10-27  
**Autor:** Jose Mauricio Eguivar Duran  
**Estado inicial:** proyecto funcional pero atado a una máquina y sin control de versiones.

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
| `scripts/02-deramp-autotune.py` | Funcional | Rutas absolutas; duplica lógica. |
| `scripts/02-NK-Variantes.py` | Funcional | CV espacial vectorizada con numpy (buena práctica). |
| `scripts/03-DoD.py` | Funcional | DoD Opción A/B; rutas absolutas en `DEM_BY_VARIANT`. |
| `scripts/04-report.py` | Funcional | Figuras F1–F9 y tablas T3–T6. |
| `scripts/test.py` | Utilidad | Crea `data/glaciar_2017.gpkg` desde shapefile local. |
| `scripts/test_glaciar_vs_estable.py` | Diagnóstico | Hull convex, distancias glaciar–estable. |
| `data/*.gpkg` | Versionables | `stable_terrain.gpkg` y `glaciar_2017.gpkg` (~200 KB). |
| Rásteres derivados | No versionar | `dems_*`, `dod/`, `report/dod_geotiffs/` (~2.8 GB). |
| Resultados CSV | Generados | `coreg_variants_summary.csv`, `dod_summary.csv`. |

## 3. Métricas clave de los resultados ya generados

DoD (glaciar 2017 vs referencia 2025), volumen de cambio:

| Año | Opción B (todo NK) | Opción A (mixta) | ΔVolumen |
|-----|--------------------|------------------|----------|
| 2017 | +1.751 × 10⁶ m³ | +1.751 × 10⁶ m³ | 0 |
| 2018 | +1.572 × 10⁶ m³ | +1.375 × 10⁶ m³ | −0.197 × 10⁶ m³ (−12.5 %) |
| 2023 | +0.738 × 10⁶ m³ | +0.738 × 10⁶ m³ | 0 |

Co-registro (NMAD en zona estable):
- 2017: NK = 0.471 m (CV rechazó deramp)
- 2018: NK = 0.372 m → deramp3 = 0.321 m (CV aceptó)
- 2023: NK = 0.143 m (CV rechazó deramp)

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
- [ ] Crear el repositorio vacío en GitHub (usuario: eguivar).
- [ ] Conectar remoto y hacer push:
      ```bash
      git remote add origin https://github.com/eguivar/NK-native.git
      git branch -M main
      git push -u origin main
      ```
- [ ] Añadir badges de CI (GitHub Actions) para correr `pytest tests/`
  en cada push (opcional, requiere datos fuente en el runner).
- [ ] Documentar en `docs/` el significado de cada variante y la decisión de CV.
