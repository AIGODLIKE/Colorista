"""Activate/defer handlers and timers until coloring is enabled."""

_active = False


def is_active() -> bool:
    return _active


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
        update_custom_vt,
        update_node_group,
    )
    from .timer import UpdateTimer1s, update_device

    DepsgraphPostHandler.add(update_node_group)
    DepsgraphPostHandler.add(update_custom_vt)
    DepsgraphPostHandler.register()
    RenderHandler.add(switch_to_cpu_device, "pre")
    RenderHandler.add(restore_render_device, "complete")
    RenderHandler.register()
    UpdateTimer1s.add(update_device)
    UpdateTimer1s.register()


def deactivate() -> None:
    global _active
    from .utils import set_viewport_shading

    if _active:
        from .handler import DepsgraphPostHandler, RenderHandler
        from .timer import UpdateTimer1s

        UpdateTimer1s.unregister()
        DepsgraphPostHandler.unregister()
        RenderHandler.unregister()
        _active = False

    set_viewport_shading("DISABLED")

    from ...utils.timer import Timer
    from ...utils.watcher import FSWatcher

    FSWatcher.stop()
    Timer.unreg()
