"""Configuración central del proyecto.

Prioridad de resolución (de menor a mayor):
  1. Valores por defecto embebidos en este módulo.
  2. ``config.toml`` en la raíz del repositorio.
  3. ``config.local.toml`` (rutas de la máquina; ignorado por git).
  4. Variables de entorno ``NK_*``.

Todas las rutas relativas se resuelven desde la raíz del repositorio.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]

_DEFAULTS: dict[str, Any] = {
    "project": {
        "reference_year": "2025",
        "years": ["2017", "2018", "2023"],
    },
    "params": {
        "nk_subsample": 0.2,
        "poly_order": 3,
        "cv_n_blocks": 4,
        "cv_min_pixels_per_block": 2000,
        "cv_max_train_pixels": 200000,
        "random_seed": 42,
        "n_eff_fraction": 0.05,
        "map_downsample": 4,
        "vmin_pct": 2,
        "vmax_pct": 98,
        "n_hyps_bins": 20,
    },
    "input": {
        "dem_dir": "data/raw/dems",
        "dem_pattern": "{year}/{year}_DSM.tif",
        "reference_dem": "data/raw/dems/2025_B/2025_B_DSM.tif",
        "stable_terrain": "data/stable_terrain.gpkg",
        "glacier_polygon": "data/glaciar_2017.gpkg",
    },
    "output": {
        "aligned_dir": "dems_alineados",
        "nk_dir": "dems_nk",
        "variants_dir": "dems_variants",
        "dod_dir": "dod",
        "dod_figures_dir": "dod_figures",
        "report_dir": "report",
        "test_outputs_dir": "test_outputs",
        "coreg_csv": "coreg_variants_summary.csv",
        "dod_csv": "dod_summary.csv",
        "nk_csv": "nk_coreg_summary.csv",
    },
}

# Variables de entorno aceptadas -> clave anidada en la configuración.
_ENV_OVERRIDES = {
    "NK_DEM_DIR": "input.dem_dir",
    "NK_DEM_PATTERN": "input.dem_pattern",
    "NK_REFERENCE_DEM": "input.reference_dem",
    "NK_STABLE_TERRAIN": "input.stable_terrain",
    "NK_GLACIER_POLYGON": "input.glacier_polygon",
}


@dataclass(frozen=True)
class Config:
    """Rutas y parámetros resueltos del proyecto."""

    root: Path
    reference_year: str
    years: tuple[str, ...]
    dem_dir: Path
    dem_pattern: str
    reference_dem: Path
    stable_terrain: Path
    glacier_polygon: Path
    aligned_dir: Path
    nk_dir: Path
    variants_dir: Path
    dod_dir: Path
    dod_figures_dir: Path
    report_dir: Path
    test_outputs_dir: Path
    coreg_csv: Path
    dod_csv: Path
    nk_csv: Path

    @property
    def tables_dir(self) -> Path:
        return self.report_dir / "tables"

    @property
    def figures_dir(self) -> Path:
        return self.report_dir / "figures"

    def dem(self, year: str) -> Path:
        """Ruta al DSM crudo de ``year`` según ``dem_pattern``."""
        pattern = Path(self.dem_pattern.format(year=year))
        if pattern.is_absolute():
            return pattern
        return (self.dem_dir / pattern).resolve()

    def aligned_dem(self, year: str) -> Path:
        return (self.aligned_dir / f"dem_{year}_aligned.tif").resolve()

    def nk_dem(self, year: str) -> Path:
        return (self.nk_dir / f"dem_{year}_nk.tif").resolve()

    def variant_dem(self, year: str, variant: str) -> Path:
        return (self.variants_dir / f"{year}_{variant}.tif").resolve()

    def rel(self, path: str | Path) -> str:
        """Devuelve ``path`` relativo a la raíz (POSIX) si es posible.

        Se usa para guardar rutas portables en los CSV de resultados.
        """
        resolved = Path(path).resolve()
        try:
            return resolved.relative_to(self.root.resolve()).as_posix()
        except ValueError:
            return resolved.as_posix()


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value
    return base


def _set_nested(data: dict[str, Any], dotted: str, value: Any) -> None:
    keys = dotted.split(".")
    node = data
    for key in keys[:-1]:
        node = node.setdefault(key, {})
    node[keys[-1]] = value


def _read_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _resolve(root: Path, value: str | Path) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else (root / path).resolve()


def load_config(root: str | Path | None = None) -> Config:
    """Carga y resuelve la configuración del proyecto."""
    root_path = Path(root).resolve() if root is not None else PROJECT_ROOT

    data: dict[str, Any] = {
        section: dict(values) for section, values in _DEFAULTS.items()
    }

    config_file = root_path / "config.toml"
    if config_file.exists():
        _merge(data, _read_toml(config_file))

    local_file = root_path / "config.local.toml"
    if local_file.exists():
        _merge(data, _read_toml(local_file))

    for env_name, dotted in _ENV_OVERRIDES.items():
        if env_name in os.environ and os.environ[env_name]:
            _set_nested(data, dotted, os.environ[env_name])

    project = data["project"]
    inputs = data["input"]
    outputs = data["output"]

    years = tuple(str(year) for year in project["years"])
    reference_year = str(project["reference_year"])
    if reference_year not in years:
        years = (*years, reference_year)

    dem_dir = _resolve(root_path, inputs["dem_dir"])
    aligned_dir = _resolve(root_path, outputs["aligned_dir"])

    return Config(
        root=root_path,
        reference_year=reference_year,
        years=years,
        dem_dir=dem_dir,
        dem_pattern=str(inputs["dem_pattern"]),
        reference_dem=_resolve(root_path, inputs["reference_dem"]),
        stable_terrain=_resolve(root_path, inputs["stable_terrain"]),
        glacier_polygon=_resolve(root_path, inputs["glacier_polygon"]),
        aligned_dir=aligned_dir,
        nk_dir=_resolve(root_path, outputs["nk_dir"]),
        variants_dir=_resolve(root_path, outputs["variants_dir"]),
        dod_dir=_resolve(root_path, outputs["dod_dir"]),
        dod_figures_dir=_resolve(root_path, outputs["dod_figures_dir"]),
        report_dir=_resolve(root_path, outputs["report_dir"]),
        test_outputs_dir=_resolve(root_path, outputs["test_outputs_dir"]),
        coreg_csv=_resolve(root_path, outputs["coreg_csv"]),
        dod_csv=_resolve(root_path, outputs["dod_csv"]),
        nk_csv=_resolve(root_path, outputs["nk_csv"]),
    )


def require_files(paths: dict[str, str | Path]) -> None:
    """Comprueba que existan los archivos indicados y falla con un mensaje útil."""
    missing = {name: Path(path) for name, path in paths.items() if not Path(path).exists()}
    if not missing:
        return
    lines = [f"  - {name}: {path}" for name, path in missing.items()]
    raise FileNotFoundError(
        "Faltan archivos de entrada:\n"
        + "\n".join(lines)
        + "\n\nCopia los DSM crudos en 'data/raw/dems' o define NK_DEM_DIR / "
        "config.local.toml con la ruta correcta. Ver README.md §Datos."
    )
