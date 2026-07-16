"""Public facade for Colorista coloring."""

from __future__ import annotations

from pathlib import Path

import bpy

from ..i18n import _T
from . import catalog
from .constants import PRESET_NONE_ID
from .load import schedule_load  # noqa: F401 — re-export for properties
from .session import preset_key


def enable(context: bpy.types.Context) -> bool:
    """Enable coloring: load default preset and activate handlers."""
    from .load import load as _load
    from .runtime import activate

    if not _load(context, use_default=True):
        return False
    activate()
    return True


def disable(context: bpy.types.Context | None = None) -> None:
    from .runtime import deactivate

    deactivate(context, clear_tree=True)


def load(
    context: bpy.types.Context,
    *,
    path: str | Path | None = None,
    preset: str | Path | None = None,
    use_default: bool = False,
    cache: bool = True,
    force: bool = False,
    reporter=None,
) -> bool:
    from .load import load as _load

    return _load(
        context,
        path=path,
        preset=preset,
        use_default=use_default,
        cache=cache,
        force=force,
        reporter=reporter,
    )


def switch_asset(context: bpy.types.Context, delta: int) -> bool:
    prop = context.scene.colorista_prop
    items = catalog.list_assets(prop.pre_dir, context)
    if not items:
        return False
    pos = catalog.enum_item_index(items, prop.asset)
    prop.asset = items[(pos + delta) % len(items)][0]
    return True


def switch_preset(context: bpy.types.Context, delta: int) -> tuple[bool, str]:
    """Return (ok, message). Message is set when cancelled."""
    prop = context.scene.colorista_prop
    items = [
        item
        for item in catalog.list_presets(prop.get_asset_path(context), context)
        if item[0] != PRESET_NONE_ID
    ]
    if len(items) <= 1:
        return False, _T("Only one preset available")

    pos = catalog.enum_item_index(items, prop.preset)
    new_preset = items[(pos + delta) % len(items)][0]
    if preset_key(new_preset) == preset_key(prop.preset):
        return False, _T("Only one preset available")

    prop.preset = new_preset
    return True, ""


def reset_to_defaults(context: bpy.types.Context, *, reporter=None) -> bool:
    """Reload the current asset .blend so node values return to defaults."""
    prop = context.scene.colorista_prop
    asset = prop.get_asset_path(context)
    if not asset:
        return False
    return load(context, path=asset, force=True, cache=True, reporter=reporter)
