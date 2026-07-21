"""Helpers for Colorista panel node / socket iteration."""

import bpy


def node_panel_id(node: bpy.types.Node) -> str:
    return f"colorista_{node.name}"


def find_ui_node_inputs(node: bpy.types.Node) -> list:
    """Sockets shown in the Colorista panel."""
    sockets = []
    for inp in node.inputs:
        if inp.is_linked:
            continue
        if inp.enabled is False or inp.hide:
            continue
        if inp.type == "RGBA" and inp.hide_value:
            continue
        sockets.append(inp)
    return sockets


def iter_ui_coloring_nodes(tree: bpy.types.NodeTree | None):
    """Yield (node, sockets) for top-level compositor nodes in the Colorista panel."""
    if tree is None:
        return
    nodes = []
    for node in tree.nodes:
        if node.type in {"VIEWER", "R_LAYERS"}:
            continue
        if not node.label:
            continue
        if node.bl_idname == "NodeUndefined":
            continue
        sockets = find_ui_node_inputs(node)
        if len(sockets) == 0 and node.type == "GROUP":
            continue
        nodes.append((node, sockets))
    nodes.sort(key=lambda item: item[0].label)
    yield from nodes


def draw_layout_panel(layout, panel_id: str, default_closed: bool = False):
    return layout.panel(panel_id, default_closed=default_closed)
