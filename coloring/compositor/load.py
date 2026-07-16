"""Load compositor assets (.blend) and presets (.json)."""

from __future__ import annotations

from pathlib import Path

import bpy

from ...src.translate import _T
from ...utils.compat import IS_BL42_TO_43, IS_BL5
from ...utils.logger import logger
from ...utils.node import ensure_comp_node_tree, get_comp_node_tree, scene_uses_compositor
from ...utils.paths import get_default_preset_path
from ..session import preset_key, session
from .handlers import update_custom_vt, update_node_group
from .transfer import reload_drivers, reset_driver_with_scene_ref, transfer_compositor
from .viewport import set_viewport_shading


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
    """Detach and remove prior Colorista compositor data before library append."""
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


def load_asset(
    blend_path: Path,
    context: bpy.types.Context,
    *,
    use_asset_color_space: bool = False,
) -> bool:
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
    transfer_compositor(
        load_sce,
        context,
        use_asset_color_space=use_asset_color_space,
    )
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
        _report(reporter, {"ERROR"}, _T("Preset not found: {}").format(data.get("asset", "")))
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
    cache: bool = True,
    force: bool = False,
    reporter=None,
    use_asset_color_space: bool = False,
    sync_asset_enum=None,
) -> bool:
    """Load a compositor asset or preset into the current scene.

    *cache* is unused here; history is orchestrated by ``coloring.api``.
    """
    del cache  # handled by coloring.api facade
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

