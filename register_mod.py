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
    from .coloring import catalog

    # Module state survives disable/enable; drop stale icon_id caches.
    catalog.invalidate()
    for mod in module_list:
        mod.register()


def unregister():
    from .coloring import catalog
    from .utils.icon import Icon

    try:
        for mod in reversed(module_list):
            mod.unregister()
    finally:
        # Preview collections are destroyed; drop enum caches that store icon_id.
        catalog.invalidate()
        Icon.cleanup()
        logger.close()
