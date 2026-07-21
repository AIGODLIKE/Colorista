from pathlib import Path
import importlib

# Blender renamed the Simplified Chinese locale from "zh_CN" to "zh_HANS" in
# 4.0; serve both keys so preferences saved under either name still resolve.
LOCALE_ALIASES = {"zh_CN": "zh_HANS"}


def compile_translation(translations) -> dict:
    """Build Blender's {(context, source): translation} mapping.

    Items are (source, translation) or (source, translation, context) tuples.
    """
    t = {}
    for item in translations:
        if len(item) < 2:
            continue
        context = None if len(item) == 2 else item[2]
        source, translation = item[:2]
        t[(context, source)] = translation
    return t


def load_translations():
    translations_dir = Path(__file__).resolve().parent.joinpath("translations")
    translations_dict = {}

    for translation_file in translations_dir.glob("*.py"):
        if translation_file.stem == "__init__":
            continue
        language_code = translation_file.stem
        locale = language_code.replace('-', '_')
        translation_module = importlib.import_module(f".translations.{language_code}", package=__package__)
        if not hasattr(translation_module, "translations"):
            continue
        translations_dict[locale] = compile_translation(translation_module.translations)

    for alias, source in LOCALE_ALIASES.items():
        if alias not in translations_dict and source in translations_dict:
            translations_dict[alias] = translations_dict[source]

    return translations_dict
