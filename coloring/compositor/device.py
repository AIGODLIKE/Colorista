"""Keep compositor processing devices in sync."""

from __future__ import annotations

import bpy


def set_compositor_device(
    render: bpy.types.RenderSettings,
    device: str,
) -> None:
    render.compositor_device = device
    render.compositor_denoise_device = device
