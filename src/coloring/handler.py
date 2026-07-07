import re

import bpy

from ..preference import get_pref
from ...utils.logger import logger
from ...utils.node import get_comp_node_tree


class DepsgraphPostHandler:
    handlers: dict[callable, None] = {}
    _registered = False

    @classmethod
    def add(cls, handler: callable):
        cls.handlers[handler] = None

    @classmethod
    def remove(cls, handler: callable):
        cls.handlers.pop(handler, None)

    @classmethod
    @bpy.app.handlers.persistent
    def update(cls, scene, deps):
        if not scene.colorista_prop.enable_coloring:
            return
        for handler in cls.handlers:
            try:
                handler(scene)
            except Exception:
                logger.exception("Depsgraph handler failed")

    @classmethod
    def register(cls):
        if cls._registered:
            return
        bpy.app.handlers.depsgraph_update_post.append(cls.update)
        cls._registered = True

    @classmethod
    def unregister(cls):
        if not cls._registered:
            return
        try:
            bpy.app.handlers.depsgraph_update_post.remove(cls.update)
        except ValueError:
            pass
        cls._registered = False
        cls.handlers.clear()


def _main_node_group_name() -> str:
    pref = get_pref()
    if pref and pref.main_node_group_name:
        return pref.main_node_group_name
    return "Basic adjustment nodes for colorists"


def update_node_group(scene):
    pref = get_pref()
    verbose = pref.enable_logging if pref else False
    main_node_tree = get_comp_node_tree(scene)
    if not main_node_tree:
        return
    main_node_group = main_node_tree.nodes.get(_main_node_group_name())
    if not main_node_group or not main_node_group.node_tree:
        return
    for node in main_node_group.node_tree.nodes:
        match = re.match(r"inputs\[(\d+)\]", node.name)
        if not match:
            continue
        input_index = int(match.group(1))
        if input_index < len(main_node_group.inputs):
            input_socket = main_node_group.inputs[input_index]
            input_name = input_socket.name
            if input_socket.default_value == 0:
                node.mute = True
                if verbose:
                    logger.debug("Child node %s is blocked because the parameter is 0", node.name)
            else:
                node.label = f"Bound({input_name})"
                node.mute = False
                if verbose:
                    logger.debug("The new label for the child node is: %s", node.label)
        elif verbose:
            logger.debug("Input number %s is out of range", input_index)


class RenderHandler:
    handlers: dict[str, dict[callable, None]] = {
        "pre": {},
        "post": {},
        "init": {},
        "complete": {},
    }
    ctx = {}

    @classmethod
    def add(self, handler: callable, stage="pre"):
        if stage not in self.handlers:
            raise ValueError(f"Invalid stage: {stage}")
        self.handlers[stage][handler] = None

    @classmethod
    @bpy.app.handlers.persistent
    def update_pre(self, scene, deps):
        self.update_ex(scene, deps, "pre")

    @classmethod
    @bpy.app.handlers.persistent
    def update_init(self, scene, deps):
        self.update_ex(scene, deps, "init")

    @classmethod
    @bpy.app.handlers.persistent
    def update_post(self, scene, deps):
        self.update_ex(scene, deps, "post")

    @classmethod
    @bpy.app.handlers.persistent
    def update_complete(self, scene, deps):
        self.update_ex(scene, deps, "complete")

    @classmethod
    def update_ex(self, scene, deps, stage):
        for handler in self.handlers[stage]:
            try:
                handler(self, scene)
            except Exception:
                logger.exception("Render handler failed")

    @classmethod
    def register(self):
        bpy.app.handlers.render_init.append(self.update_init)
        bpy.app.handlers.render_pre.append(self.update_pre)
        bpy.app.handlers.render_post.append(self.update_post)
        bpy.app.handlers.render_complete.append(self.update_complete)

    @classmethod
    def unregister(self):
        for handler_list, fn in (
            (bpy.app.handlers.render_init, self.update_init),
            (bpy.app.handlers.render_pre, self.update_pre),
            (bpy.app.handlers.render_post, self.update_post),
            (bpy.app.handlers.render_complete, self.update_complete),
        ):
            try:
                handler_list.remove(fn)
            except ValueError:
                pass
        self.handlers.clear()


def switch_to_cpu_device(self: RenderHandler, scene: bpy.types.Scene):
    self.ctx["old_compositor_device"] = scene.render.compositor_device
    pref = get_pref()
    if pref and pref.force_use_cpu_render_image:
        scene.render.compositor_device = "CPU"


def restore_render_device(self: RenderHandler, scene: bpy.types.Scene):
    old = self.ctx.get("old_compositor_device")
    if old is not None:
        scene.render.compositor_device = old


def register():
    pass


def unregister():
    DepsgraphPostHandler.unregister()
    RenderHandler.unregister()
