import sys

import bpy
from pathlib import Path
from functools import lru_cache

LANG_SUFFIXES = {
    "en_US": "EN",
    "zh_CN": "CN",
    "zh_HANS": "CN",
}


def _get_locale():
    if not bpy.context.preferences.view.use_translate_interface:
        return "en_US"
    return bpy.app.translations.locale


def _get_locale_suffix():
    return LANG_SUFFIXES.get(_get_locale(), "EN")


def get_addon_root() -> Path:
    root_pkg = get_package_root()
    mod = sys.modules.get(root_pkg)
    if mod is not None and getattr(mod, "__file__", None):
        return Path(mod.__file__).resolve().parent
    return Path(__file__).resolve().parent.parent


def get_resource_dir() -> Path:
    return get_addon_root().joinpath("resource")


def grd() -> Path:
    return get_resource_dir()


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


def get_package_root() -> str:
    return __package__.rsplit(".", 1)[0]


def get_user_cache_dir() -> Path:
    cache = Path(bpy.utils.extension_path_user(get_package_root())).joinpath("cache")
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

    resource = get_resource_dir()
    if resource.is_dir():
        for blend in sorted(resource.rglob("default.blend")):
            if blend.is_file():
                return blend
    return None


def get_asset_preset_dir(asset_path: Path) -> Path:
    asset = Path(asset_path)
    return asset.parent.joinpath(asset.stem)


@lru_cache(maxsize=4)
def get_resource_dir_cache(locale):
    return get_locale_dir(LANG_SUFFIXES.get(locale, "EN"))
