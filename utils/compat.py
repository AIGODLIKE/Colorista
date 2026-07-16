"""Blender version helpers for Colorista."""

import bpy

IS_BL5 = bpy.app.version >= (5, 0, 0)
IS_BL42_PLUS = bpy.app.version >= (4, 2, 0)
IS_BL42_TO_43 = (4, 2) <= bpy.app.version <= (4, 3)


def layout_separator(layout) -> None:
    if IS_BL42_PLUS:
        layout.separator(type="LINE")
    else:
        layout.separator()
