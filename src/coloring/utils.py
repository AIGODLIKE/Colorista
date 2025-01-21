import bpy


def get_viewport_shadings() -> list[bpy.types.View3DShading]:
    shadings = []
    for area in bpy.context.screen.areas:
        if area.type != "VIEW_3D":
            continue
        shadings += [s.shading for s in area.spaces if s.type == "VIEW_3D"]

    return shadings


def set_viewport_shading(mode):
    for shading in get_viewport_shadings():
        shading.use_compositor = mode


def toggle_viewport_shading():
    for shading in get_viewport_shadings():
        if shading.use_compositor == "ALWAYS":
            shading.use_compositor = "DISABLED"
        else:
            shading.use_compositor = "ALWAYS"


def register():
    ...


def unregister():
    ...
