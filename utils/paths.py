"""Addon / resource / user-preset path helpers (prefs-agnostic)."""

from __future__ import annotations

from pathlib import Path

import bpy

LANG_SUFFIXES = {
    "en_US": "EN",
    "zh_CN": "CN",
    "zh_HANS": "CN",
}

USER_PRESETS_DIR_NAME = "presets"


def _get_locale() -> str:
    if not bpy.context.preferences.view.use_translate_interface:
        return "en_US"
    return bpy.app.translations.locale


def _get_locale_suffix() -> str:
    return LANG_SUFFIXES.get(_get_locale(), "EN")


def get_package_root() -> str:
    """Extension / addon package id (parent of ``utils``)."""
    return __package__.rsplit(".", 1)[0]


def get_addon_root() -> Path:
    return Path(__file__).resolve().parent.parent


def get_resource_dir() -> Path:
    return get_addon_root().joinpath("resource")


def get_icons_dir() -> Path:
    return get_resource_dir().joinpath("icons")


def get_none_icon_path() -> Path:
    return get_icons_dir().joinpath("none.png")


def get_locale_dir(locale_suffix: str) -> Path:
    return get_resource_dir().joinpath(locale_suffix)


def _dir_has_assets(path: Path) -> bool:
    if not path.is_dir():
        return False
    try:
        for entry in path.iterdir():
            if entry.is_dir():
                return True
            if entry.suffix.lower() == ".blend":
                return True
    except OSError:
        return False
    return False


def get_resource_dir_locale() -> Path:
    preferred = get_locale_dir(_get_locale_suffix())
    if _dir_has_assets(preferred):
        return preferred
    fallback = get_locale_dir("CN")
    if _dir_has_assets(fallback):
        return fallback
    return preferred


def get_extension_user_folder() -> Path:
    """Persistent user data root (never the extension install tree).

    Prefers ``extension_path_user``. Falls back to ``user_resource`` only for
    legacy (non-extension) installs where ``extension_path_user`` raises.
    """
    try:
        path = Path(bpy.utils.extension_path_user(get_package_root()))
    except ValueError:
        # Legacy add-on install: extension_path_user is unavailable.
        path = Path(bpy.utils.user_resource("DATAFILES", path="Colorista", create=True))
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_default_user_presets_folder() -> Path:
    path = get_extension_user_folder().joinpath(USER_PRESETS_DIR_NAME)
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_user_presets_root(custom_path: str | None = None) -> Path:
    """Active root for user-saved presets.

    Pass *custom_path* from preferences when a custom folder is enabled; utils
    never imports the preferences package.
    """
    folder = get_default_user_presets_folder()
    if not custom_path or not str(custom_path).strip():
        return folder
    try:
        custom = Path(bpy.path.abspath(str(custom_path).strip())).resolve()
    except OSError:
        return folder
    if custom.is_file():
        return folder
    try:
        custom.mkdir(parents=True, exist_ok=True)
    except OSError:
        return folder
    return custom


def get_user_cache_dir() -> Path:
    cache = get_extension_user_folder().joinpath("cache")
    cache.mkdir(parents=True, exist_ok=True)
    return cache


def find_first_blend(directory: Path) -> Path | None:
    if not directory.is_dir():
        return None
    blends = sorted(directory.glob("*.blend"), key=lambda p: p.name.lower())
    return blends[0] if blends else None


def get_default_preset_path() -> Path | None:
    """Return bundled default preset (.blend) from the extension resource tree."""
    locale_suffixes = (
        _get_locale_suffix(),
        "CN",
        "EN",
    )
    seen: set[Path] = set()
    for suffix in locale_suffixes:
        category = get_locale_dir(suffix).joinpath("default")
        if category in seen:
            continue
        seen.add(category)

        direct = category.joinpath("default.blend")
        if direct.is_file():
            return direct

        nested = find_first_blend(category.joinpath("default"))
        if nested is not None:
            return nested

        fallback = find_first_blend(category)
        if fallback is not None:
            return fallback
    return None


def _asset_preset_key(asset_path: Path) -> Path:
    asset = Path(asset_path)
    try:
        rel = asset.resolve().relative_to(get_resource_dir().resolve())
        return rel.with_suffix("")
    except (ValueError, OSError):
        return Path(asset.stem)


def get_asset_preset_dir(asset_path: Path, *, custom_presets_root: str | None = None) -> Path:
    """User-writable preset folder for an asset (never under the install tree)."""
    root = resolve_user_presets_root(custom_presets_root)
    return root.joinpath(_asset_preset_key(asset_path))


def is_under_user_presets_root(
    path: Path | str,
    *,
    custom_presets_root: str | None = None,
) -> bool:
    try:
        Path(path).resolve().relative_to(resolve_user_presets_root(custom_presets_root).resolve())
    except (ValueError, OSError):
        return False
    return True


def is_user_preset_file(
    path: Path | str,
    *,
    custom_presets_root: str | None = None,
) -> bool:
    try:
        p = Path(path).resolve()
    except OSError:
        return False
    return (
        p.suffix.lower() == ".json"
        and p.is_file()
        and is_under_user_presets_root(p, custom_presets_root=custom_presets_root)
    )
