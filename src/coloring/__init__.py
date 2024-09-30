import bpy
from pathlib import Path


def get_modules():
    PREFIX = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    return [f.stem for f in Path(__file__).parent.iterdir() if f.name[0] in PREFIX]


register, unregister = bpy.utils.register_submodule_factory(__package__, get_modules())
