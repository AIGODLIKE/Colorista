"""Public facade for Colorista coloring."""

from __future__ import annotations

from pathlib import Path

import bpy

from .compositor import load as load_mod
from .constants import PRESET_NONE_ID
from .session import preset_key, session
from ..src.translate import _T
from ..utils.node import scene_uses_compositor
from ..utils.timer import Timer
from . import catalog, history, runtime
from .config import get_config

_pending_kwargs: dict | None = None
_import_scheduled = False


def schedule_load(**kwargs) -> None:
    """Defer load out of RNA property updates (avoids nested ops / write crashes)."""
    global _pending_kwargs, _import_scheduled
    _pending_kwargs = kwargs
    if _import_scheduled:
        return
    _import_scheduled = True
    Timer.put(_flush_scheduled_load)


def _flush_scheduled_load() -> None:
    global _pending_kwargs, _import_scheduled
    _import_scheduled = False
    kwargs = _pending_kwargs
    _pending_kwargs = None
    if kwargs is None:
        return
    try:
        load(bpy.context, **kwargs)
    except Exception:
        from ..utils.logger import logger

        logger.exception("Deferred compositor import failed")


def _sync_asset_enum(context: bpy.types.Context, asset_path: Path) -> None:
    prop = context.scene.colorista_prop
    asset_id = asset_path.as_posix()
    items = catalog.list_assets(prop.pre_dir, context)
    valid = {item[0] for item in items}
    if asset_id in valid and prop.asset != asset_id:
        with session.suppress_asset_updates():
            prop.asset = asset_id


def _resolve_history_asset(context: bpy.types.Context) -> Path | str | None:
    sce = context.scene
    asset = None
    try:
        asset = sce.colorista_prop.get_asset_path(context)
    except AttributeError:
        pass
    if not asset and session.last_loaded_asset:
        asset = session.last_loaded_asset
    return asset


def _capture_history(context: bpy.types.Context) -> bool:
    sce = context.scene
    if not scene_uses_compositor(sce):
        return False
    asset = _resolve_history_asset(context)
    if not asset:
        return False
    return history.begin_capture(context, sce, asset)


def _refresh_baseline(context: bpy.types.Context) -> None:
    sce = context.scene
    asset = _resolve_history_asset(context)
    history.set_baseline_from_scene(sce, asset)


def enable(context: bpy.types.Context) -> bool:
    """Enable coloring: load default preset and activate handlers."""
    if not load(context, use_default=True, cache=False):
        return False
    runtime.activate()
    return True


def disable(context: bpy.types.Context | None = None) -> None:
    runtime.deactivate(context, clear_tree=True)


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
    cfg = get_config()
    captured = False
    if cache and cfg.cache_current_compositor:
        captured = _capture_history(context)
    ok = load_mod.load(
        context,
        path=path,
        preset=preset,
        use_default=use_default,
        force=force,
        reporter=reporter,
        use_asset_color_space=cfg.use_asset_color_space_pref,
        sync_asset_enum=_sync_asset_enum,
    )
    if ok:
        if captured:
            history.commit_capture(context)
        else:
            history.discard_capture()
        _refresh_baseline(context)
    else:
        history.discard_capture()
    return ok


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
    if not items:
        return False, _T("No preset available")
    if len(items) == 1:
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
