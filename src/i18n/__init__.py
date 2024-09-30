import bpy
from .loader import load_translations


def _T(text, ctx=None) -> str:
    return bpy.app.translations.pgettext(text, ctx)


def register():
    translations = load_translations()
    bpy.app.translations.register(__name__, translations)


def unregister():
    bpy.app.translations.unregister(__name__)
