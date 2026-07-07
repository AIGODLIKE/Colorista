import bpy

from .logger import logger


def scene_uses_compositor(sce: bpy.types.Scene) -> bool:
    if bpy.app.version >= (5, 0, 0):
        return sce.compositing_node_group is not None
    return bool(sce.use_nodes)


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
            logger.debug(
                "Error copying node property: %s %s %s",
                inp.identifier,
                nt.inputs[inp.identifier].default_value,
                inp.default_value,
            )
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
    remap_scene_compositor_driver_paths(st_tree.animation_data)


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
            logger.debug(
                "KeyError linking nodes: %s %s %s",
                link.from_node.name,
                link.to_node.name,
                link.from_socket.identifier,
            )
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


def remap_scene_compositor_driver_paths(an: bpy.types.AnimData) -> None:
    """Remap legacy scene.node_tree paths in drivers for Blender 5.x."""
    if bpy.app.version < (5, 0, 0) or not an:
        return
    old_prefix = "node_tree."
    new_prefix = "compositing_node_group."

    def _remap(path: str) -> str:
        if path.startswith(old_prefix):
            return new_prefix + path[len(old_prefix):]
        return path

    for fc in an.drivers:
        fc.data_path = _remap(fc.data_path)
        driver = fc.driver
        if not driver:
            continue
        for var in driver.variables:
            for target in var.targets:
                target.data_path = _remap(target.data_path)
