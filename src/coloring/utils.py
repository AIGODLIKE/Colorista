import bpy

from ...utils.node import get_comp_node_tree

_NODE_EXPAND: dict[str, bool] = {}


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


def node_expand_key(node: bpy.types.Node) -> str:
    tree = node.id_data
    return f"{getattr(tree, 'name_full', tree.name)}:{node.name}"


def node_is_expanded(node: bpy.types.Node) -> bool:
    return _NODE_EXPAND.get(node_expand_key(node), True)


def toggle_node_expanded(node: bpy.types.Node) -> bool:
    key = node_expand_key(node)
    expanded = not _NODE_EXPAND.get(key, True)
    _NODE_EXPAND[key] = expanded
    return expanded


def clear_node_expand_cache() -> None:
    _NODE_EXPAND.clear()


def register():
    ...


def unregister():
    clear_node_expand_cache()
