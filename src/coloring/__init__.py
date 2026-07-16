import bpy


def get_modules():
    # Explicit order: PropertyGroup before operators/UI that reference them.
    return (
        "properties",
        "operators",
        "history",
        "panels",
        "gizmo",
    )


_reg, _unreg = bpy.utils.register_submodule_factory(__package__, get_modules())


def register():
    _reg()
    from .runtime import register as runtime_register

    runtime_register()


def unregister():
    from .runtime import unregister as runtime_unregister

    runtime_unregister()
    _unreg()
