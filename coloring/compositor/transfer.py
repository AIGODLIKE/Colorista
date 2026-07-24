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
_TARGET_INPUT_PATH = re.compile(
    r'nodes\["([^"]+)"\]\.inputs\[(\d+)\]\.default_value'
)
_LEGACY_TARGET_PROPERTY_PATH = re.compile(
    r'nodes\["([^"]+)"\]\.(sigma_space)'
)

# Blender 5.x moved these compositor node properties to input sockets. Asset
# drivers retain the old RNA paths, so resolve only the known migrations here.
_LEGACY_TARGET_INPUTS = {
    ("CompositorNodeBilateralblur", "sigma_space"): 2,
}

# ID custom properties: bindings survive save/reopen and undo, and target
# trees are found again by uid instead of by (unstable) name.
TREE_UID_PROP = "colorista_uid"
BINDINGS_PROP = "colorista_driver_bindings"
NATIVE_BINDINGS_VERSION_PROP = "colorista_native_bindings_version"
NATIVE_BINDINGS_VERSION = 2

_BINDING_NODE_PREFIX = "__Colorista Binding"
_BINDING_NODE_LABEL = "Colorista Native Binding"

# Every driver expression used by the bundled assets. They are recognized only
# during one-time conversion to native group links and Math nodes.
DRIVER_EXPRESSIONS = frozenset(
    {
        "1-default_value",
        "default_value*-60",
        "default_value*default_value*30",
        "default_value*100",
        "100*default_value+100",
    }
)


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


def _is_numbered_id_copy(name: str, original: str) -> bool:
    """Match Blender's numeric suffix added while an older asset is still loaded."""
    if not name.startswith(f"{original}."):
        return False
    suffix = name[len(original) + 1 :]
    return len(suffix) >= 3 and suffix.isdecimal()


def _resolve_root_source_node(
    root_tree: bpy.types.NodeTree,
    stored_name: str,
    input_index: int,
):
    """Resolve a source saved before its group node was renamed or localized."""
    node = root_tree.nodes.get(stored_name)
    if node is not None and input_index < len(node.inputs):
        return node

    named_candidates = []
    for candidate in root_tree.nodes:
        child_tree = getattr(candidate, "node_tree", None)
        if child_tree is None or input_index >= len(candidate.inputs):
            continue
        if child_tree.name == stored_name or _is_numbered_id_copy(
            child_tree.name, stored_name
        ):
            named_candidates.append(candidate)
    if named_candidates:
        return named_candidates[0] if len(named_candidates) == 1 else None

    # Localized assets can change the child-tree name entirely. The legacy path
    # still contains the exact input index; accept it only when that index
    # identifies one group node in the current root tree.
    structural_candidates = [
        candidate
        for candidate in root_tree.nodes
        if candidate.type == "GROUP"
        and candidate.node_tree is not None
        and input_index < len(candidate.inputs)
    ]
    return structural_candidates[0] if len(structural_candidates) == 1 else None


