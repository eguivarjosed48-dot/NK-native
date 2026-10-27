from pathlib import Path

from nkdem.config import PROJECT_ROOT, load_config, require_files


def test_defaults_resolve_from_project_root():
    cfg = load_config()
    assert cfg.root == PROJECT_ROOT
    assert cfg.reference_year == "2025"
    assert {"2017", "2018", "2023"}.issubset(cfg.years)
    assert cfg.dem("2017").name == "2017_DSM.tif"
    assert cfg.dem("2017").is_absolute()
    assert cfg.aligned_dem("2017").parent == cfg.aligned_dir
    assert cfg.variant_dem("2018", "NK").name == "2018_NK.tif"


def test_local_config_overrides_defaults(tmp_path, monkeypatch):
    (tmp_path / "config.toml").write_text(
        '[input]\ndem_dir = "custom/dems"\n[project]\nyears = ["2000", "2001"]\n'
        'reference_year = "2001"\n'
    )
    monkeypatch.delenv("NK_DEM_DIR", raising=False)
    cfg = load_config(tmp_path)
    assert cfg.dem_dir == (tmp_path / "custom/dems").resolve()
    assert cfg.dem("2000") == (tmp_path / "custom/dems/2000/2000_DSM.tif")
    assert cfg.years == ("2000", "2001")


def test_env_override_wins(tmp_path, monkeypatch):
    monkeypatch.setenv("NK_DEM_DIR", str(tmp_path / "env_dems"))
    cfg = load_config()
    assert cfg.dem_dir == (tmp_path / "env_dems").resolve()


def test_rel_is_posix_relative_inside_root():
    cfg = load_config()
    assert cfg.rel(cfg.dod_dir / "x.tif") == "dod/x.tif"


def test_require_files_lists_missing(tmp_path):
    existing = tmp_path / "ok.txt"
    existing.write_text("x")
    require_files({"ok": existing})
    try:
        require_files({"ok": existing, "falta": tmp_path / "nope.tif"})
    except FileNotFoundError as error:
        assert "falta" in str(error)
    else:  # pragma: no cover
        raise AssertionError("Se esperaba FileNotFoundError")


def test_years_include_reference():
    cfg = load_config()
    assert Path(cfg.reference_dem).name.endswith(".tif")
    assert cfg.reference_year in cfg.years
