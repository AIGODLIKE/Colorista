import bpy

from ...utils.node import get_comp_node_tree

_NODE_EXPAND: dict[str, bool] = {}


def get_viewport_shadings() -> list[bpy.types.View3DShading]:
    shadings = []
    try:
        screen = bpy.context.screen
    except AttributeError:
        return shadings
    if screen is None:
        return shadings
    for area in screen.areas:
        if area.type != "VIEW_3D":
            continue
        shadings += [s.shading for s in area.spaces if s.type == "VIEW_3D"]
    return shadings


def set_viewport_shading(mode):
    for shading in get_viewport_shadings():
        shading.use_compositor = mode


def toggle_viewport_shading():
    for shading in get_viewport_shadings():
        if shading.use_compositor == "ALWAYS":
            shading.use_compositor = "DISABLED"
        else:
            shading.use_compositor = "ALWAYS"


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
