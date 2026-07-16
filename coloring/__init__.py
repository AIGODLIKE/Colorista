"""Coloring feature package: load/transfer, catalog, history, runtime."""

from . import runtime


def register():
    runtime.register()


def unregister():
    runtime.unregister()
