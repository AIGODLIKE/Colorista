"""Module-level runtime state (not stored on PropertyGroup)."""

loaded_node_groups: set = set()
last_loaded_preset: str | None = None
last_loaded_asset: str | None = None
suppress_asset_import: bool = False


def preset_key(path) -> str:
    from pathlib import Path
    try:
        return str(Path(path).resolve())
    except Exception:
        return str(path)


def clear_loaded_preset() -> None:
    global last_loaded_preset, last_loaded_asset
    last_loaded_preset = None
    last_loaded_asset = None


def set_loaded_preset(path) -> None:
    global last_loaded_preset
    last_loaded_preset = preset_key(path)


def set_loaded_asset(path) -> None:
    global last_loaded_asset
    last_loaded_asset = preset_key(path)


def set_suppress_asset_import(value: bool) -> None:
    global suppress_asset_import
    suppress_asset_import = value
