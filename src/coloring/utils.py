import bpy

from ...utils.node import get_comp_node_tree


def _get_window_screen(context: bpy.types.Context) -> bpy.types.Screen | None:
    window = context.window
    if window is not None:
        return window.screen
    return context.screen


def get_window_viewport_shadings(
    context: bpy.types.Context | None = None,
) -> list[bpy.types.View3DShading]:
    context = context or bpy.context
    screen = _get_window_screen(context)
    if screen is None:
        return []
    shadings = []
    for area in screen.areas:
        if area.type != "VIEW_3D":
            continue
        for space in area.spaces:
            if space.type == "VIEW_3D":
                shadings.append(space.shading)
    return shadings


def is_window_viewport_compositor_active(
    context: bpy.types.Context | None = None,
) -> bool:
    return any(
        shading.use_compositor == "ALWAYS"
        for shading in get_window_viewport_shadings(context)
    )


def set_viewport_shading(
    mode: str,
    context: bpy.types.Context | None = None,
) -> None:
    for shading in get_window_viewport_shadings(context):
        shading.use_compositor = mode


def toggle_viewport_shading(context: bpy.types.Context | None = None) -> None:
    context = context or bpy.context
    mode = "DISABLED" if is_window_viewport_compositor_active(context) else "ALWAYS"
    set_viewport_shading(mode, context)


def clear_compositor(scene: bpy.types.Scene) -> None:
    if bpy.app.version >= (5, 0, 0):
        scene.compositing_node_group = None
        return
    tree = get_comp_node_tree(scene)
    if tree is not None:
        tree.nodes.clear()
    scene.use_nodes = False


def node_panel_id(tree: bpy.types.NodeTree, node: bpy.types.Node) -> str:
    # Stable across compositor tree copies / preset reloads (tree.name changes on .copy()).
    return f"colorista_{node.name}"


def find_ui_node_inputs(node: bpy.types.Node) -> list:
    """Sockets shown in the Colorista panel (same rules as ColoringPanel)."""
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
    """Top-level compositor nodes that appear in the Colorista panel."""
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
        nodes.append(node)
    nodes.sort(key=lambda n: n.label)
    yield from nodes


def draw_layout_panel(layout, panel_id: str, default_closed: bool = False):
    try:
        return layout.panel(idname=panel_id, default_closed=default_closed)
    except TypeError:
        return layout.panel(panel_id, default_closed=default_closed)


def register():
    ...


def unregister():
    ...
