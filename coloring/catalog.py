"""Asset / preset directory listing for EnumProperty items.

Enum items are built once (lazy on first access) and kept until
``invalidate()`` — called on addon register/reload and when the user
saves/deletes a preset. Panel redraw must not touch the filesystem.
"""

from __future__ import annotations

from pathlib import Path

from .constants import PRESET_NONE_ID
from ..utils.icon import Icon
from ..utils.paths import get_asset_preset_dir, get_none_icon_path, get_resource_dir_locale
from .config import get_config

_ICON_SUFFIXES = (".png", ".jpg", ".jpeg", ".tiff")

# (items, Icon._generation) — generation invalidates preview icon_ids after reload.
_cache: dict[str, tuple[list, int]] = {}
_path_key_memo: dict[str, str] = {}
_locale_dir_memo: Path | None = None
_preset_dir_memo: dict[str, Path] = {}
_UNSET = object()
_custom_root_memo: str | None | object = _UNSET


def _path_key(path: Path) -> str:
    raw = path.as_posix()
    memo = _path_key_memo.get(raw)
    if memo is not None:
        return memo
    try:
        key = path.resolve().as_posix()
    except OSError:
        key = raw
    _path_key_memo[raw] = key
    return key


def invalidate(path: Path | str | None = None) -> None:
    """Drop cached enum lists. ``None`` clears everything (register / prefs)."""
    global _locale_dir_memo, _custom_root_memo
    if path is None:
        _cache.clear()
        _preset_dir_memo.clear()
        _locale_dir_memo = None
        _custom_root_memo = _UNSET
        return
    key = _path_key(Path(path))
    _cache.pop(key, None)


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
    """Re-resolve preview icon_ids after preview collection recreate."""
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
    icon_gen = Icon._generation
    entry = _cache.get(key)
    if entry is not None:
        items, cached_gen = entry
        if cached_gen == icon_gen:
            return items
        items = _refresh_cached_enum_icons(items)
        _cache[key] = (items, icon_gen)
        return items
    items = builder()
    _cache[key] = (items, icon_gen)
    return items


def _locale_resource_dir() -> Path:
    global _locale_dir_memo
    if _locale_dir_memo is not None:
        return _locale_dir_memo
    _locale_dir_memo = get_resource_dir_locale()
    return _locale_dir_memo


def _custom_presets_root() -> str | None:
    global _custom_root_memo
    if _custom_root_memo is not _UNSET:
        return _custom_root_memo  # type: ignore[return-value]
    root = get_config().custom_presets_root
    _custom_root_memo = root
    return root


def _preset_dir_for_asset(asset_path: str) -> Path:
    hit = _preset_dir_memo.get(asset_path)
    if hit is not None:
        return hit
    preset_dir = get_asset_preset_dir(
        Path(asset_path),
        custom_presets_root=_custom_presets_root(),
    )
    _preset_dir_memo[asset_path] = preset_dir
    return preset_dir


def list_categories(_context=None) -> list:
    rdir = _locale_resource_dir()

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
    preset_dir = _preset_dir_for_asset(asset_path)

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
