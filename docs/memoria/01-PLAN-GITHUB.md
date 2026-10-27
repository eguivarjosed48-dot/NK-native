# Plan para publicar en GitHub

## Paso 1 — Crear el repositorio en GitHub

1. Inicia sesión en https://github.com (usuario: `eguivar`).
2. Crea un repositorio **público** llamado `NK-native`.
3. **No** inicialices con README, .gitignore ni LICENSE (los traemos locales).
4. Copia la URL del repositorio remoto (HTTPS o SSH).

## Paso 2 — Conectar y subir (en la máquina local)

Desde la raíz del proyecto (`NK-native/`):

```bash
# (una sola vez) Conectar el remoto
git remote add origin https://github.com/eguivar/NK-native.git

# Renombrar rama por defecto a main
git branch -M main

# Subir por primera vez
git push -u origin main
```

## Paso 3 — Verificar en GitHub

- Revisa que aparezcan: `README.md`, `nkdem/`, `scripts/`, `tests/`,
  `docs/memoria/`, `data/*.gpkg`, `config.toml`, `.gitignore`.
- Confirma que **no** aparezcan `.venv/`, `dems_*/`, `dod/`, CSVs de resultados
  ni `config.local.toml`.

## Notas

- El repositorio versionable pesa < 5 MB (los rásteres derivados se ignoran).
- Cualquier colaborador podrá clonar y regenerar todo el pipeline definiendo
  sus rutas de DEMs en `config.local.toml` o vía variables de entorno `NK_*`.
