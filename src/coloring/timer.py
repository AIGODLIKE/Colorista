import bpy
import traceback
from functools import partial


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
        cls._prun = partial(cls._run)
        bpy.app.timers.register(cls._prun, first_interval=1, persistent=True)

    @classmethod
    def unregister(cls):
        bpy.app.timers.unregister(cls._prun)
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


VTC_NAME = "colorista-Color Space"


def has_custom_vt_control() -> bool:
    tree = bpy.context.scene.node_tree
    if not tree:
        return
    color_space_control = tree.nodes.get(VTC_NAME)
    if not color_space_control:
        return
    if not color_space_control.inputs:
        return
    space = color_space_control.inputs.get("Space")
    if not space:
        space = color_space_control.inputs[0]
    return True


def update_custom_vt():
    if not has_custom_vt_control():
        return
    tree = bpy.context.scene.node_tree
    color_space_control = tree.nodes.get(VTC_NAME)
    space = color_space_control.inputs.get("Space")
    try:
        color_space = float(space.default_value)
        ori_vt = bpy.context.scene.view_settings.view_transform
        space_value_map = {
            "AgX": 0,
            "Standard": 0.1,
            "Filmic": 0.2,
            "Khronos PBR Neutral": 0.3,
        }
        space_value = space_value_map.get(ori_vt, 0)
        if abs(space_value - color_space) < 0.00001:
            return
        space.default_value = space_value
        # vt = ori_vt
        # if abs(color_space) < 0.001:
        #     # AgX
        #     vt = "AgX"
        # elif abs(color_space - 0.1) < 0.001:
        #     vt = "Standard"
        # elif abs(color_space - 0.2) < 0.001:
        #     vt = "Filmic"
        # elif abs(color_space - 0.3) < 0.001:
        #     vt = "Khronos PBR Neutral"
        # if vt != ori_vt:
        #     bpy.context.scene.view_settings.view_transform = vt
    except Exception:
        pass


def update_color_manager():
    return
    if not bpy.context.scene.colorista_prop.enable_coloring:
        return
    if not has_custom_vt_control():
        set_attr_if_not_equal(bpy.context.scene.view_settings, "view_transform", "Raw")
    set_attr_if_not_equal(bpy.context.scene.view_settings, "look", "None")
    set_attr_if_not_equal(bpy.context.scene.view_settings, "exposure", 0)
    set_attr_if_not_equal(bpy.context.scene.view_settings, "gamma", 1)
    set_attr_if_not_equal(bpy.context.scene.view_settings, "use_curve_mapping", False)


def register():
    UpdateTimer1s.add(update_device)
    UpdateTimer1s.add(update_color_manager)
    UpdateTimer1s.add(update_custom_vt)
    UpdateTimer1s.register()


def unregister():
    UpdateTimer1s.unregister()
