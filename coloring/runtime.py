"""Activate event-driven synchronization only while coloring is enabled."""

import bpy

from .session import session

_active = False
_load_post_registered = False
_bootstrap_timer_registered = False
_scene_msgbus_owner = object()
_scene_msgbus_registered = False
_changing_scene = False


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
            _suspend_runtime()
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
    # References into the previous file (node groups, binding target trees,
    # last-loaded keys) are all invalid now; drop them before touching data.
    session.clear_loaded_preset()
    session.loaded_node_groups.clear()
    from . import history

    history.clear_baseline()
    try:
        _suspend_runtime()
        _register_scene_msgbus()
        ensure_coloring_content(bpy.context)
        _refresh_history_ui(bpy.context)
    except Exception:
        from ..utils.logger import logger

        logger.exception("Colorista file-load restore failed")


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


def _on_active_scene_change() -> None:
    """Activate or suspend runtime state when a window switches scenes."""
    global _changing_scene
    if _changing_scene:
        return
    _changing_scene = True
    try:
        scene = bpy.context.scene
        props = getattr(scene, "colorista_prop", None)
        _suspend_runtime()
        if props is not None and props.enable_coloring:
            activate()
    except (AttributeError, ReferenceError):
        _suspend_runtime()
    finally:
        _changing_scene = False


def _register_scene_msgbus() -> None:
    global _scene_msgbus_registered
    bpy.msgbus.clear_by_owner(_scene_msgbus_owner)
    try:
        bpy.msgbus.subscribe_rna(
            key=(bpy.types.Window, "scene"),
            owner=_scene_msgbus_owner,
            args=(),
            notify=_on_active_scene_change,
        )
    except (AttributeError, RuntimeError, TypeError, ValueError):
        _scene_msgbus_registered = False
        return
    _scene_msgbus_registered = True


def _unregister_scene_msgbus() -> None:
    global _scene_msgbus_registered
    bpy.msgbus.clear_by_owner(_scene_msgbus_owner)
    _scene_msgbus_registered = False


def bootstrap_coloring_state():
    try:
        # Preference values are only reliable after registration completes;
        # restore the opt-in logging state here instead of in register().
        from ..utils.logger import configure_logger
        from .config import get_config

        configure_logger(get_config().enable_logging)
        ensure_coloring_content(bpy.context)
        _refresh_history_ui(bpy.context)
    except Exception:
        pass


def _deferred_bootstrap():
    global _bootstrap_timer_registered
    _bootstrap_timer_registered = False
    bootstrap_coloring_state()
    return None


def activate() -> None:
    global _active

    from .compositor.handlers import (
        ColoristaMsgBusMonitor,
        RenderHandler,
        configure_handlers,
        restore_render_device,
        switch_to_cpu_device,
        update_custom_vt,
        update_node_group,
    )
    from .config import get_config
    from .compositor.transfer import materialize_stored_bindings
    from ..utils.node import get_comp_node_tree

    configure_handlers(
        main_node_group_name=lambda: get_config().main_node_group_name,
        enable_logging=lambda: get_config().enable_logging,
        force_use_cpu=lambda: get_config().force_use_cpu_render_image,
    )

    materialize_stored_bindings(get_comp_node_tree(bpy.context.scene))
    update_node_group(bpy.context.scene)
    update_custom_vt(bpy.context.scene)
    ColoristaMsgBusMonitor.register(bpy.context.scene)
    # Stash/force on render_init (once per job); restore on either outcome.
    RenderHandler.add(switch_to_cpu_device, "init")
    RenderHandler.add(restore_render_device, "complete")
    RenderHandler.add(restore_render_device, "cancel")
    RenderHandler.register()
    _active = True


def _suspend_runtime() -> None:
    """Remove runtime callbacks without clearing scene data or session state."""
    global _active
    from .compositor.handlers import ColoristaMsgBusMonitor, RenderHandler

    ColoristaMsgBusMonitor.unregister()
    RenderHandler.unregister()
    _active = False


def deactivate(context: bpy.types.Context | None = None, *, clear_tree: bool = False) -> None:
    """Tear down handlers. Clear compositor only when *clear_tree* is True."""
    global _active
    from .compositor.viewport import clear_compositor, set_viewport_shading

    _suspend_runtime()

    if clear_tree:
        from .compositor.load import remove_orphan_node_groups
        from ..utils.logger import logger

        try:
            scene = (context or bpy.context).scene
            clear_compositor(scene)
            set_viewport_shading("DISABLED", context)
        except Exception:
            pass
        try:
            remove_orphan_node_groups(session.loaded_node_groups)
        except Exception:
            logger.exception("Failed to purge Colorista node groups")
        session.loaded_node_groups.clear()

    from ..utils.timer import Timer

    Timer.unreg()
    session.clear_loaded_preset()
    from . import history

    history.clear_baseline()
    history.discard_capture()


def register():
    global _bootstrap_timer_registered
    # load_post must stay registered while the extension is enabled: coloring
    # state is stored per scene, so opening a file with coloring on has to
    # rebuild the RNA subscriptions and render callbacks.
    _register_load_post()
    _register_scene_msgbus()
    if not _bootstrap_timer_registered:
        bpy.app.timers.register(_deferred_bootstrap, first_interval=0)
        _bootstrap_timer_registered = True


def unregister():
    global _bootstrap_timer_registered
    _unregister_scene_msgbus()
    try:
        deactivate(bpy.context, clear_tree=False)
    except Exception:
        deactivate(None, clear_tree=False)
    _unregister_load_post()
    if _bootstrap_timer_registered and bpy.app.timers.is_registered(_deferred_bootstrap):
        bpy.app.timers.unregister(_deferred_bootstrap)
    _bootstrap_timer_registered = False
