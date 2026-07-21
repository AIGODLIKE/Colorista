"""Compositor node-tree access and driver helpers."""

from __future__ import annotations

import bpy


def scene_uses_compositor(sce: bpy.types.Scene) -> bool:
    return sce.compositing_node_group is not None


def get_comp_node_tree(sce: bpy.types.Scene) -> bpy.types.CompositorNodeTree:
    return sce.compositing_node_group


def remap_scene_compositor_driver_paths(an: bpy.types.AnimData) -> None:
    """Remap legacy ``scene.node_tree`` driver paths from 4.x-era assets."""
    if not an:
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
