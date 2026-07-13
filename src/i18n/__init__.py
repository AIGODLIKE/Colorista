import bpy
from .loader import load_translations


def _T(text, ctx=None) -> str:
    return bpy.app.translations.pgettext(text, ctx)


def _addon_package() -> str:
    # src.i18n -> extension root (same depth as src.preference.get_package)
    return __package__.rsplit(".", 2)[0]


def register():
    translations = load_translations()
    bpy.app.translations.register(_addon_package(), translations)


def unregister():
    bpy.app.translations.unregister(_addon_package())
