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


def get_resource_dir() -> Path:
    return Path(__file__).parent.parent / "resource"


def grd() -> Path:
    """
    简写版
    """
    return get_resource_dir()


def get_resource_dir_locale() -> Path:
    return get_resource_dir() / _get_locale_suffix()


def get_package_root() -> str:
    return __package__.rsplit(".", 1)[0]


def get_user_cache_dir() -> Path:
    cache = Path(bpy.utils.extension_path_user(get_package_root())) / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    return cache


def get_default_preset_path() -> Path:
    return get_resource_dir_locale() / "default" / "default.blend"


@lru_cache(maxsize=4)
def get_resource_dir_cache(locale):
    return get_resource_dir() / LANG_SUFFIXES.get(locale, "EN")
