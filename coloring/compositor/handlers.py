"""Depsgraph / render handlers and color-space sync."""

from __future__ import annotations

import re
from typing import Callable

import bpy

from ...utils.logger import logger
from ...utils.node import get_comp_node_tree

VTC_NAME = "colorista-Color Space"

# Injected by coloring.runtime (keeps handlers free of prefs imports).
_main_node_group_name_fn: Callable[[], str] | None = None
_enable_logging_fn: Callable[[], bool] | None = None
_force_cpu_fn: Callable[[], bool] | None = None


def configure_handlers(
    *,
    main_node_group_name: Callable[[], str] | None = None,
    enable_logging: Callable[[], bool] | None = None,
    force_use_cpu: Callable[[], bool] | None = None,
) -> None:
    global _main_node_group_name_fn, _enable_logging_fn, _force_cpu_fn
    _main_node_group_name_fn = main_node_group_name
    _enable_logging_fn = enable_logging
    _force_cpu_fn = force_use_cpu


def _main_node_group_name() -> str:
    if _main_node_group_name_fn is not None:
        return _main_node_group_name_fn()
    return "Basic adjustment nodes for colorists"


def _verbose() -> bool:
    if _enable_logging_fn is not None:
        return _enable_logging_fn()
    return False


class DepsgraphPostHandler:
    handlers: dict = {}
    _registered = False

    @classmethod
    def add(cls, handler):
        cls.handlers[handler] = None

    @classmethod
    def remove(cls, handler):
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


def update_node_group(scene):
    verbose = _verbose()
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
            should_mute = input_socket.default_value == 0
            if should_mute:
                if not node.mute:
                    node.mute = True
                    if verbose:
                        logger.debug(
                            "Child node %s is blocked because the parameter is 0",
                            node.name,
                        )
            else:
                new_label = f"Bound({input_name})"
                if node.mute:
                    node.mute = False
                if node.label != new_label:
                    node.label = new_label
                    if verbose:
                        logger.debug("The new label for the child node is: %s", node.label)
        elif verbose:
            logger.debug("Input number %s is out of range", input_index)


class RenderHandler:
    _STAGES = ("pre", "post", "init", "complete")
    handlers: dict[str, dict] = {
        "pre": {},
        "post": {},
        "init": {},
        "complete": {},
    }
    ctx = {}
    _registered = False

    @classmethod
    def _ensure_stages(cls) -> None:
        for stage in cls._STAGES:
            if stage not in cls.handlers:
                cls.handlers[stage] = {}

    @classmethod
    def add(cls, handler, stage="pre"):
        cls._ensure_stages()
        if stage not in cls.handlers:
            raise ValueError(f"Invalid stage: {stage}")
        cls.handlers[stage][handler] = None

    @classmethod
    @bpy.app.handlers.persistent
    def update_pre(cls, scene, deps):
        cls.update_ex(scene, deps, "pre")

    @classmethod
    @bpy.app.handlers.persistent
    def update_init(cls, scene, deps):
        cls.update_ex(scene, deps, "init")

    @classmethod
    @bpy.app.handlers.persistent
    def update_post(cls, scene, deps):
        cls.update_ex(scene, deps, "post")

    @classmethod
    @bpy.app.handlers.persistent
    def update_complete(cls, scene, deps):
        cls.update_ex(scene, deps, "complete")

    @classmethod
    def update_ex(cls, scene, deps, stage):
        for handler in cls.handlers[stage]:
            try:
                handler(cls, scene)
            except Exception:
                logger.exception("Render handler failed")

    @classmethod
    def register(cls):
        if cls._registered:
            return
        bpy.app.handlers.render_init.append(cls.update_init)
        bpy.app.handlers.render_pre.append(cls.update_pre)
        bpy.app.handlers.render_post.append(cls.update_post)
        bpy.app.handlers.render_complete.append(cls.update_complete)
        cls._registered = True

    @classmethod
    def unregister(cls):
        if cls._registered:
            for handler_list, fn in (
                (bpy.app.handlers.render_init, cls.update_init),
                (bpy.app.handlers.render_pre, cls.update_pre),
                (bpy.app.handlers.render_post, cls.update_post),
                (bpy.app.handlers.render_complete, cls.update_complete),
            ):
                try:
                    handler_list.remove(fn)
                except ValueError:
                    pass
            cls._registered = False
        cls._ensure_stages()
        for stage in cls._STAGES:
            cls.handlers[stage].clear()


def switch_to_cpu_device(self: RenderHandler, scene: bpy.types.Scene):
    self.ctx["old_compositor_device"] = scene.render.compositor_device
    if _force_cpu_fn is not None and _force_cpu_fn():
        scene.render.compositor_device = "CPU"


def restore_render_device(self: RenderHandler, scene: bpy.types.Scene):
    old = self.ctx.get("old_compositor_device")
    if old is not None:
        scene.render.compositor_device = old


def has_custom_vt_control(scene: bpy.types.Scene | None = None) -> bool:
    scene = scene or bpy.context.scene
    tree = get_comp_node_tree(scene)
    if not tree:
        return False
    color_space_control = tree.nodes.get(VTC_NAME)
    if not color_space_control or not color_space_control.inputs:
        return False
    space = color_space_control.inputs.get("Space")
    if not space:
        space = color_space_control.inputs[0]
    return space is not None


def update_custom_vt(scene: bpy.types.Scene | None = None) -> None:
    scene = scene or bpy.context.scene
    if not has_custom_vt_control(scene):
        return
    tree = get_comp_node_tree(scene)
    color_space_control = tree.nodes.get(VTC_NAME)
    space = color_space_control.inputs.get("Space")
    if not space:
        space = color_space_control.inputs[0]
    try:
        color_space = float(space.default_value)
        ori_vt = scene.view_settings.view_transform
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