def extract_root_input_bindings(
    node_trees: set[bpy.types.NodeTree],
    root_tree: bpy.types.NodeTree,
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
                    if match is None:
                        continue
                    input_index = int(match.group(2))
                    source_node = _resolve_root_source_node(
                        root_tree,
                        match.group(1),
                        input_index,
                    )
                    if source_node is not None:
                        matches.append((source_node.name, input_index))
                if len(matches) == 1:
                    source_indexes.append(matches[0])
            expression = curve.driver.expression
            if len(source_indexes) != 1 or expression not in DRIVER_EXPRESSIONS:
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


def _group_input_output(
    tree: bpy.types.NodeTree,
    identifier: str,
    fallback_name: str,
):
    group_inputs = [node for node in tree.nodes if node.type == "GROUP_INPUT"]
    if not group_inputs:
        try:
            group_inputs.append(tree.nodes.new("NodeGroupInput"))
        except RuntimeError:
            return None
    for group_input in group_inputs:
        for output in group_input.outputs:
            if output.identifier == identifier:
                return output
    for group_input in group_inputs:
        output = group_input.outputs.get(fallback_name)
        if output is not None:
            return output
    return None


def _find_group_paths(
    source_tree: bpy.types.NodeTree,
    target_tree: bpy.types.NodeTree,
) -> list[list[bpy.types.Node]]:
    """Return every nested group-node path from source_tree to target_tree."""
    if source_tree == target_tree:
        return [[]]
    paths: list[list[bpy.types.Node]] = []
    stack = [(source_tree, [], {source_tree.as_pointer()})]
    while stack:
        tree, path, visited = stack.pop()
        for node in tree.nodes:
            child_tree = getattr(node, "node_tree", None)
            if child_tree is None:
                continue
            child_path = [*path, node]
            if child_tree == target_tree:
                paths.append(child_path)
                continue
            pointer = child_tree.as_pointer()
            if pointer in visited:
                continue
            stack.append((child_tree, child_path, {*visited, pointer}))
    return paths


def _binding_socket_name(source_node: bpy.types.Node, input_index: int) -> str:
    signature = f"{source_node.id_data.name}:{source_node.name}:{input_index}"
    token = uuid.uuid5(uuid.NAMESPACE_URL, signature).hex[:12]
    return f"__Colorista Input {token}"


def _ensure_interface_input(
    tree: bpy.types.NodeTree,
    name: str,
):
    for item in tree.interface.items_tree:
        if (
            getattr(item, "item_type", None) == "SOCKET"
            and getattr(item, "in_out", None) == "INPUT"
            and item.name == name
        ):
            return item
    try:
        socket = tree.interface.new_socket(
            name=name,
            in_out="INPUT",
            socket_type="NodeSocketFloat",
        )
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return None
    if hasattr(socket, "hide_value"):
        socket.hide_value = True
    socket.description = "Internal Colorista value link"
    return socket


def _socket_by_identifier(sockets, identifier: str, fallback_name: str):
    for socket in sockets:
        if socket.identifier == identifier:
            return socket
    return sockets.get(fallback_name)


def _ensure_link(
    tree: bpy.types.NodeTree,
    output_socket,
    input_socket,
) -> bool:
    for link in input_socket.links:
        if link.from_socket == output_socket:
            return True
    if input_socket.is_linked:
        return False
    try:
        tree.links.new(output_socket, input_socket)
    except (RuntimeError, TypeError):
        return False
    return True


def _propagate_group_input(
    source_node: bpy.types.Node,
    input_index: int,
    path: list[bpy.types.Node],
):
    source_tree = source_node.node_tree
    source_socket = source_node.inputs[input_index]
    output = _group_input_output(
        source_tree,
        source_socket.identifier,
        source_socket.name,
    )
    if output is None:
        return None
    helper_name = _binding_socket_name(source_node, input_index)
    current_tree = source_tree
    for group_node in path:
        child_tree = group_node.node_tree
        interface_socket = _ensure_interface_input(child_tree, helper_name)
        if interface_socket is None:
            return None
        group_socket = _socket_by_identifier(
            group_node.inputs,
            interface_socket.identifier,
            helper_name,
        )
        if group_socket is None or not _ensure_link(current_tree, output, group_socket):
            return None
        output = _group_input_output(
            child_tree,
            interface_socket.identifier,
            helper_name,
        )
        if output is None:
            return None
        current_tree = child_tree
    return output


def _ensure_math_node(
    tree: bpy.types.NodeTree,
    key: str,
    suffix: str,
    operation: str,
    target_node: bpy.types.Node,
):
    name = f"{_BINDING_NODE_PREFIX} {key} {suffix}"
    node = tree.nodes.get(name)
    if node is None or node.bl_idname != "ShaderNodeMath":
        node = tree.nodes.new("ShaderNodeMath")
        node.name = name
    node.label = _BINDING_NODE_LABEL
    node.operation = operation
    node.hide = True
    node.location = (target_node.location.x - 220.0, target_node.location.y)
    return node


def _ensure_combine_xyz_node(
    tree: bpy.types.NodeTree,
    key: str,
    target_node: bpy.types.Node,
):
    name = f"{_BINDING_NODE_PREFIX} {key} Vector"
    node = tree.nodes.get(name)
    if node is None or node.bl_idname != "ShaderNodeCombineXYZ":
        node = tree.nodes.new("ShaderNodeCombineXYZ")
        node.name = name
    node.label = _BINDING_NODE_LABEL
    node.hide = True
    node.location = (target_node.location.x - 100.0, target_node.location.y)
    return node


def _is_normalized_split_position(
    target_node: bpy.types.Node,
    target_socket,
    array_index: int,
) -> bool:
    return (
        target_node.bl_idname == "CompositorNodeSplit"
        and target_socket.bl_idname == "NodeSocketVectorFactor2D"
        and array_index == 0
    )


def _formula_output(
    tree: bpy.types.NodeTree,
    source_socket,
    expression: str,
    key: str,
    target_node: bpy.types.Node,
    target_socket,
    array_index: int,
):
    def math(suffix: str, operation: str):
        return _ensure_math_node(tree, key, suffix, operation, target_node)

    # The Split node used percentages in the Blender version that authored the
    # assets. Blender 5.1+ migrates Position to a normalized 2D vector, but it
    # does not rewrite the old driver expression.
    if _is_normalized_split_position(target_node, target_socket, array_index):
        if expression == "default_value*100":
            return source_socket
        if expression == "100*default_value+100":
            node = math("A", "ADD")
            node.inputs[1].default_value = 1.0
            if not _ensure_link(tree, source_socket, node.inputs[0]):
                return None
            return node.outputs[0]

    if expression == "1-default_value":
        node = math("A", "SUBTRACT")
        node.inputs[0].default_value = 1.0
        if not _ensure_link(tree, source_socket, node.inputs[1]):
            return None
        return node.outputs[0]
    if expression == "default_value*-60":
        node = math("A", "MULTIPLY")
        node.inputs[1].default_value = -60.0
        if not _ensure_link(tree, source_socket, node.inputs[0]):
            return None
        return node.outputs[0]
    if expression == "default_value*default_value*30":
        square = math("A", "MULTIPLY")
        if not _ensure_link(tree, source_socket, square.inputs[0]):
            return None
        if not _ensure_link(tree, source_socket, square.inputs[1]):
            return None
        scale = math("B", "MULTIPLY")
        scale.inputs[1].default_value = 30.0
        if not _ensure_link(tree, square.outputs[0], scale.inputs[0]):
            return None
        return scale.outputs[0]
    if expression == "default_value*100":
        node = math("A", "MULTIPLY")
        node.inputs[1].default_value = 100.0
        if not _ensure_link(tree, source_socket, node.inputs[0]):
            return None
        return node.outputs[0]
    if expression == "100*default_value+100":
        scale = math("A", "MULTIPLY")
        scale.inputs[1].default_value = 100.0
        if not _ensure_link(tree, source_socket, scale.inputs[0]):
            return None
        offset = math("B", "ADD")
        offset.inputs[1].default_value = 100.0
        if not _ensure_link(tree, scale.outputs[0], offset.inputs[0]):
            return None
        return offset.outputs[0]
    return None


def _component_vector_output(
    tree: bpy.types.NodeTree,
    source_socket,
    target_socket,
    array_index: int,
    key: str,
    target_node: bpy.types.Node,
):
    """Put a scalar driver replacement into one vector component."""
    if target_socket.type != "VECTOR":
        return source_socket

    try:
        defaults = list(target_socket.default_value)
    except (AttributeError, TypeError):
        return None
    if array_index < 0 or array_index >= len(defaults) or array_index >= 3:
        return None

    combine = _ensure_combine_xyz_node(tree, key, target_node)
    for index, socket in enumerate(combine.inputs[:3]):
        socket.default_value = defaults[index] if index < len(defaults) else 0.0
    if not _ensure_link(tree, source_socket, combine.inputs[array_index]):
        return None
    return combine.outputs[0]


def _resolve_target_input(
    target_tree: bpy.types.NodeTree,
    data_path: str,
):
    match = _TARGET_INPUT_PATH.fullmatch(data_path)
    if match is not None:
        target_node = target_tree.nodes.get(match.group(1))
        target_index = int(match.group(2))
    else:
        match = _LEGACY_TARGET_PROPERTY_PATH.fullmatch(data_path)
        if match is None:
            return None
        target_node = target_tree.nodes.get(match.group(1))
        if target_node is None:
            return None
        target_index = _LEGACY_TARGET_INPUTS.get(
            (target_node.bl_idname, match.group(2))
        )
        if target_index is None:
            return None

    if target_node is None or target_index >= len(target_node.inputs):
        return None
    return target_node, target_node.inputs[target_index]


def _materialize_binding(
    root_tree: bpy.types.NodeTree,
    binding: tuple,
) -> bool:
    target_tree, data_path, array_index, node_name, input_index, expression = binding
    source_node = _resolve_root_source_node(root_tree, node_name, input_index)
    if (
        source_node is None
        or source_node.node_tree is None
        or input_index >= len(source_node.inputs)
    ):
        return False
    target = _resolve_target_input(target_tree, data_path)
    if target is None:
        return False
    target_node, target_socket = target
    if target_socket.is_linked:
        return True

    paths = _find_group_paths(source_node.node_tree, target_tree)
    if not paths:
        return False
    source_outputs = []
    for path in paths:
        output = _propagate_group_input(source_node, input_index, path)
        if output is None:
            return False
        source_outputs.append(output)
    source_output = source_outputs[0]

    signature = "|".join(
        (
            _ensure_tree_uid(target_tree),
            data_path,
            node_name,
            str(input_index),
            str(array_index),
            expression,
        )
    )
    key = uuid.uuid5(uuid.NAMESPACE_URL, signature).hex[:12]
    output = _formula_output(
        target_tree,
        source_output,
        expression,
        key,
        target_node,
        target_socket,
        array_index,
    )
    if output is not None:
        output = _component_vector_output(
            target_tree,
            output,
            target_socket,
            array_index,
            key,
            target_node,
        )
    return output is not None and _ensure_link(target_tree, output, target_socket)


def materialize_root_input_bindings(
    root_tree: bpy.types.NodeTree,
    bindings: list[tuple],
) -> list[tuple]:
    """Replace former cross-tree drivers with native group links and Math nodes.

    Returns only bindings whose target cannot be represented as a node socket.
    They remain serialized for a future migration, but are not driven at runtime.
    """
    remaining = []
    for binding in bindings:
        try:
            converted = _materialize_binding(root_tree, binding)
        except (AttributeError, IndexError, ReferenceError, RuntimeError, TypeError, ValueError):
            converted = False
        if not converted:
            remaining.append(binding)
    return remaining


def _walk_group_trees(root_tree: bpy.types.NodeTree):
    pending = [root_tree]
    visited: set[int] = set()
    while pending:
        tree = pending.pop()
        pointer = tree.as_pointer()
        if pointer in visited:
            continue
        visited.add(pointer)
        yield tree
        for node in tree.nodes:
            child_tree = getattr(node, "node_tree", None)
            if child_tree is not None:
                pending.append(child_tree)


def _normalize_legacy_split_math(output_node: bpy.types.Node) -> bool:
    """Change the generated v*100[+100] chain to v*1[+1]."""
    changed = False
    pending = [output_node]
    visited: set[int] = set()
    while pending:
        node = pending.pop()
        pointer = node.as_pointer()
        if pointer in visited:
            continue
        visited.add(pointer)
        if node.bl_idname != "ShaderNodeMath" or node.label != _BINDING_NODE_LABEL:
            continue
        for socket in node.inputs[:2]:
            if socket.is_linked:
                pending.extend(link.from_node for link in socket.links)
                continue
            try:
                is_legacy_scale = abs(float(socket.default_value) - 100.0) < 1.0e-5
            except (AttributeError, TypeError, ValueError):
                is_legacy_scale = False
            if is_legacy_scale:
                socket.default_value = 1.0
                changed = True
    return changed


def _upgrade_legacy_split_binding(
    tree: bpy.types.NodeTree,
    target_node: bpy.types.Node,
) -> bool:
    if len(target_node.inputs) == 0:
        return False
    target_socket = target_node.inputs[0]
    if target_socket.bl_idname != "NodeSocketVectorFactor2D" or not target_socket.is_linked:
        return False

    target_link = target_socket.links[0]
    scalar_node = target_link.from_node
    if scalar_node.bl_idname == "ShaderNodeCombineXYZ":
        return False
    if scalar_node.bl_idname != "ShaderNodeMath" or scalar_node.label != _BINDING_NODE_LABEL:
        return False

    changed = _normalize_legacy_split_math(scalar_node)
    signature = f"{_ensure_tree_uid(tree)}|{target_node.name}|Position|legacy-vector"
    key = uuid.uuid5(uuid.NAMESPACE_URL, signature).hex[:12]
    combine = _ensure_combine_xyz_node(tree, key, target_node)
    try:
        defaults = list(target_socket.default_value)
    except (AttributeError, TypeError):
        defaults = [0.0, 0.5]
    for index, socket in enumerate(combine.inputs[:3]):
        socket.default_value = defaults[index] if index < len(defaults) else 0.0
    if not _ensure_link(tree, target_link.from_socket, combine.inputs[0]):
        return changed

    tree.links.remove(target_link)
    if _ensure_link(tree, combine.outputs[0], target_socket):
        return True
    _ensure_link(tree, scalar_node.outputs[0], target_socket)
    return changed


def upgrade_native_bindings(root_tree: bpy.types.NodeTree | None) -> int:
    """Repair native bindings created before normalized Split support."""
    if root_tree is None:
        return 0
    changed = 0
    for tree in _walk_group_trees(root_tree):
        for node in tree.nodes:
            if node.bl_idname != "CompositorNodeSplit":
                continue
            if _upgrade_legacy_split_binding(tree, node):
                changed += 1
    root_tree[NATIVE_BINDINGS_VERSION_PROP] = NATIVE_BINDINGS_VERSION
    return changed


def _ensure_tree_uid(tree: bpy.types.NodeTree) -> str:
    uid = tree.get(TREE_UID_PROP, "")
    if not isinstance(uid, str) or not uid:
        uid = uuid.uuid4().hex
        tree[TREE_UID_PROP] = uid
    return uid


def store_driver_bindings(root_tree: bpy.types.NodeTree, bindings: list[tuple]) -> None:
    """Persist unconverted legacy metadata for later migrations."""
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
    """Resolve persisted legacy metadata to current node-tree objects."""
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
        if target_tree is None or expression not in DRIVER_EXPRESSIONS:
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


def materialize_stored_bindings(root_tree: bpy.types.NodeTree | None) -> list[tuple]:
    """Upgrade bindings saved by earlier Colorista versions to native nodes."""
    if root_tree is None:
        return []
    bindings = load_driver_bindings(root_tree)
    remaining = materialize_root_input_bindings(root_tree, bindings)
    if bindings and len(remaining) != len(bindings):
        store_driver_bindings(root_tree, remaining)
    upgrade_native_bindings(root_tree)
    return remaining


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
