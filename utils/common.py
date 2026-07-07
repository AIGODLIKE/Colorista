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
    return get_resource_dir()


def _dir_has_assets(path: Path) -> bool:
    if not path.is_dir():
        return False
    try:
        for entry in path.iterdir():
            if entry.is_dir():
                return True
    except OSError:
        return False
    return False


def get_resource_dir_locale() -> Path:
    preferred = get_resource_dir() / _get_locale_suffix()
    if _dir_has_assets(preferred):
        return preferred
    fallback = get_resource_dir() / "CN"
    if _dir_has_assets(fallback):
        return fallback
    return preferred


def get_package_root() -> str:
    return __package__.rsplit(".", 1)[0]


def get_user_cache_dir() -> Path:
    cache = Path(bpy.utils.extension_path_user(get_package_root())) / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    return cache


def find_first_blend(directory: Path) -> Path | None:
    if not directory.is_dir():
        return None
    blends = sorted(directory.glob("*.blend"), key=lambda p: p.name.lower())
    return blends[0] if blends else None


def get_default_preset_path() -> Path | None:
    candidates = (
        get_resource_dir_locale() / "default" / "default",
        get_resource_dir() / "CN" / "default" / "default",
        get_resource_dir_locale() / "Default" / "default",
        get_resource_dir() / "EN" / "default" / "default",
    )
    for directory in candidates:
        preset = find_first_blend(directory)
        if preset is not None:
            return preset
    return None


@lru_cache(maxsize=4)
def get_resource_dir_cache(locale):
    return get_resource_dir() / LANG_SUFFIXES.get(locale, "EN")
