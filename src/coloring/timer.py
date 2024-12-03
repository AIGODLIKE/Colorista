import bpy


def update_device():
    if bpy.app.version >= (4, 4) or bpy.app.version < (4, 3):
        return 1
    render = bpy.context.scene.render
    if render.compositor_device != "GPU":
        render.compositor_device = "GPU"
        print("Changed compositor device to GPU")
    return 1


def register():
    bpy.app.timers.register(update_device, first_interval=1, persistent=True)


def unregister():
    bpy.app.timers.unregister(update_device)
