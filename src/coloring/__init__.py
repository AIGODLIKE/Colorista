import bpy
from pathlib import Path


def get_modules():
    PREFIX = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    SKIP = {"runtime", "state", "serialize"}
    return [f.stem for f in Path(__file__).parent.iterdir()
            if f.name[0] in PREFIX and f.stem not in SKIP]


_reg, _unreg = bpy.utils.register_submodule_factory(__package__, get_modules())


def register():
    _reg()
    from .runtime import register as runtime_register

    runtime_register()


def unregister():
    from .runtime import unregister as runtime_unregister

    runtime_unregister()
    _unreg()
