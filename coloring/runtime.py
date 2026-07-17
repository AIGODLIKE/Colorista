"""Activate/defer handlers until coloring is enabled."""

import bpy

from .session import session

_active = False
_load_post_registered = False


def is_active() -> bool:
    return _active


def _has_ui_nodes(scene: bpy.types.Scene) -> bool:
    from .compositor.ui_nodes import iter_ui_coloring_nodes
    from ..utils.node import get_comp_node_tree, scene_uses_compositor

    if not scene_uses_compositor(scene):
        return False
    tree = get_comp_node_tree(scene)
    if tree is None:
        return False
    return any(True for _node, _sockets in iter_ui_coloring_nodes(tree))


def ensure_coloring_content(context: bpy.types.Context | None = None) -> None:
    """If coloring is on but the compositor UI is empty, reload asset/default."""
    context = context or bpy.context
    try:
        scene = context.scene
        if not scene.colorista_prop.enable_coloring:
            return
    except Exception:
        return

    activate()
    if _has_ui_nodes(scene):
        from . import history

        asset = None
        try:
            asset = scene.colorista_prop.get_asset_path(context)
        except Exception:
            pass
        if not asset:
            asset = session.last_loaded_asset
        history.set_baseline_from_scene(scene, asset)
        return

    from ..utils.logger import logger
    from . import api as coloring

    try:
        asset = scene.colorista_prop.get_asset_path(context)
        if asset:
            coloring.load(context, path=asset, force=True, cache=False)
        else:
            coloring.load(context, use_default=True, force=True, cache=False)
    except Exception:
        logger.exception("Failed to restore coloring compositor")


def _refresh_history_ui(context: bpy.types.Context | None = None) -> None:
    from . import history

    history.refresh_from_disk(context)


@bpy.app.handlers.persistent
def _on_file_load(_scene):
    session.loaded_node_groups.clear()
    from . import history

    history.clear_baseline()
    try:
        ensure_coloring_content(bpy.context)
        _refresh_history_ui(bpy.context)
    except AttributeError:
        pass


def _register_load_post():
    global _load_post_registered
    if _load_post_registered:
        return
    bpy.app.handlers.load_post.append(_on_file_load)
    _load_post_registered = True


def _unregister_load_post():
    global _load_post_registered
    if not _load_post_registered:
        return
    try:
        bpy.app.handlers.load_post.remove(_on_file_load)
    except ValueError:
        pass
    _load_post_registered = False


def bootstrap_coloring_state():
    try:
        ensure_coloring_content(bpy.context)
        _refresh_history_ui(bpy.context)
    except Exception:
        pass


def _deferred_bootstrap():
    bootstrap_coloring_state()
    return None


def activate() -> None:
    global _active
    if _active:
        return
    _active = True

    from .compositor.handlers import (
        DepsgraphPostHandler,
        RenderHandler,
        configure_handlers,
        restore_render_device,
        switch_to_cpu_device,
        update_custom_vt,
        update_node_group,
    )
    from ..utils.watcher import FSWatcher
    from .config import get_config

    configure_handlers(
        main_node_group_name=lambda: get_config().main_node_group_name,
        enable_logging=lambda: get_config().enable_logging,
        force_use_cpu=lambda: get_config().force_use_cpu_render_image,
    )

    DepsgraphPostHandler.add(update_node_group)
    DepsgraphPostHandler.add(lambda scene: update_custom_vt())
    DepsgraphPostHandler.register()
    RenderHandler.add(switch_to_cpu_device, "pre")
    RenderHandler.add(restore_render_device, "complete")
    RenderHandler.register()
    FSWatcher.enable()


def deactivate(context: bpy.types.Context | None = None, *, clear_tree: bool = False) -> None:
    """Tear down handlers. Clear compositor only when *clear_tree* is True."""
    global _active
    from .compositor.viewport import clear_compositor, set_viewport_shading

    if _active:
        from .compositor.handlers import DepsgraphPostHandler, RenderHandler
        from ..utils.watcher import FSWatcher

        DepsgraphPostHandler.unregister()
        RenderHandler.unregister()
        FSWatcher.disable()
        _active = False

    if clear_tree:
        try:
            scene = (context or bpy.context).scene
            clear_compositor(scene)
            set_viewport_shading("DISABLED", context)
        except Exception:
            pass

    from ..utils.timer import Timer

    Timer.unreg()
    session.clear_loaded_preset()
    from . import history

    history.clear_baseline()
    history.discard_capture()


def register():
    _register_load_post()
    bpy.app.timers.register(_deferred_bootstrap, first_interval=0)


def unregister():
    try:
        deactivate(bpy.context, clear_tree=False)
    except Exception:
        deactivate(None, clear_tree=False)
    _unregister_load_post()
