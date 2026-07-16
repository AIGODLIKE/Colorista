"""Serialize compositor UI-tunable values (sockets, CurveMapping, ColorRamp) to JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import bpy

from ...utils.logger import logger
from ...utils.node import get_comp_node_tree
from ...utils.paths import get_resource_dir
from ..compositor.ui_nodes import find_ui_node_inputs, iter_ui_coloring_nodes

PRESET_VERSION = 1


def _to_json_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (tuple, list)):
        return [_to_json_value(v) for v in value]
    try:
        return [_to_json_value(v) for v in value[:]]
    except Exception:
        return value


def dump_curve_mapping(mapping: bpy.types.CurveMapping) -> dict:
    data: dict[str, Any] = {"curves": []}
    for attr in (
        "extend",
        "tone",
        "use_clip",
        "clip_min_x",
        "clip_min_y",
        "clip_max_x",
        "clip_max_y",
    ):
        if hasattr(mapping, attr):
            try:
                data[attr] = getattr(mapping, attr)
            except Exception:
                pass
    for attr in ("black_level", "white_level"):
        if hasattr(mapping, attr):
            try:
                data[attr] = list(getattr(mapping, attr)[:])
            except Exception:
                pass

    for curve in mapping.curves:
        points = []
        for point in curve.points:
            pt: dict[str, Any] = {"location": list(point.location[:])}
            if hasattr(point, "handle_type"):
                pt["handle_type"] = point.handle_type
            points.append(pt)
        data["curves"].append({"points": points})
    return data


def apply_curve_mapping(mapping: bpy.types.CurveMapping, data: dict) -> None:
    if not data:
        return
    for attr in (
        "extend",
        "tone",
        "use_clip",
        "clip_min_x",
        "clip_min_y",
        "clip_max_x",
        "clip_max_y",
    ):
        if attr in data and hasattr(mapping, attr):
            try:
                setattr(mapping, attr, data[attr])
            except Exception:
                pass
    for attr in ("black_level", "white_level"):
        if attr in data and hasattr(mapping, attr):
            try:
                setattr(mapping, attr, data[attr])
            except Exception:
                pass

    curves_data = data.get("curves") or []
    for i, curve in enumerate(mapping.curves):
        if i >= len(curves_data):
            break
        points_data = curves_data[i].get("points") or []
        target_count = max(2, len(points_data))
        while len(curve.points) > target_count:
            try:
                curve.points.remove(curve.points[1])
            except Exception:
                break
        while len(curve.points) < len(points_data):
            try:
                curve.points.new(0.0, 0.0)
            except Exception:
                break
        for j, point in enumerate(curve.points):
            if j >= len(points_data):
                break
            pd = points_data[j]
            loc = pd.get("location")
            if loc is not None:
                try:
                    point.location = loc
                except Exception:
                    pass
            handle = pd.get("handle_type")
            if handle is not None and hasattr(point, "handle_type"):
                try:
                    point.handle_type = handle
                except Exception:
                    pass
    try:
        mapping.update()
    except Exception:
        pass


def dump_color_ramp(ramp: bpy.types.ColorRamp) -> dict:
    data: dict[str, Any] = {"elements": []}
    for attr in ("interpolation", "hue_interpolation", "color_mode"):
        if hasattr(ramp, attr):
            try:
                data[attr] = getattr(ramp, attr)
            except Exception:
                pass
    for el in ramp.elements:
        data["elements"].append({
            "position": el.position,
            "color": list(el.color[:]),
        })
    return data


def apply_color_ramp(ramp: bpy.types.ColorRamp, data: dict) -> None:
    if not data:
        return
    for attr in ("interpolation", "hue_interpolation", "color_mode"):
        if attr in data and hasattr(ramp, attr):
            try:
                setattr(ramp, attr, data[attr])
            except Exception:
                pass
    elements_data = data.get("elements") or []
    if not elements_data:
        return
    target_count = max(2, len(elements_data))
    while len(ramp.elements) > target_count:
        try:
            ramp.elements.remove(ramp.elements[-2])
        except Exception:
            break
    while len(ramp.elements) < len(elements_data):
        try:
            pos = elements_data[len(ramp.elements)].get("position", 0.5)
            ramp.elements.new(pos)
        except Exception:
            break
    for i, el in enumerate(ramp.elements):
        if i >= len(elements_data):
            break
        ed = elements_data[i]
        if "position" in ed:
            try:
                el.position = ed["position"]
            except Exception:
                pass
        if "color" in ed:
            try:
                el.color = ed["color"]
            except Exception:
                pass


def _dump_ui_socket_inputs(node: bpy.types.Node) -> dict:
    inputs: dict[str, Any] = {}
    for inp in find_ui_node_inputs(node):
        if inp.name.startswith("——"):
            continue
        if not hasattr(inp, "default_value"):
            continue
        try:
            inputs[inp.identifier] = _to_json_value(inp.default_value)
        except Exception:
            continue
    return inputs


def _apply_socket_inputs(node: bpy.types.Node, inputs: dict) -> None:
    if not inputs:
        return
    for identifier, value in inputs.items():
        sock = node.inputs.get(identifier)
        if sock is None or sock.is_linked:
            continue
        if not hasattr(sock, "default_value"):
            continue
        try:
            sock.default_value = value
        except Exception:
            try:
                cur = sock.default_value
                if hasattr(cur, "__len__") and not isinstance(cur, str):
                    for idx, item in enumerate(value):
                        cur[idx] = item
            except Exception:
                pass


def dump_ui_node(node: bpy.types.Node) -> dict:
    data: dict[str, Any] = {}
    inputs = _dump_ui_socket_inputs(node)
    if inputs:
        data["inputs"] = inputs

    mapping = getattr(node, "mapping", None)
    if mapping is not None and isinstance(mapping, bpy.types.CurveMapping):
        data["mapping"] = dump_curve_mapping(mapping)

    color_ramp = getattr(node, "color_ramp", None)
    if color_ramp is not None and isinstance(color_ramp, bpy.types.ColorRamp):
        data["color_ramp"] = dump_color_ramp(color_ramp)

    return data


def apply_ui_node(node: bpy.types.Node, data: dict) -> None:
    if not data:
        return
    _apply_socket_inputs(node, data.get("inputs") or {})

    if "mapping" in data:
        mapping = getattr(node, "mapping", None)
        if mapping is not None and isinstance(mapping, bpy.types.CurveMapping):
            apply_curve_mapping(mapping, data["mapping"])

    if "color_ramp" in data:
        color_ramp = getattr(node, "color_ramp", None)
        if color_ramp is not None and isinstance(color_ramp, bpy.types.ColorRamp):
            apply_color_ramp(color_ramp, data["color_ramp"])

    nested = data.get("nodes")
    if nested and node.type == "GROUP" and getattr(node, "node_tree", None):
        apply_node_tree_values(node.node_tree, nested)


def dump_node_tree_values(tree: bpy.types.NodeTree | None) -> dict:
    if tree is None:
        return {}
    nodes: dict[str, Any] = {}
    for node, _sockets in iter_ui_coloring_nodes(tree):
        if len(node.inputs) == 0:
            continue
        node_data = dump_ui_node(node)
        if node_data:
            nodes[node.name] = node_data
    return nodes


def apply_node_tree_values(tree: bpy.types.NodeTree | None, nodes_data: dict) -> None:
    if tree is None or not nodes_data:
        return
    for name, node_data in nodes_data.items():
        node = tree.nodes.get(name)
        if node is None:
            continue
        apply_ui_node(node, node_data)


def asset_path_for_storage(asset_path: Path | str) -> str:
    path = Path(asset_path)
    try:
        resolved = path.resolve()
    except Exception:
        resolved = path
    try:
        resource = get_resource_dir().resolve()
        return resolved.relative_to(resource).as_posix()
    except Exception:
        return path.as_posix()


def resolve_asset_path(stored: str) -> Path | None:
    if not stored:
        return None
    path = Path(stored)
    if path.is_file():
        return path
    candidate = get_resource_dir().joinpath(stored)
    if candidate.is_file():
        return candidate
    try:
        resolved = path.resolve()
        if resolved.is_file():
            return resolved
    except Exception:
        pass
    return None


def dump_color_settings(scene: bpy.types.Scene) -> dict:
    data: dict[str, Any] = {}
    try:
        data["display_device"] = scene.display_settings.display_device
    except Exception:
        pass
    try:
        data["view_transform"] = scene.view_settings.view_transform
    except Exception:
        pass
    return data


def apply_color_settings(
    scene: bpy.types.Scene,
    data: dict,
    *,
    use_asset_color_space: bool | None = None,
) -> None:
    if not data:
        return
    if use_asset_color_space is None:
        use_asset_color_space = False
    if not use_asset_color_space:
        return
    if "display_device" in data:
        try:
            scene.display_settings.display_device = data["display_device"]
        except Exception:
            pass
    if "view_transform" in data:
        try:
            scene.view_settings.view_transform = data["view_transform"]
        except Exception:
            pass


def dump_scene_preset(scene: bpy.types.Scene, asset_path: Path | str) -> dict:
    tree = get_comp_node_tree(scene)
    return {
        "version": PRESET_VERSION,
        "asset": asset_path_for_storage(asset_path),
        "color": dump_color_settings(scene),
        "nodes": dump_node_tree_values(tree),
    }


def apply_scene_preset(
    scene: bpy.types.Scene,
    data: dict,
    *,
    use_asset_color_space: bool | None = None,
) -> None:
    apply_color_settings(
        scene,
        data.get("color") or {},
        use_asset_color_space=use_asset_color_space,
    )
    apply_node_tree_values(get_comp_node_tree(scene), data.get("nodes") or {})


def write_preset_json(path: Path | str, data: dict) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def read_preset_json(path: Path | str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_compositor_values_json(
    filepath: Path | str,
    scene: bpy.types.Scene,
    asset_path: Path | str,
) -> Path:
    data = dump_scene_preset(scene, asset_path)
    path = write_preset_json(filepath, data)
    logger.debug("Saved compositor values JSON: %s", path)
    return path
