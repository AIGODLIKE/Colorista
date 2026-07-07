import bpy
from functools import partial

from ...utils.logger import logger
from ...utils.node import get_comp_node_tree


class UpdateTimer1s:
    timers: dict[callable, None] = {}
    _prun = None
    _registered = False

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
                logger.exception("Timer callback failed")

    @classmethod
    def _run(cls,):
        try:
            cls._run_ex()
        except Exception:
            logger.exception("UpdateTimer1s failed")
        return 1

    @classmethod
    def register(cls):
        if cls._registered:
            return
        cls._prun = partial(cls._run)
        bpy.app.timers.register(cls._prun, first_interval=1, persistent=True)
        cls._registered = True

    @classmethod
    def unregister(cls):
        if cls._registered and cls._prun is not None:
            try:
                bpy.app.timers.unregister(cls._prun)
            except Exception:
                pass
        cls._registered = False
        cls._prun = None
        cls.timers.clear()


def update_device():
    if not bpy.context.scene.colorista_prop.enable_coloring:
        return
    if bpy.app.version >= (4, 4) or bpy.app.version < (4, 3):
        return
    render = bpy.context.scene.render
    if render.compositor_device != "GPU":
        render.compositor_device = "GPU"
        logger.debug("Changed compositor device to GPU")


VTC_NAME = "colorista-Color Space"


def has_custom_vt_control() -> bool:
    tree = get_comp_node_tree(bpy.context.scene)
    if not tree:
        return False
    color_space_control = tree.nodes.get(VTC_NAME)
    if not color_space_control:
        return False
    if not color_space_control.inputs:
        return False
    space = color_space_control.inputs.get("Space")
    if not space:
        space = color_space_control.inputs[0]
    return space is not None


def update_custom_vt():
    if not has_custom_vt_control():
        return
    tree = get_comp_node_tree(bpy.context.scene)
    color_space_control = tree.nodes.get(VTC_NAME)
    space = color_space_control.inputs.get("Space")
    if not space:
        space = color_space_control.inputs[0]
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
    except Exception:
        pass


def register():
    pass


def unregister():
    UpdateTimer1s.unregister()
