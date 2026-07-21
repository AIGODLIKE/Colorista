"""Load compositor assets (.blend) and presets (.json)."""

from __future__ import annotations

from pathlib import Path

import bpy

from ...src.translate import _T
from ...utils.logger import logger
from ...utils.node import get_comp_node_tree, scene_uses_compositor
from ...utils.paths import get_default_preset_path
from ..session import preset_key, session
from .handlers import (
    ColoristaDepsgraphMonitor,
    sync_nested_driver_values,
    update_custom_vt,
    update_node_group,
)
from .transfer import (
    extract_root_input_bindings,
    reload_drivers,
    remove_invalid_drivers,
    reset_driver_with_scene_ref,
    store_driver_bindings,
    transfer_compositor,
)
from .viewport import set_viewport_shading


def _report(reporter, type_set, message: str) -> None:
    if reporter is not None:
        reporter(type_set, message)
        return
    if "INFO" in type_set:
        logger.info("%s", message)
    else:
        logger.error("%s", message)


def _load_compositor_scene(path: str):
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
    data_path = Path(preset)
    if not data_path.exists():
        return None
    try:
        return _load_compositor_scene(data_path.as_posix())
    except Exception:
        logger.exception("Failed to load compositor scene from %s", data_path)
        return None


def _finish_load(sce: bpy.types.Scene, label: str) -> bool:
    logger.info(_T("Loaded compositor: {}").format(label))
    update_node_group(sce)
    update_custom_vt(sce)
    ColoristaDepsgraphMonitor.refresh(sce)
    return True


def remove_orphan_node_groups(groups: set) -> None:
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


def _remove_loaded_scenes(scenes: set[bpy.types.Scene]) -> None:
    """Remove temporary scenes appended from a compositor asset.

    The tree must be detached first: removing a scene that still references
    the (now shared) tree triggers a Blender 5.1/5.2 ID-user bug.
    """
    for scene in scenes:
        scene.compositing_node_group = None
        bpy.data.scenes.remove(scene)


def load_asset(
    blend_path: Path,
    context: bpy.types.Context,
    *,
    use_asset_color_space: bool = False,
) -> bool:
    """Load .blend topology into the current scene compositor."""
    sce = context.scene
    set_viewport_shading("ALWAYS", context)
    # Groups from the previous load stay in place until the new tree replaces
    # them (removing them up front hits the 5.1/5.2 ID-user bug); they are
    # cleaned up as orphans at the end of this load.
    previous_groups = set(session.loaded_node_groups)
    session.loaded_node_groups.clear()
    old_nts = set(bpy.data.node_groups)
    load_sce = _load_compositor_sce(blend_path, context)
    if not load_sce:
        return False
    new_nts = set(bpy.data.node_groups) - old_nts
    transfer_compositor(
        load_sce,
        context,
        use_asset_color_space=use_asset_color_space,
    )
    current_tree = get_comp_node_tree(sce)
    if current_tree is None or current_tree not in new_nts:
        # Asset had no usable compositor tree: roll the append back.
        logger.error("No compositor tree found in asset: %s", blend_path)
        _remove_loaded_scenes(load_sce)
        remove_orphan_node_groups(new_nts)
        session.loaded_node_groups.clear()
        session.loaded_node_groups.update(previous_groups)
        return False
    root_node_names = {node.name for node in current_tree.nodes}
    bindings = extract_root_input_bindings(new_nts, root_node_names)
    # Persist so save/reopen and undo can rebuild the runtime bindings; the
    # monitor caches them from this property in refresh().
    store_driver_bindings(current_tree, bindings)
    sync_nested_driver_values(sce, bindings)
    for nt in new_nts:
        reset_driver_with_scene_ref(nt.animation_data, load_sce)
    _remove_loaded_scenes(load_sce)
    for nt in list(new_nts):
        try:
            reload_drivers(nt.animation_data)
        except ReferenceError:
            continue
    remove_invalid_drivers(new_nts, sce)
    remove_orphan_node_groups(previous_groups)
    session.set_loaded_asset(blend_path)
    return True


def apply_preset(
    preset_path: Path,
    context: bpy.types.Context,
    *,
    reporter=None,
    use_asset_color_space: bool = False,
    sync_asset_enum=None,
) -> bool:
    """Apply a .json preset (loads asset topology if needed)."""
    from ..preset.io import apply_scene_preset, read_preset_json, resolve_asset_path

    sce = context.scene
    try:
        data = read_preset_json(preset_path)
    except Exception:
        logger.exception("Failed to read preset JSON: %s", preset_path)
        _report(reporter, {"ERROR"}, _T("Failed to load compositor from {}").format(preset_path))
        return False
    asset_path = resolve_asset_path(data.get("asset", ""))
    if asset_path is None or not asset_path.exists():
        _report(reporter, {"ERROR"}, _T("Asset not found: {}").format(data.get("asset", "")))
        return False

    same_asset = (
        session.last_loaded_asset == preset_key(asset_path)
        and scene_uses_compositor(sce)
        and get_comp_node_tree(sce) is not None
    )
    if not same_asset:
        if not load_asset(
            asset_path, context, use_asset_color_space=use_asset_color_space
        ):
            _report(reporter, {"ERROR"}, _T("Failed to load compositor from {}").format(asset_path))
            return False
    else:
        set_viewport_shading("ALWAYS", context)

    try:
        apply_scene_preset(
            sce, data, use_asset_color_space=use_asset_color_space
        )
    except Exception:
        logger.exception("Failed to apply preset JSON: %s", preset_path)
        _report(reporter, {"ERROR"}, _T("Failed to load compositor from {}").format(preset_path))
        return False

    if sync_asset_enum is not None:
        try:
            sync_asset_enum(context, asset_path)
        except Exception:
            pass

    return _finish_load(sce, preset_path.as_posix())


def load(
    context: bpy.types.Context,
    *,
    path: str | Path | None = None,
    preset: str | Path | None = None,
    use_default: bool = False,
    force: bool = False,
    reporter=None,
    use_asset_color_space: bool = False,
    sync_asset_enum=None,
) -> bool:
    """Load a compositor asset or preset into the current scene.

    History is orchestrated by ``coloring.api``, not this module.
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

    if preset_path.suffix.lower() == ".json":
        ok = apply_preset(
            preset_path,
            context,
            reporter=reporter,
            use_asset_color_space=use_asset_color_space,
            sync_asset_enum=sync_asset_enum,
        )
    else:
        if not load_asset(
            preset_path, context, use_asset_color_space=use_asset_color_space
        ):
            _report(reporter, {"ERROR"}, _T("Failed to load compositor from {}").format(preset_path))
            return False
        ok = _finish_load(sce, preset_path.as_posix())

    if not ok:
        return False
    session.set_loaded_preset(preset_path)
    return True
