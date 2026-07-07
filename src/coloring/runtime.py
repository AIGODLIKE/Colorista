"""Activate/defer handlers and timers until coloring is enabled."""

import bpy

from .state import loaded_node_groups

_active = False
_load_post_registered = False


def is_active() -> bool:
    return _active


@bpy.app.handlers.persistent
def _on_file_load(scene):
    loaded_node_groups.clear()
    try:
        if not scene.colorista_prop.enable_coloring:
            return
        activate()
        from .cache_history import update_history

        update_history()
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
        scenes = bpy.data.scenes
    except AttributeError:
        return
    for scene in scenes:
        try:
            if scene.colorista_prop.enable_coloring:
                activate()
                return
        except AttributeError:
            pass


def _deferred_bootstrap():
    bootstrap_coloring_state()
    return None


def activate() -> None:
    global _active
    if _active:
        return
    _active = True

    from .handler import (
        DepsgraphPostHandler,
        RenderHandler,
        restore_render_device,
        switch_to_cpu_device,
        update_node_group,
    )
    from .timer import update_custom_vt
    from ...utils.watcher import FSWatcher

    DepsgraphPostHandler.add(update_node_group)
    DepsgraphPostHandler.add(lambda scene: update_custom_vt())
    DepsgraphPostHandler.register()
    RenderHandler.add(switch_to_cpu_device, "pre")
    RenderHandler.add(restore_render_device, "complete")
    RenderHandler.register()
    FSWatcher.enable()


def deactivate(context: bpy.types.Context | None = None) -> None:
    global _active
    from .utils import clear_compositor, set_viewport_shading

    if _active:
        from .handler import DepsgraphPostHandler, RenderHandler
        from ...utils.watcher import FSWatcher

        DepsgraphPostHandler.unregister()
        RenderHandler.unregister()
        FSWatcher.disable()
        _active = False

    try:
        scene = (context or bpy.context).scene
        clear_compositor(scene)
        set_viewport_shading("DISABLED", context)
    except Exception:
        pass

    from ...utils.timer import Timer

    Timer.unreg()


def register():
    _register_load_post()
    bpy.app.timers.register(_deferred_bootstrap, first_interval=0)


def unregister():
    try:
        deactivate(bpy.context)
    except Exception:
        deactivate(None)
    _unregister_load_post()
