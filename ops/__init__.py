"""Operators."""

import bpy

modules = (
    "operators",
    "history",
)

_reg, _unreg = bpy.utils.register_submodule_factory(__package__, modules)


def register():
    _reg()


def unregister():
    _unreg()
