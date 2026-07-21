"""Depsgraph / render handlers and color-space sync."""

from __future__ import annotations

import re
from typing import Callable

import bpy

from ...utils.logger import logger
from ...utils.node import get_comp_node_tree

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


def sync_nested_driver_values(scene: bpy.types.Scene, bindings: list[tuple] | None = None) -> None:
    """Apply former driver formulas without cross-tree dependencies."""
    from .transfer import DRIVER_FORMULAS

    if bindings is None:
        bindings = ColoristaDepsgraphMonitor.bindings
    tree = get_comp_node_tree(scene)
    if tree is None:
        return
    for binding in list(bindings):
        target_tree, data_path, array_index, node_name, index, expression = binding
        source_node = tree.nodes.get(node_name)
        if source_node is None or index >= len(source_node.inputs):
            continue
        source = getattr(source_node.inputs[index], "default_value", None)
        if not isinstance(source, (bool, int, float)):
            continue
        formula = DRIVER_FORMULAS.get(expression)
        if formula is None:
            continue
        value = formula(float(source))
        try:
            owner_path, attribute = data_path.rsplit(".", 1)
            owner = target_tree.path_resolve(owner_path)
            current = getattr(owner, attribute)
            if hasattr(current, "__len__"):
                # Vector/color property: the driver targeted one component.
                if current[array_index] != value:
                    current[array_index] = value
            else:
                if isinstance(current, bool):
                    value = bool(round(value))
                elif isinstance(current, int):
                    value = int(round(value))
                if current != value:
                    setattr(owner, attribute, value)
        except (AttributeError, IndexError, ReferenceError, TypeError, ValueError):
            continue


class ColoristaDepsgraphMonitor:
    """React only when a node tree owned by the active Colorista setup changes."""

    # Bindings are cached from the persisted custom property (see transfer
    # store/load_driver_bindings); refresh() is the only writer.
    bindings: list[tuple] = []
    _tree_pointers: set[int] = set()
    _registered = False
    _updating = False

    @classmethod
    def refresh(cls, scene: bpy.types.Scene) -> None:
        """Rebuild the tree-pointer filter and restore persisted bindings."""
        from .transfer import load_driver_bindings

        cls._tree_pointers.clear()
        tree = get_comp_node_tree(scene)
        if tree is None:
            cls.bindings = []
            return
        cls._tree_pointers.add(tree.as_pointer())
        main_node = tree.nodes.get(_main_node_group_name())
        if main_node is not None and main_node.node_tree is not None:
            cls._tree_pointers.add(main_node.node_tree.as_pointer())
        cls.bindings = load_driver_bindings(tree)

    @classmethod
    @bpy.app.handlers.persistent
    def update(cls, scene, depsgraph) -> None:
        if cls._updating:
            return
        props = getattr(scene, "colorista_prop", None)
        if props is None or not props.enable_coloring:
            return
        tree = get_comp_node_tree(scene)
        if tree is None:
            return
        if tree.as_pointer() not in cls._tree_pointers:
            # Undo/redo, scene switching, or a reload replaced the datablocks:
            # cached pointers (and binding tree references) are stale.
            cls.refresh(scene)
        for update in depsgraph.updates:
            uid = update.id
            if uid is None:
                continue
            # Evaluated IDs expose their datablock via .original; original IDs
            # return None there, so fall back to the ID itself.
            base = uid.original or uid
            if base.as_pointer() in cls._tree_pointers:
                break
        else:
            return
        cls._updating = True
        try:
            sync_nested_driver_values(scene)
            update_node_group(scene)
            update_custom_vt(scene)
        except Exception:
            logger.exception("Colorista node synchronization failed")
        finally:
            cls._updating = False

    @classmethod
    def register(cls) -> None:
        if cls._registered:
            return
        bpy.app.handlers.depsgraph_update_post.append(cls.update)
        cls._registered = True

    @classmethod
    def unregister(cls) -> None:
        if cls._registered:
            try:
                bpy.app.handlers.depsgraph_update_post.remove(cls.update)
            except ValueError:
                pass
        cls._registered = False
        cls._tree_pointers.clear()
        cls.bindings = []
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
        if cls._registered:
            return
        bpy.app.handlers.render_init.append(cls.update_init)
        bpy.app.handlers.render_pre.append(cls.update_pre)
        bpy.app.handlers.render_post.append(cls.update_post)
        bpy.app.handlers.render_complete.append(cls.update_complete)
        bpy.app.handlers.render_cancel.append(cls.update_cancel)
        cls._registered = True

    @classmethod
    def unregister(cls):
        if cls._registered:
            for handler_list, fn in (
                (bpy.app.handlers.render_init, cls.update_init),
                (bpy.app.handlers.render_pre, cls.update_pre),
                (bpy.app.handlers.render_post, cls.update_post),
                (bpy.app.handlers.render_complete, cls.update_complete),
                (bpy.app.handlers.render_cancel, cls.update_cancel),
            ):
                try:
                    handler_list.remove(fn)
                except ValueError:
                    pass
            cls._registered = False
        for stage_handlers in cls.handlers.values():
            stage_handlers.clear()
        cls.ctx.clear()


def switch_to_cpu_device(handler_cls: type[RenderHandler], scene: bpy.types.Scene):
    """Stash the device once per render job (render_init), not per frame.

    Stashing on render_pre would overwrite the stash with the already-forced
    "CPU" value from the second animation frame on, losing the user setting.
    """
    if _force_cpu_fn is None or not _force_cpu_fn():
        return
    if "old_compositor_device" not in handler_cls.ctx:
        handler_cls.ctx["old_compositor_device"] = scene.render.compositor_device
    scene.render.compositor_device = "CPU"


def restore_render_device(handler_cls: type[RenderHandler], scene: bpy.types.Scene):
    old = handler_cls.ctx.pop("old_compositor_device", None)
    if old is not None:
        scene.render.compositor_device = old


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
