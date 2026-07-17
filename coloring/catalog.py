"""Asset / preset directory listing for EnumProperty items."""

from __future__ import annotations

from pathlib import Path

from .constants import PRESET_NONE_ID
from ..utils.icon import Icon
from ..utils.paths import get_asset_preset_dir, get_none_icon_path, get_resource_dir_locale
from ..utils.watcher import FSWatcher
from .config import get_config

_ICON_SUFFIXES = (".png", ".jpg", ".jpeg", ".tiff")

_cache: dict[str, tuple[int | None, list]] = {}


def _path_key(path: Path) -> str:
    try:
        return path.resolve().as_posix()
    except OSError:
        return path.as_posix()


def _dir_mtime(path: Path) -> int | None:
    try:
        if path.exists():
            return path.stat().st_mtime_ns
    except OSError:
        pass
    return None


def invalidate(path: Path | str | None = None) -> None:
    if path is None:
        _cache.clear()
        return
    _cache.pop(_path_key(Path(path)), None)


def find_icon(name: str, directory: Path) -> Path:
    for suf in _ICON_SUFFIXES:
        img = directory.joinpath(name).with_suffix(suf)
        if img.exists():
            return img
    return get_none_icon_path()


def _register_asset_icon(icon_path: Path) -> int:
    Icon.reg_icon(icon_path)
    return Icon.get_icon_id(icon_path)


def _refresh_cached_enum_icons(items: list) -> list:
    """Re-resolve preview icon_ids.

    After addon disable/enable, ``bpy.utils.previews`` IDs are invalidated but
    directory mtimes are unchanged — cached tuples must not keep stale IDs.
    """
    if not items:
        return items
    refreshed = []
    changed = False
    for item in items:
        if len(item) < 5:
            refreshed.append(item)
            continue
        identifier, name, desc, icon_id, idx = item
        if identifier == PRESET_NONE_ID:
            refreshed.append(item)
            continue
        path = Path(identifier)
        if path.suffix.lower() not in {".blend", ".json"}:
            refreshed.append(item)
            continue
        new_id = _register_asset_icon(find_icon(path.stem, path.parent))
        if new_id != icon_id:
            changed = True
            refreshed.append((identifier, name, desc, new_id, idx))
        else:
            refreshed.append(item)
    return refreshed if changed else items


def _get_cached(directory: Path, builder) -> list:
    key = _path_key(directory)
    FSWatcher.register(directory)
    mtime = _dir_mtime(directory)
    changed = FSWatcher.consume_change(directory)
    if not changed and key in _cache:
        cached_mtime, items = _cache[key]
        if cached_mtime == mtime:
            refreshed = _refresh_cached_enum_icons(items)
            _cache[key] = (mtime, refreshed)
            return refreshed
    items = builder()
    _cache[key] = (mtime, items)
    return items


def list_categories(_context=None) -> list:
    rdir = get_resource_dir_locale()

    def build():
        items = []
        if rdir.is_dir():
            for f in rdir.iterdir():
                if f.is_file():
                    continue
                items.append((f.as_posix(), f.name, f.name, 0, len(items)))
        items.sort(key=lambda x: x[1])
        return items

    return _get_cached(rdir, build)


def list_assets(category: str, _context=None) -> list:
    if not category:
        return []
    rdir = Path(category)

    def build():
        items = []
        if rdir.is_dir():
            for f in sorted(rdir.glob("*.blend"), key=lambda x: x.name):
                icon_path = find_icon(f.stem, rdir)
                icon_id = _register_asset_icon(icon_path)
                items.append((f.as_posix(), f.stem, f.stem, icon_id, len(items)))
        return items

    return _get_cached(rdir, build)


def list_presets(asset_path: str, _context=None) -> list:
    if not asset_path:
        return [(PRESET_NONE_ID, "None", "No preset available", 0)]
    asset = Path(asset_path)
    preset_dir = get_asset_preset_dir(asset, custom_presets_root=get_config().custom_presets_root)

    def build():
        items = []
        if preset_dir.is_dir():
            for file in sorted(preset_dir.glob("*.json"), key=lambda x: x.name):
                icon_path = find_icon(file.stem, preset_dir)
                icon_id = _register_asset_icon(icon_path)
                items.append((file.as_posix(), file.stem, file.stem, icon_id, len(items)))
        elif asset.is_file() and asset.suffix.lower() == ".blend":
            icon_path = find_icon(asset.stem, asset.parent)
            icon_id = _register_asset_icon(icon_path)
            items.append((asset.as_posix(), asset.stem, asset.stem, icon_id, 0))
        if not items:
            items.append((PRESET_NONE_ID, "None", "No preset available", 0))
        return items

    return _get_cached(preset_dir, build)


def enum_item_index(items, identifier: str) -> int:
    for index, item in enumerate(items):
        if item[0] == identifier:
            return index
    return 0


def resolve_enum_value(items, current: str) -> str:
    if not items:
        return ""
    if current in {item[0] for item in items}:
        return current
    return items[0][0]
