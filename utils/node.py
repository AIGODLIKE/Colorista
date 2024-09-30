import bpy


def copy_node_properties(nf: bpy.types.Node, nt: bpy.types.Node):
    """
    拷贝两个节点的属性, 节点组需要特殊处理
    """
    if nt.type == "GROUP":
        nt.node_tree = nf.node_tree
    bpy.context.view_layer.update()
    for prop_name in nf.bl_rna.properties.keys():
        if nt.type == "GROUP" and prop_name == "node_tree":
            continue
        try:
            setattr(nt, prop_name, getattr(nf, prop_name))
        except (AttributeError, TypeError):
            pass
    for inp in nf.inputs:
        nt.inputs[inp.identifier].default_value = inp.default_value
