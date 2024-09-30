import bpy

modules = (
    "timer",
    "watcher",
)

register, unregister = bpy.utils.register_submodule_factory(__package__, modules)
