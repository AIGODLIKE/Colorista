"""Transfer compositor node trees between scenes."""

from __future__ import annotations

import json
import re
import uuid

import bpy

from ...utils.node import get_comp_node_tree, remap_scene_compositor_driver_paths

_MAIN_INPUT_PATH = re.compile(
    r'(?:node_tree|compositing_node_group)\.nodes\["([^"]+)"\]'
    r'\.inputs\[(\d+)\]\.default_value'
)

# ID custom properties: bindings survive save/reopen and undo, and target
# trees are found again by uid instead of by (unstable) name.
TREE_UID_PROP = "colorista_uid"
BINDINGS_PROP = "colorista_driver_bindings"

# Every driver expression used by the bundled assets. Cross-tree drivers with
# these formulas are converted to explicit bindings at load time (drivers that
# read the parent tree would create a dependency cycle in Blender 5.x).
DRIVER_FORMULAS = {
    "1-default_value": lambda v: 1.0 - v,
    "default_value*-60": lambda v: v * -60.0,
    "default_value*default_value*30": lambda v: v * v * 30.0,
    "default_value*100": lambda v: v * 100.0,
    "100*default_value+100": lambda v: v * 100.0 + 100.0,
}


def sync_color_settings(
    current_sce: bpy.types.Scene,
    loaded_sce: bpy.types.Scene,
    *,
    use_asset_color_space: bool = False,
) -> None:
    if not use_asset_color_space:
        return
    try:
        current_sce.display_settings.display_device = loaded_sce.display_settings.display_device
        current_sce.view_settings.view_transform = loaded_sce.view_settings.view_transform
    except TypeError:
        pass


def _pick_source_scene(from_sces: set[bpy.types.Scene]) -> bpy.types.Scene:
    from_sce = next(iter(from_sces))
    for ls in from_sces:
        if ls.name == "AC-Coloring":
            return ls
    return from_sce


def transfer_compositor(
    from_sces: set[bpy.types.Scene],
    context: bpy.types.Context,
    *,
    use_asset_color_space: bool = False,
) -> None:
    """Take over the appended tree so Blender keeps dynamic node socket state."""
    if not from_sces:
        return
    from_sce = _pick_source_scene(from_sces)
    sce = context.scene
    source_tree = get_comp_node_tree(from_sce)
    if not source_tree:
        return
    old_tree = sce.compositing_node_group
    sce.compositing_node_group = source_tree
    if old_tree is not None and old_tree != source_tree and old_tree.users == 0:
        bpy.data.node_groups.remove(old_tree)
    r_layer = next((node for node in source_tree.nodes if node.type == "R_LAYERS"), None)
    if r_layer:
        r_layer.scene = sce
        r_layer.layer = context.view_layer.name
    sync_color_settings(sce, from_sce, use_asset_color_space=use_asset_color_space)


def reset_driver_with_scene_ref(an: bpy.types.AnimData, scenes: set[bpy.types.Scene]) -> None:
    """Retarget driver variables from the temp appended scenes to the active scene."""
    if not an or not scenes:
        return

    def is_scene_ref(v, scenes_set):
        if v.type != "SINGLE_PROP":
            return False
        for t in v.targets:
            if t.id_type == "SCENE" and t.id in scenes_set:
                return True
        return False

    for d in an.drivers:
        for v in d.driver.variables:
            if not is_scene_ref(v, scenes):
                continue
            v.type = "CONTEXT_PROP"


def reload_drivers(an: bpy.types.AnimData) -> None:
    """Remap legacy driver paths and poke targets so relations rebuild."""
    if not an:
        return
    remap_scene_compositor_driver_paths(an)
    targets = [
        t
        for d in an.drivers
        for v in d.driver.variables
        for t in v.targets
        if v.type == "CONTEXT_PROP"
    ]
    for t in targets:
        t.data_path = t.data_path


