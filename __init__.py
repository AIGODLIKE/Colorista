bl_info = {
    'name': 'Colorista',
    'author': '朔朔,会飞的键盘侠，只剩一瓶辣椒酱',
    'version': (1, 0, 0),
    'blender': (4, 0, 0),
    'location': '3DView->Panel',
    'category': 'Compositor',
    'doc_url': "https://github.com/AIGODLIKE/Colorista"
}

import sys

from .src import register as reg
from .src import unregister as unreg
from .utils.logger import logger
from .utils import register_util, unregister_util


def register():
    register_util()
    reg()


def unregister():
    unreg()
    unregister_util()
    modules_update()


def modules_update():
    logger.close()
    for i in list(sys.modules):
        if not i.startswith(__package__) or i == __package__:
            continue
        del sys.modules[i]
    del sys.modules[__package__]
