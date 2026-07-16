"""Transfer compositor node trees between scenes (4.x copy / 5.x assign)."""

from __future__ import annotations

import bpy

from ...utils.compat import IS_BL5
from ...utils.logger import logger
from ...utils.node import (
    copy_node_properties,
    copy_node_tree_drivers,
    get_comp_node_tree,
)
from ..preference import get_pref


def sync_color_settings(current_sce: bpy.types.Scene, loaded_sce: bpy.types.Scene) -> None:
    pref = get_pref()
    if not pref or not pref.use_asset_color_space_pref:
        return
    try:
        current_sce.display_settings.display_device = loaded_sce.display_settings.display_device
        current_sce.view_settings.view_transform = loaded_sce.view_settings.view_transform
    except TypeError:
        pass


def transfer_compositor(
    from_sces: set[bpy.types.Scene],
    context: bpy.types.Context,
) -> None:
    if not from_sces:
        return
    from_sce = next(iter(from_sces))
    for ls in from_sces:
        if ls.name == "AC-Coloring":
            from_sce = ls
            break
    sce = context.scene
    context.view_layer.update()
    from_tree = get_comp_node_tree(from_sce)
    to_tree = get_comp_node_tree(sce)
    r_layer = None

    if IS_BL5:
        if not from_tree:
            return
        old_tree = sce.compositing_node_group
        sce.compositing_node_group = from_tree
        to_tree = sce.compositing_node_group
        if old_tree is not None and old_tree != to_tree:
            try:
                if old_tree.users == 0:
                    bpy.data.node_groups.remove(old_tree)
            except ReferenceError:
                pass
        for n in to_tree.nodes:
            if n.type == "R_LAYERS":
                r_layer = n
        if r_layer:
            r_layer.scene = sce
            r_layer.layer = context.view_layer.name
        sync_color_settings(sce, from_sce)
        return

    node_map = {}
    for nf in from_tree.nodes:
        if nf.bl_idname == "NodeUndefined":
            logger.error("NodeUndefined: %s", nf.name)
            continue
        nt = to_tree.nodes.new(type=nf.bl_idname)
        if nt.type == "GROUP":
            nt.node_tree = nf.node_tree
        if nf.type == "R_LAYERS":
            r_layer = nt
        if nf.bl_idname == "CompositorNodeOutputFile":
            nt.file_slots.clear()
            for i, inp in enumerate(nf.inputs):
                nt.file_slots.new(inp.identifier)
                nt.file_slots[i].path = nf.file_slots[i].path
                nt.file_slots[i].use_node_format = nf.file_slots[i].use_node_format
        copy_node_properties(nf, nt)
        node_map[nf.name] = nt
    for link in from_tree.links:
        if link.from_node.bl_idname == "NodeUndefined" or link.to_node.bl_idname == "NodeUndefined":
            logger.error(
                "NodeUndefined link: %s -> %s",
                link.from_node.name,
                link.to_node.name,
            )
            continue
        if link.from_node.name not in node_map or link.to_node.name not in node_map:
            continue
        fnode = node_map[link.from_node.name]
        tnode = node_map[link.to_node.name]
        fsocket = fnode.outputs.get(link.from_socket.identifier)
        tsocket = tnode.inputs.get(link.to_socket.identifier)
        if not fsocket:
            logger.error("Socket not found: %s", link.from_socket.identifier)
            continue
        if not tsocket:
            logger.error("Socket not found: %s", link.to_socket.identifier)
            continue
        to_tree.links.new(tsocket, fsocket)
    if r_layer:
        r_layer.scene = sce
        r_layer.layer = context.view_layer.name
    sync_color_settings(sce, from_sce)
    copy_node_tree_drivers(from_sce, sce)


def reset_driver_with_scene_ref(an: bpy.types.AnimData, scenes: set[bpy.types.Scene]) -> None:
    if not an or not scenes:
        return

    def is_scene_ref(v, scenes_set):
        if v.type != "SINGLE_PROP":
            return False
        for t in v.targets:
            if t.id_type == "SCENE" and t.id in scenes_set:
                return True
        return False

    for d in an.drivers:
        for v in d.driver.variables:
            if not is_scene_ref(v, scenes):
                continue
            v.type = "CONTEXT_PROP"


def reload_drivers(an: bpy.types.AnimData) -> None:
    if not an:
        return
    from ...utils.node import remap_scene_compositor_driver_paths

    remap_scene_compositor_driver_paths(an)
    targets = [
        t
        for d in an.drivers
        for v in d.driver.variables
        for t in v.targets
        if v.type == "CONTEXT_PROP"
    ]
    for t in targets:
        t.data_path = t.data_path
