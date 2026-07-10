"""Module-level runtime state (not stored on PropertyGroup)."""

loaded_node_groups: set = set()
last_loaded_preset: str | None = None


def preset_key(path) -> str:
    from pathlib import Path
    try:
        return str(Path(path).resolve())
    except Exception:
        return str(path)


def clear_loaded_preset() -> None:
    global last_loaded_preset
    last_loaded_preset = None


def set_loaded_preset(path) -> None:
    global last_loaded_preset
    last_loaded_preset = preset_key(path)
