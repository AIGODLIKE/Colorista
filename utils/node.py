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
        if inp.identifier not in nt.inputs:
            continue
        try:
            nt.inputs[inp.identifier].default_value = inp.default_value
        except ValueError:
            print("Error copying node property:", inp.identifier, nt.inputs[inp.identifier].default_value, inp.default_value)
        except AttributeError:
            pass


def copy_node_tree_drivers(sf: bpy.types.Scene, st: bpy.types.Scene):
    st_tree = get_comp_node_tree(st)
    sf_tree = get_comp_node_tree(sf)
    if not sf_tree:
        return
    if not sf_tree.animation_data:
        return
    if not st_tree.animation_data:
        st_tree.animation_data_create()
    for driver in sf_tree.animation_data.drivers:
        st_tree.animation_data.drivers.from_existing(src_driver=driver)


def copy_comp_node_tree(sf: bpy.types.Scene, st: bpy.types.Scene):
    if bpy.app.version >= (5, 0, 0):
        sft = sf.compositing_node_group
        st.compositing_node_group = sf.compositing_node_group.copy() if sft else sft
        return
    ensure_comp_node_tree(st)
    st_tree = get_comp_node_tree(st)
    sf_tree = get_comp_node_tree(sf)
    st_tree.nodes.clear()
    node_map = {}
    for node in sf_tree.nodes:
        new_node = st_tree.nodes.new(type=node.bl_idname)
        if new_node.type == "GROUP":
            new_node.node_tree = node.node_tree
        copy_node_properties(node, new_node)
        node_map[node.name] = new_node
    for link in sf_tree.links:
        fnode = node_map[link.from_node.name]
        tnode = node_map[link.to_node.name]
        try:
            fsocket = fnode.outputs[link.from_socket.identifier]
            tsocket = tnode.inputs[link.to_socket.identifier]
            st_tree.links.new(tsocket, fsocket)
        except KeyError:
            print("KeyError:", link.from_node.name, link.to_node.name, link.from_socket.identifier)
    for node in st_tree.nodes:
        if node.type == "R_LAYERS":
            node.scene = None


def ensure_comp_node_tree(sce: bpy.types.Scene):
    if bpy.app.version >= (5, 0):
        if sce.compositing_node_group:
            return
        tree = bpy.data.node_groups.new("Render Layers", "CompositorNodeTree")
        sce.compositing_node_group = tree
    else:
        sce.use_nodes = True


def get_comp_node_tree(sce: bpy.types.Scene) -> bpy.types.CompositorNodeTree:
    if bpy.app.version >= (5, 0):
        return sce.compositing_node_group
    return sce.node_tree
