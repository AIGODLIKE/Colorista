import bpy

from .utils.logger import logger

modules = (
    "src",
    "utils",
)

reg, unreg = bpy.utils.register_submodule_factory(__package__, modules)


def register():
    reg()


def unregister():
    from .utils.icon import Icon

    unreg()
    Icon.cleanup()
    logger.close()
