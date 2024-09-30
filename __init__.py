bl_info = {
    'name': 'Colorista',
    'author': '朔朔,会飞的键盘侠，只剩一瓶辣椒酱',
    'version': (1, 1, 0),
    'blender': (4, 0, 0),
    'location': '3DView->Panel',
    'category': 'Compositor',
    'doc_url': "https://github.com/AIGODLIKE/Colorista"
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
    try:
        unreg()
        logger.close()
    except AttributeError:
        # caused by blender 4.0 error
        import traceback
        traceback.print_exc()
