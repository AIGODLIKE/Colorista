"""Helpers for Colorista panel node / socket iteration."""

import bpy


_COLOR_BALANCE_MODE_INPUT = 2
_COLOR_BALANCE_MODE_INPUTS = {
    "Lift/Gamma/Gain": range(3, 9),
    "Offset/Power/Slope (ASC-CDL)": range(9, 15),
    "Offset/Power/Slope": range(9, 15),
    "White Point": range(15, 19),
    "Temperature/Tint": range(15, 19),
}

_COLOR_CORRECTION_SECTIONS = (
    ("mask", "Mask", (1,)),
    ("master", "Master", range(2, 7)),
    ("highlights", "Highlights", range(7, 12)),
    ("midtones", "Midtones", range(12, 17)),
    ("shadows", "Shadows", range(17, 22)),
    ("midtones_range", "Midtones Range", (22, 23)),
    ("channels", "Channels", (24, 25, 26)),
)


def node_panel_id(node: bpy.types.Node) -> str:
    return f"colorista_{node.name}"


def _is_color_balance_socket_visible(node: bpy.types.Node, index: int) -> bool:
    if node.bl_idname != "CompositorNodeColorBalance":
        return True
    if index in (1, _COLOR_BALANCE_MODE_INPUT):
        return True
    try:
        mode = node.inputs[_COLOR_BALANCE_MODE_INPUT].default_value
    except (AttributeError, IndexError, TypeError):
        return True
    indexes = _COLOR_BALANCE_MODE_INPUTS.get(mode)
    return indexes is None or index in indexes


def find_ui_node_inputs(node: bpy.types.Node, *, visible_only: bool = False) -> list:
    """Return editable node inputs, optionally matching the active node mode."""
    sockets = []
    for index, inp in enumerate(node.inputs):
        if inp.is_linked:
            continue
        if inp.enabled is False or inp.hide:
            continue
        if inp.type == "RGBA" and inp.hide_value:
            continue
        if visible_only and not _is_color_balance_socket_visible(node, index):
            continue
        sockets.append(inp)
    return sockets


def iter_ui_node_input_sections(node: bpy.types.Node, sockets: list):
    """Yield stable collapsible sections for nodes with native UI groups."""
    if node.bl_idname != "CompositorNodeColorCorrection":
        yield None, "", sockets
        return

    allowed = {socket.identifier for socket in sockets}
    for section_id, label, indexes in _COLOR_CORRECTION_SECTIONS:
        section_sockets = [
            node.inputs[index]
            for index in indexes
            if index < len(node.inputs)
            and node.inputs[index].identifier in allowed
        ]
        if section_sockets:
            yield section_id, label, section_sockets


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
        sockets = find_ui_node_inputs(node, visible_only=True)
        if len(sockets) == 0 and node.type == "GROUP":
            continue
        nodes.append((node, sockets))
    nodes.sort(key=lambda item: item[0].label)
    yield from nodes


def draw_layout_panel(layout, panel_id: str, default_closed: bool = False):
    return layout.panel(panel_id, default_closed=default_closed)
