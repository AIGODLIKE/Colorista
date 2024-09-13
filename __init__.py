bl_info = {
    'name': 'Colorista',
    'author': '会飞的键盘侠',
    'version': (0, 0, 1),
    'blender': (4, 0, 0),
    'location': '3DView->Panel',
    'category': '辣椒出品',
    'doc_url': "https://github.com/AIGODLIKE/Colorista"
}

import sys
import bpy
from .src import register as reg
from .src import unregister as unreg
from .utils.logger import logger


def register():
    if bpy.app.version < (4, 0, 0):
        return
        raise RuntimeError('Blender版本不得低于 4.0.0')
    logger.debug(f'{bl_info["name"]}: register')
    reg()


def unregister():
    logger.debug(f'{bl_info["name"]}: unregister')
    unreg()
    modules_update()


def modules_update():
    from .utils.logger import logger
    logger.close()
    for i in list(sys.modules):
        if not i.startswith(__package__) or i == __package__:
            continue
        del sys.modules[i]
    del sys.modules[__package__]
