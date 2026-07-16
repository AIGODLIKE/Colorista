"""Addon registration (gesture-style entry orchestration)."""

from . import coloring, ops, preferences, props, ui, utils
from .src import translate
from .utils.logger import logger

module_list = (
    utils,
    translate,
    preferences,
    props,
    ops,
    ui,
    coloring,
)


def register():
    for mod in module_list:
        mod.register()


def unregister():
    from .utils.icon import Icon

    try:
        for mod in reversed(module_list):
            mod.unregister()
    finally:
        Icon.cleanup()
        logger.close()
