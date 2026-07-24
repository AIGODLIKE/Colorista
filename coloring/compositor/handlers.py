"""Event-driven compositor synchronization and render handlers."""

from __future__ import annotations

import re
from typing import Callable

import bpy

from ...utils.logger import logger
from ...utils.node import get_comp_node_tree
from .device import set_compositor_device

VTC_NAME = "colorista-Color Space"

# Inner nodes bound to a group input are named "inputs[<socket index>]".
_BOUND_NODE_RE = re.compile(r"inputs\[(\d+)\]")

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


class ColoristaMsgBusMonitor:
    """Track scene/tree replacement and the scene view transform."""

    _owner = object()
    _scene_pointer: int | None = None
    _tree_pointer: int | None = None
    _registered = False
    _updating = False

    @classmethod
    def _subscribe_property(
        cls,
        owner,
        data_path: str,
        *,
        type_wide: bool = False,
    ) -> bool:
        try:
            key = (
                (type(owner), data_path)
                if type_wide
                else owner.path_resolve(data_path, False)
            )
            bpy.msgbus.subscribe_rna(
                key=key,
                owner=cls._owner,
                args=(),
                notify=cls.update,
            )
        except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
            return False
        return True

    @classmethod
    def refresh(cls, scene: bpy.types.Scene) -> None:
        """Subscribe only to RNA state not represented by compositor links."""
        bpy.msgbus.clear_by_owner(cls._owner)
        cls._scene_pointer = scene.as_pointer()
        tree = get_comp_node_tree(scene)
        cls._tree_pointer = tree.as_pointer() if tree is not None else None
        if not cls._registered:
            return

        # Rebuild subscriptions when the compositor tree itself is replaced.
        cls._subscribe_property(scene, "compositing_node_group", type_wide=True)
        cls._subscribe_property(scene.view_settings, "view_transform", type_wide=True)

    @classmethod
    def update(cls) -> None:
        if not cls._registered or cls._updating:
            return
        try:
            scene = bpy.context.scene
            props = getattr(scene, "colorista_prop", None)
            if props is None or not props.enable_coloring:
                return
            tree = get_comp_node_tree(scene)
            tree_pointer = tree.as_pointer() if tree is not None else None
            if scene.as_pointer() != cls._scene_pointer or tree_pointer != cls._tree_pointer:
                cls.refresh(scene)
            if tree is None:
                return
        except (AttributeError, ReferenceError):
            return

        cls._updating = True
        try:
            update_custom_vt(scene)
        except Exception:
            logger.exception("Colorista view-transform synchronization failed")
        finally:
            cls._updating = False

    @classmethod
    def register(cls, scene: bpy.types.Scene | None = None) -> None:
        cls._registered = True
        cls.refresh(scene or bpy.context.scene)

    @classmethod
    def unregister(cls) -> None:
        bpy.msgbus.clear_by_owner(cls._owner)
        cls._registered = False
        cls._scene_pointer = None
        cls._tree_pointer = None
        cls._updating = False


def update_node_group(scene):
    verbose = _verbose()
    main_node_tree = get_comp_node_tree(scene)
    if not main_node_tree:
        return
    main_node_group = main_node_tree.nodes.get(_main_node_group_name())
    if not main_node_group or not main_node_group.node_tree:
        return
    for node in main_node_group.node_tree.nodes:
        match = _BOUND_NODE_RE.match(node.name)
        if not match:
            continue
        input_index = int(match.group(1))
        if input_index < len(main_node_group.inputs):
            input_socket = main_node_group.inputs[input_index]
            input_name = input_socket.name
            # Node-socket edits do not reliably publish RNA message-bus events.
            # Keep the native graph live and let its own value links determine
            # the neutral/effect result instead of relying on Python to unmute.
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
    _STAGES = ("pre", "post", "init", "complete", "cancel")
    # Insertion-ordered "sets" of callbacks per render stage.
    handlers: dict[str, dict] = {stage: {} for stage in _STAGES}
    ctx = {}
    _registered = False

    @classmethod
    def add(cls, handler, stage="pre"):
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
    @bpy.app.handlers.persistent
    def update_cancel(cls, scene, deps):
        cls.update_ex(scene, deps, "cancel")

    @classmethod
    def update_ex(cls, scene, deps, stage):
        for handler in cls.handlers[stage]:
            try:
                handler(cls, scene)
            except Exception:
                logger.exception("Render handler failed")

    @classmethod
    def register(cls):
        for handler_list, fn in (
            (bpy.app.handlers.render_init, cls.update_init),
            (bpy.app.handlers.render_pre, cls.update_pre),
            (bpy.app.handlers.render_post, cls.update_post),
            (bpy.app.handlers.render_complete, cls.update_complete),
            (bpy.app.handlers.render_cancel, cls.update_cancel),
        ):
            if fn not in handler_list:
                handler_list.append(fn)
        cls._registered = True

    @classmethod
    def unregister(cls):
        for handler_list, fn in (
            (bpy.app.handlers.render_init, cls.update_init),
            (bpy.app.handlers.render_pre, cls.update_pre),
            (bpy.app.handlers.render_post, cls.update_post),
            (bpy.app.handlers.render_complete, cls.update_complete),
            (bpy.app.handlers.render_cancel, cls.update_cancel),
        ):
            while fn in handler_list:
                handler_list.remove(fn)
        cls._registered = False
        for stage_handlers in cls.handlers.values():
            stage_handlers.clear()
        cls.ctx.clear()


def switch_to_cpu_device(handler_cls: type[RenderHandler], scene: bpy.types.Scene):
    """Stash the device once per render job (render_init), not per frame.

    Stashing on render_pre would overwrite the stash with the already-forced
    "CPU" value from the second animation frame on, losing the user setting.
    """
    props = getattr(scene, "colorista_prop", None)
    if props is None or not props.enable_coloring:
        return
    if _force_cpu_fn is None or not _force_cpu_fn():
        return
    if "old_compositor_device" not in handler_cls.ctx:
        handler_cls.ctx["old_compositor_device"] = scene.render.compositor_device
    set_compositor_device(scene.render, "CPU")


def restore_render_device(handler_cls: type[RenderHandler], scene: bpy.types.Scene):
    old = handler_cls.ctx.pop("old_compositor_device", None)
    if old is not None:
        set_compositor_device(scene.render, old)


# Encodes the scene view transform for the asset's color-space switch node.
_VIEW_TRANSFORM_VALUES = {
    "AgX": 0.0,
    "Standard": 0.1,
    "Filmic": 0.2,
    "Khronos PBR Neutral": 0.3,
}


def _custom_vt_socket(scene: bpy.types.Scene) -> bpy.types.NodeSocket | None:
    tree = get_comp_node_tree(scene)
    if not tree:
        return None
    node = tree.nodes.get(VTC_NAME)
    if not node or not node.inputs:
        return None
    return node.inputs.get("Space") or node.inputs[0]


def update_custom_vt(scene: bpy.types.Scene | None = None) -> None:
    """Mirror the scene view transform into the asset's color-space socket."""
    scene = scene or bpy.context.scene
    space = _custom_vt_socket(scene)
    if space is None:
        return
    try:
        current = float(space.default_value)
        target = _VIEW_TRANSFORM_VALUES.get(scene.view_settings.view_transform, 0.0)
        if abs(target - current) < 0.00001:
            return
        space.default_value = target
    except (AttributeError, TypeError, ValueError):
        pass
