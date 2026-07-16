bl_info = {
    "name": "Colorista",
    "author": "朔朔,会飞的键盘侠，只剩一瓶辣椒酱",
    "version": (1, 2, 2),
    "blender": (4, 2, 0),
    "location": "3DView->Panel",
    "category": "Compositor",
    "doc_url": "https://github.com/AIGODLIKE/Colorista",
}

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

    try:
        unreg()
    finally:
        Icon.cleanup()
        logger.close()
