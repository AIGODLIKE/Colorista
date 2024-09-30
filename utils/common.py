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


@lru_cache(maxsize=4)
def get_resource_dir_cache(locale):
    return get_resource_dir() / LANG_SUFFIXES.get(locale, "EN")
