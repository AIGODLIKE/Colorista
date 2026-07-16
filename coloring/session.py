"""Module-level coloring session state."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


def preset_key(path) -> str:
    try:
        return str(Path(path).resolve())
    except Exception:
        return str(path)


class ColoringSession:
    def __init__(self) -> None:
        self.loaded_node_groups: set = set()
        self.last_loaded_preset: str | None = None
        self.last_loaded_asset: str | None = None
        self._suppress_asset_import = False

    @property
    def suppress_asset_import(self) -> bool:
        return self._suppress_asset_import

    @contextmanager
    def suppress_asset_updates(self) -> Iterator[None]:
        prev = self._suppress_asset_import
        self._suppress_asset_import = True
        try:
            yield
        finally:
            self._suppress_asset_import = prev

    def clear_loaded_preset(self) -> None:
        self.last_loaded_preset = None
        self.last_loaded_asset = None

    def set_loaded_preset(self, path) -> None:
        self.last_loaded_preset = preset_key(path)

    def set_loaded_asset(self, path) -> None:
        self.last_loaded_asset = preset_key(path)


session = ColoringSession()
