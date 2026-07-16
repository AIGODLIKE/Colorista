"""Shared utilities: paths, timers, icons, logging (no preferences / UI imports)."""

from . import timer, watcher

modules = (
    "timer",
    "watcher",
)


def register():
    timer.register()
    watcher.register()


def unregister():
    watcher.unregister()
    timer.unregister()
