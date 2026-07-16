"""Load compositor assets (.blend) and presets (.json)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import bpy

from ..i18n import _T
from ..preference import get_pref
from ...utils.compat import IS_BL42_TO_43, IS_BL5
from ...utils.logger import logger
from ...utils.node import ensure_comp_node_tree, get_comp_node_tree, scene_uses_compositor
from ...utils.paths import get_default_preset_path, get_user_cache_dir
from ...utils.timer import Timer
from . import catalog
from .handlers import update_custom_vt, update_node_group
from .preset_io import (
    apply_scene_preset,
    read_preset_json,
    resolve_asset_path,
    save_compositor_values_json,
)
from .session import preset_key, session
from .transfer import reload_drivers, reset_driver_with_scene_ref, transfer_compositor
from .viewport import set_viewport_shading

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
        logger.exception("Deferred compositor import failed")


def _report(reporter, type_set, message: str) -> None:
    if reporter is not None:
        reporter(type_set, message)
        return
    if "INFO" in type_set:
        logger.info("%s", message)
    else:
        logger.error("%s", message)


def _rsc_used(rsc) -> bool:
    try:
        return (rsc.users >= 1 and not rsc.use_fake_user) or rsc.users >= 2
    except ReferenceError:
        return False


def _current_asset_path(context: bpy.types.Context) -> Path | None:
    try:
        asset = context.scene.colorista_prop.get_asset_path(context)
    except AttributeError:
        return None
    if not asset:
        return None
    path = Path(asset)
    return path if path.exists() else None


def _load_compositor_scene(path: str):
    for group in list(session.loaded_node_groups):
        if _rsc_used(group):
            continue
        session.loaded_node_groups.discard(group)
        try:
            bpy.data.node_groups.remove(group)
        except ReferenceError:
            pass

    old_groups = set(bpy.data.node_groups)
    old_scenes = set(bpy.data.scenes)
    load_sce_name = "AC-Coloring"
    with bpy.data.libraries.load(path, link=False) as (df, dt):
        if load_sce_name not in df.scenes:
            load_sce_name = ""
        if not load_sce_name and df.scenes:
            load_sce_name = df.scenes[0]
        if not load_sce_name:
            return
        dt.scenes.append(load_sce_name)
    new_scenes = set(bpy.data.scenes) - old_scenes
    new_groups = set(bpy.data.node_groups) - old_groups
    for ngroup in new_groups:
        session.loaded_node_groups.add(ngroup)
    if not new_scenes:
        return
    return new_scenes


def _load_compositor_sce(preset, context: bpy.types.Context):
    ensure_comp_node_tree(context.scene)
    data_path = Path(preset)
    if not data_path.exists():
        return None
    try:
        return _load_compositor_scene(data_path.as_posix())
    except Exception:
        logger.exception("Failed to load compositor scene from %s", data_path)
        return None


def _cache_history_json(context: bpy.types.Context, sce: bpy.types.Scene, *, no_cache: bool) -> None:
    pref = get_pref()
    if not pref or not pref.cache_current_compositor or no_cache:
        return
    if not scene_uses_compositor(sce):
        return
    asset_path = _current_asset_path(context)
    if asset_path is None and session.last_loaded_asset:
        asset_path = Path(session.last_loaded_asset)
    if asset_path is None:
        return
    from .history import append_history_item

    name = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    path = get_user_cache_dir().joinpath(f"{name}.json")
    try:
        save_compositor_values_json(path, sce, asset_path)
    except Exception as e:
        logger.error(e)
        return
    append_history_item(context, path)


def _finish_load(sce: bpy.types.Scene, label: str) -> bool:
    logger.info(_T("Load Compositor: {}").format(label))
    update_node_group(sce)
    update_custom_vt()
    return True


def _collect_nested_node_groups(tree, out: set) -> None:
    if tree is None:
        return
    for node in tree.nodes:
        if node.type == "GROUP" and node.node_tree:
            nt = node.node_tree
            if nt not in out:
                out.add(nt)
                _collect_nested_node_groups(nt, out)


def _remove_orphan_node_groups(groups: set) -> None:
    pending = set(groups)
    for _ in range(max(1, len(pending))):
        if not pending:
            break
        removed = False
        for ng in list(pending):
            try:
                if ng.users == 0:
                    bpy.data.node_groups.remove(ng)
                    pending.discard(ng)
                    removed = True
            except ReferenceError:
                pending.discard(ng)
        if not removed:
            break


def _purge_compositor_before_reload(context: bpy.types.Context) -> None:
    """Detach and remove prior Colorista compositor data before library append.

    Without this, append creates ``Name.001`` / ``Name.002`` duplicates because
    the previous asset's node groups are still in ``bpy.data``.
    """
    sce = context.scene
    to_remove = set(session.loaded_node_groups)

    if IS_BL5:
        root = sce.compositing_node_group
        if root is not None:
            to_remove.add(root)
            _collect_nested_node_groups(root, to_remove)
        sce.compositing_node_group = None
    else:
        tree = get_comp_node_tree(sce)
        if tree is not None:
            _collect_nested_node_groups(tree, to_remove)
            tree.nodes.clear()

    session.loaded_node_groups.clear()
    _remove_orphan_node_groups(to_remove)


def load_asset(blend_path: Path, context: bpy.types.Context) -> bool:
    """Load .blend topology into the current scene compositor."""
    sce = context.scene
    if IS_BL42_TO_43:
        sce.render.compositor_device = "GPU"
    set_viewport_shading("ALWAYS", context)
    _purge_compositor_before_reload(context)
    ensure_comp_node_tree(sce)
    old_nts = set(bpy.data.node_groups)
    load_sce = _load_compositor_sce(blend_path, context)
    if not load_sce:
        return False
    new_nts = set(bpy.data.node_groups) - old_nts
    transfer_compositor(load_sce, context)
    for nt in new_nts:
        reset_driver_with_scene_ref(nt.animation_data, load_sce)
    for ls in load_sce:
        bpy.data.scenes.remove(ls)
    current_tree = get_comp_node_tree(sce)
    if current_tree is not None:
        new_nts.add(current_tree)
    for nt in list(new_nts):
        try:
            if nt is not None:
                reload_drivers(nt.animation_data)
        except ReferenceError:
            continue
    session.set_loaded_asset(blend_path)
    return True


def apply_preset(preset_path: Path, context: bpy.types.Context, *, reporter=None) -> bool:
    """Apply a .json preset (loads asset topology if needed)."""
    sce = context.scene
    try:
        data = read_preset_json(preset_path)
    except Exception:
        logger.exception("Failed to read preset JSON: %s", preset_path)
        _report(reporter, {"ERROR"}, _T("Failed to load compositor from {}").format(preset_path))
        return False
    asset_path = resolve_asset_path(data.get("asset", ""))
    if asset_path is None or not asset_path.exists():
        _report(reporter, {"ERROR"}, _T("Preset not found: {}").format(data.get("asset", "")))
        return False

    same_asset = (
        session.last_loaded_asset == preset_key(asset_path)
        and scene_uses_compositor(sce)
        and get_comp_node_tree(sce) is not None
    )
    if not same_asset:
        if not load_asset(asset_path, context):
            _report(reporter, {"ERROR"}, _T("Failed to load compositor from {}").format(asset_path))
            return False
    else:
        set_viewport_shading("ALWAYS", context)

    try:
        apply_scene_preset(sce, data)
    except Exception:
        logger.exception("Failed to apply preset JSON: %s", preset_path)
        _report(reporter, {"ERROR"}, _T("Failed to load compositor from {}").format(preset_path))
        return False

    try:
        prop = sce.colorista_prop
        asset_id = asset_path.as_posix()
        items = catalog.list_assets(prop.pre_dir, context)
        valid = {item[0] for item in items}
        if asset_id in valid and prop.asset != asset_id:
            with session.suppress_asset_updates():
                prop.asset = asset_id
    except Exception:
        pass

    return _finish_load(sce, preset_path.as_posix())


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
    """Load a compositor asset or preset into the current scene.

    ``preset`` is an alias of ``path`` for operator compatibility.
    """
    target = path if path is not None else preset

    if use_default:
        preset_path = get_default_preset_path()
        if preset_path is None:
            _report(reporter, {"ERROR"}, _T("No default preset found"))
            return False
    elif target:
        preset_path = Path(target)
    else:
        asset = context.scene.colorista_prop.get_asset_path(context)
        preset_path = Path(asset) if asset else None

    if preset_path is None:
        _report(reporter, {"ERROR"}, _T("No default preset found"))
        return False
    if not preset_path.exists():
        _report(reporter, {"ERROR"}, _T("Preset not found: {}").format(preset_path))
        return False

    key = preset_key(preset_path)
    if not force and not use_default and session.last_loaded_preset == key:
        _report(reporter, {"INFO"}, _T("Already on this preset"))
        return True

    sce = context.scene
    _cache_history_json(context, sce, no_cache=not cache)

    if preset_path.suffix.lower() == ".json":
        ok = apply_preset(preset_path, context, reporter=reporter)
    else:
        if not load_asset(preset_path, context):
            _report(reporter, {"ERROR"}, _T("Failed to load compositor from {}").format(preset_path))
            return False
        ok = _finish_load(sce, preset_path.as_posix())

    if not ok:
        return False
    session.set_loaded_preset(preset_path)
    return True
