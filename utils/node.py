"""Compositor node-tree access and driver helpers."""

from __future__ import annotations

import bpy

from .compat import IS_BL5
from .logger import logger

# RNA props that are identity / structure — skip when copying node state.
_SKIP_NODE_PROPS = frozenset({
    "rna_type",
    "name",
    "label",
    "type",
    "bl_idname",
    "bl_label",
    "bl_description",
    "bl_icon",
    "bl_static_type",
    "bl_width_default",
    "bl_width_min",
    "bl_width_max",
    "bl_height_default",
    "bl_height_min",
    "bl_height_max",
    "internal_links",
    "inputs",
    "outputs",
    "dimensions",
    "width_hidden",
    "show_options",
    "show_preview",
    "show_texture",
    "use_custom_color",
    "color",
    "select",
    "hide",
    "mute",
    "parent",
})


def scene_uses_compositor(sce: bpy.types.Scene) -> bool:
    if IS_BL5:
        return sce.compositing_node_group is not None
    return bool(sce.use_nodes)


def copy_node_properties(nf: bpy.types.Node, nt: bpy.types.Node) -> None:
    """Copy node RNA + unlinked input defaults without forcing depsgraph updates.

    Callers must not invoke ``view_layer.update()`` per node — that is the
    dominant 4.x transfer cost.
    """
    if nt.type == "GROUP":
        nt.node_tree = nf.node_tree

    for prop_name in nf.bl_rna.properties.keys():
        if prop_name in _SKIP_NODE_PROPS:
            continue
        if nt.type == "GROUP" and prop_name == "node_tree":
            continue
        prop = nf.bl_rna.properties[prop_name]
        if prop.is_readonly:
            continue
        try:
            setattr(nt, prop_name, getattr(nf, prop_name))
        except (AttributeError, TypeError):
            pass

    # Location / size / flags after generic props so layout matches the asset.
    for attr in ("location", "width", "height", "label", "name", "mute", "hide"):
        try:
            setattr(nt, attr, getattr(nf, attr))
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


def copy_node_tree_drivers(sf: bpy.types.Scene, st: bpy.types.Scene) -> None:
    st_tree = get_comp_node_tree(st)
    sf_tree = get_comp_node_tree(sf)
    if not sf_tree or not sf_tree.animation_data:
        return
    if not st_tree.animation_data:
        st_tree.animation_data_create()
    for driver in sf_tree.animation_data.drivers:
        st_tree.animation_data.drivers.from_existing(src_driver=driver)
    remap_scene_compositor_driver_paths(st_tree.animation_data)


def ensure_comp_node_tree(sce: bpy.types.Scene) -> None:
    if IS_BL5:
        if sce.compositing_node_group:
            return
        tree = bpy.data.node_groups.new("Render Layers", "CompositorNodeTree")
        sce.compositing_node_group = tree
    else:
        sce.use_nodes = True


def get_comp_node_tree(sce: bpy.types.Scene) -> bpy.types.CompositorNodeTree:
    if IS_BL5:
        return sce.compositing_node_group
    return sce.node_tree


def remap_scene_compositor_driver_paths(an: bpy.types.AnimData) -> None:
    """Remap legacy scene.node_tree paths in drivers for Blender 5.x."""
    if not IS_BL5 or not an:
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
