import bpy

from ...utils.node import get_comp_node_tree

VTC_NAME = "colorista-Color Space"


def has_custom_vt_control() -> bool:
    tree = get_comp_node_tree(bpy.context.scene)
    if not tree:
        return False
    color_space_control = tree.nodes.get(VTC_NAME)
    if not color_space_control:
        return False
    if not color_space_control.inputs:
        return False
    space = color_space_control.inputs.get("Space")
    if not space:
        space = color_space_control.inputs[0]
    return space is not None


def update_custom_vt():
    if not has_custom_vt_control():
        return
    tree = get_comp_node_tree(bpy.context.scene)
    color_space_control = tree.nodes.get(VTC_NAME)
    space = color_space_control.inputs.get("Space")
    if not space:
        space = color_space_control.inputs[0]
    try:
        color_space = float(space.default_value)
        ori_vt = bpy.context.scene.view_settings.view_transform
        space_value_map = {
            "AgX": 0,
            "Standard": 0.1,
            "Filmic": 0.2,
            "Khronos PBR Neutral": 0.3,
        }
        space_value = space_value_map.get(ori_vt, 0)
        if abs(space_value - color_space) < 0.00001:
            return
        space.default_value = space_value
    except Exception:
        pass


def register():
    pass


def unregister():
    pass
