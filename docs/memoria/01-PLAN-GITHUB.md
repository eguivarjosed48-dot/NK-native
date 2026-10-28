# Plan para publicar en GitHub

## Paso 1 — Crear el repositorio en GitHub  ✅ (hecho 2026-10-28)

1. Inicia sesión en https://github.com (cuenta: `eguivarjosed48-dot`, la que autentica la clave SSH de esta máquina).
2. Crea un repositorio **público** llamado `NK-native`.
3. **No** inicialices con README, .gitignore ni LICENSE (los traemos locales).
4. Copia la URL del repositorio remoto (HTTPS o SSH).

## Paso 2 — Conectar y subir (en la máquina local)  ✅ (hecho)

Desde la raíz del proyecto (`NK-native/`):

```bash
# (una sola vez) Conectar el remoto
git remote add origin git@github.com:eguivarjosed48-dot/NK-native.git

# Renombrar rama por defecto a main
git branch -M main

# Subir por primera vez
git push -u origin main
```

## Paso 2b — Metadatos del repositorio (pendiente: descripción y topics)

- Descripción: «Co-registro Nuth & Kääb + deramp con validación cruzada + DoD de
  DSM del Glaciar Llojeta (2017–2025), 0,1 m».
- Topics: `glaciology`, `dem`, `nuth-kaab`, `deramp`, `xdem`, `geospatial`,
  `drone-photogrammetry`, `bolivia`.
- Activar Issues y el badge de CI (`.github/workflows/tests.yml`).

## Paso 3 — Verificar en GitHub  ✅ (47 entradas, solo los 2 .gpkg como binarios; CI en verde)

- Revisa que aparezcan: `README.md`, `nkdem/`, `scripts/`, `tests/`,
  `docs/memoria/`, `data/*.gpkg`, `config.toml`, `.gitignore`.
- Confirma que **no** aparezcan `.venv/`, `dems_*/`, `dod/`, CSVs de resultados
  ni `config.local.toml`.

## Notas

- El repositorio versionable pesa < 1 MB (los rásteres derivados se ignoran).
- CI: cada push ejecuta `pytest` (28 pruebas) en GitHub Actions.
- Cualquier colaborador podrá clonar y regenerar todo el pipeline definiendo
  sus rutas de DEMs en `config.local.toml` o vía variables de entorno `NK_*`.
