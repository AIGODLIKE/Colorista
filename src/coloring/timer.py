import bpy
import traceback


class UpdateTimer1s:
    timers: dict[callable, None] = {}

    @classmethod
    def add(cls, timer):
        cls.timers[timer] = None

    @classmethod
    def remove(cls, timer):
        cls.timers.pop(timer, None)

    @classmethod
    def _run_ex(cls):
        for timer in cls.timers:
            try:
                timer()
            except Exception:
                traceback.print_exc()

    @classmethod
    def _run(cls,):
        try:
            cls._run_ex()
        except Exception:
            traceback.print_exc()
        return 1

    @classmethod
    def register(cls):
        bpy.app.timers.register(cls._run, first_interval=1, persistent=True)

    @classmethod
    def unregister(cls):
        bpy.app.timers.unregister(cls._run)
        cls.timers.clear()


def update_device():
    if not bpy.context.scene.colorista_prop.enable_coloring:
        return
    if bpy.app.version >= (4, 4) or bpy.app.version < (4, 3):
        return
    render = bpy.context.scene.render
    if render.compositor_device != "GPU":
        render.compositor_device = "GPU"
        print("Changed compositor device to GPU")


def set_attr_if_not_equal(obj, attr, value):
    try:
        if getattr(obj, attr) == value:
            return
        setattr(obj, attr, value)
    except Exception:
        ...


def update_color_manager():
    if not bpy.context.scene.colorista_prop.enable_coloring:
        return
    set_attr_if_not_equal(bpy.context.scene.view_settings, "view_transform", "Raw")
    set_attr_if_not_equal(bpy.context.scene.view_settings, "look", "None")
    set_attr_if_not_equal(bpy.context.scene.view_settings, "exposure", 0)
    set_attr_if_not_equal(bpy.context.scene.view_settings, "gamma", 1)
    set_attr_if_not_equal(bpy.context.scene.view_settings, "use_curve_mapping", False)


def register():
    UpdateTimer1s.add(update_device)
    UpdateTimer1s.add(update_color_manager)
    UpdateTimer1s.register()


def unregister():
    UpdateTimer1s.unregister()
