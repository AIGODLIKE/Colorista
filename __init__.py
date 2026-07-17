from . import register_mod

bl_info = {
    "name": "Colorista",
    "author": "朔朔,会飞的键盘侠，只剩一瓶辣椒酱",
    "version": (1, 2, 2),
    "blender": (4, 2, 0),
    "location": "3DView->Panel",
    "category": "Compositor",
    "doc_url": "https://github.com/AIGODLIKE/Colorista",
}


def register():
    register_mod.register()


def unregister():
    register_mod.unregister()