def extract_root_input_bindings(
    node_trees: set[bpy.types.NodeTree],
    root_node_names: set[str],
) -> list[tuple]:
    """Remove cross-tree drivers and return explicit scalar bindings."""
    bindings = []
    for tree in node_trees:
        animation = getattr(tree, "animation_data", None)
        if animation is None:
            continue
        for curve in list(animation.drivers):
            source_indexes = []
            for variable in curve.driver.variables:
                matches = []
                for target in variable.targets:
                    match = _MAIN_INPUT_PATH.fullmatch(target.data_path)
                    if match and match.group(1) in root_node_names:
                        matches.append((match.group(1), int(match.group(2))))
                if len(matches) == 1:
                    source_indexes.append(matches[0])
            expression = curve.driver.expression
            if len(source_indexes) != 1 or expression not in DRIVER_FORMULAS:
                continue
            node_name, index = source_indexes[0]
            binding = (
                tree,
                curve.data_path,
                curve.array_index,
                node_name,
                index,
                expression,
            )
            if binding not in bindings:
                bindings.append(binding)
            animation.drivers.remove(curve)
    return bindings


def _ensure_tree_uid(tree: bpy.types.NodeTree) -> str:
    uid = tree.get(TREE_UID_PROP, "")
    if not isinstance(uid, str) or not uid:
        uid = uuid.uuid4().hex
        tree[TREE_UID_PROP] = uid
    return uid


def store_driver_bindings(root_tree: bpy.types.NodeTree, bindings: list[tuple]) -> None:
    """Persist bindings on the root tree so they survive save/reopen and undo."""
    data = [
        {
            "uid": _ensure_tree_uid(target_tree),
            "path": data_path,
            "index": array_index,
            "node": node_name,
            "input": input_index,
            "expr": expression,
        }
        for target_tree, data_path, array_index, node_name, input_index, expression in bindings
    ]
    root_tree[BINDINGS_PROP] = json.dumps(data)


def load_driver_bindings(root_tree: bpy.types.NodeTree) -> list[tuple]:
    """Rebuild runtime bindings from the persisted form (empty when absent)."""
    raw = root_tree.get(BINDINGS_PROP, "")
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    trees_by_uid: dict[str, bpy.types.NodeTree] = {}
    for tree in bpy.data.node_groups:
        uid = tree.get(TREE_UID_PROP, "")
        if isinstance(uid, str) and uid and uid not in trees_by_uid:
            trees_by_uid[uid] = tree
    bindings = []
    for item in data:
        if not isinstance(item, dict):
            continue
        target_tree = trees_by_uid.get(item.get("uid", ""))
        expression = item.get("expr", "")
        if target_tree is None or expression not in DRIVER_FORMULAS:
            continue
        try:
            binding = (
                target_tree,
                str(item["path"]),
                int(item["index"]),
                str(item["node"]),
                int(item["input"]),
                expression,
            )
        except (KeyError, TypeError, ValueError):
            continue
        bindings.append(binding)
    return bindings


def _driver_targets_valid(driver: bpy.types.Driver, scene: bpy.types.Scene) -> bool:
    for variable in driver.variables:
        if variable.type not in {"SINGLE_PROP", "CONTEXT_PROP"}:
            continue
        for target in variable.targets:
            if variable.type == "CONTEXT_PROP":
                if target.context_property != "ACTIVE_SCENE":
                    continue
                owner = scene
            else:
                owner = target.id
            if owner is None:
                return False
            try:
                owner.path_resolve(target.data_path)
            except (AttributeError, ValueError):
                return False
    return True


def remove_invalid_drivers(
    node_trees: set[bpy.types.NodeTree], scene: bpy.types.Scene
) -> int:
    """Remove drivers that can never evaluate.

    Covers destinations removed in newer Blender versions and stale asset
    drivers whose variable source was lost at authoring time (id ``None``
    or a path that no longer resolves). Must run after driver paths were
    remapped for the current scene.
    """
    removed = 0
    for tree in node_trees:
        try:
            animation = tree.animation_data
        except ReferenceError:
            continue
        if animation is None:
            continue
        for curve in list(animation.drivers):
            try:
                tree.path_resolve(curve.data_path)
            except (AttributeError, ValueError):
                animation.drivers.remove(curve)
                removed += 1
                continue
            if not _driver_targets_valid(curve.driver, scene):
                animation.drivers.remove(curve)
                removed += 1
    return removed
