# type: ignore
from __future__ import annotations

import bpy

from ..coloring.constants import PROP_TCTX


def get_package() -> str:
    return __package__.rsplit(".", 1)[0]


def get_pref() -> Preferences | None:
    try:
        addon = bpy.context.preferences.addons.get(get_package())
        if addon is not None:
            return addon.preferences
    except Exception:
        pass
    return None


class Preferences(bpy.types.AddonPreferences):
    bl_idname = get_package()

    use_asset_color_space_pref: bpy.props.BoolProperty(
        default=False,
        name="Use Asset Color Management",
        translation_context=PROP_TCTX,
    )

    ui_icon_scale: bpy.props.FloatProperty(
        default=8,
        name="UI Icon Scale",
        min=1,
        max=20,
        translation_context=PROP_TCTX,
    )

    gizmo_offset: bpy.props.IntProperty(
        default=0,
        name="Gizmo Offset",
        min=0,
        max=100,
        translation_context=PROP_TCTX,
    )

    cache_current_compositor: bpy.props.BoolProperty(
        name="Cache Compositor",
        default=True,
        translation_context=PROP_TCTX,
    )

    def update_cache_current_cache_count(self, context):
        from ..coloring.history import apply_limit_change

        apply_limit_change(context)

    cache_current_cache_count: bpy.props.IntProperty(
        name="Cache Count",
        default=10,
        min=1,
        max=100,
        update=update_cache_current_cache_count,
        translation_context=PROP_TCTX,
    )

    cache_history_merge_seconds: bpy.props.IntProperty(
        name="History Merge Window",
        description="Within this many seconds, a new snapshot for the same asset replaces the latest one instead of adding another",
        default=30,
        min=0,
        max=600,
        translation_context=PROP_TCTX,
    )

    force_use_cpu_render_image: bpy.props.BoolProperty(
        name="Force CPU Compositor on Render",
        default=False,
        translation_context=PROP_TCTX,
    )

    main_node_group_name: bpy.props.StringProperty(
        name="Main Node Group Name",
        default="Basic adjustment nodes for colorists",
        translation_context=PROP_TCTX,
    )

    def update_enable_logging(self, context):
        from ..utils.logger import configure_logger

        configure_logger(self.enable_logging)

    enable_logging: bpy.props.BoolProperty(
        name="Enable Logging",
        default=False,
        update=update_enable_logging,
        translation_context=PROP_TCTX,
    )

    def update_presets_folder(self, context):
        from ..coloring import catalog

        catalog.invalidate()

    use_custom_presets_path: bpy.props.BoolProperty(
        name="Use Custom Presets Folder",
        description="Save user presets to a custom folder instead of the default",
        default=False,
        update=update_presets_folder,
        translation_context=PROP_TCTX,
    )

    presets_path: bpy.props.StringProperty(
        name="Custom Presets Folder",
        description="Folder for user-saved presets when custom path is enabled",
        subtype="DIR_PATH",
        default="",
        update=update_presets_folder,
        translation_context=PROP_TCTX,
    )

    def draw(self, context):
        from ..utils.paths import get_default_user_presets_folder, resolve_user_presets_root
        from ..coloring.config import get_config

        layout = self.layout
        layout.prop(self, "use_asset_color_space_pref")
        layout.prop(self, "gizmo_offset")
        layout.prop(self, "main_node_group_name")
        layout.prop(self, "ui_icon_scale")
        row = layout.row()
        row.prop(self, "cache_current_compositor", toggle=True)
        row.prop(self, "cache_current_cache_count")
        layout.prop(self, "cache_history_merge_seconds")

        layout.separator()

        box = layout.box()
        box.label(text="User presets")
        default_folder = get_default_user_presets_folder().as_posix()
        active_folder = resolve_user_presets_root(get_config().custom_presets_root).as_posix()
        row = box.row(align=True)
        row.label(text=default_folder, translate=False)
        from ..utils.icon import Icon

        row.operator(
            "wm.path_open", text="", icon=Icon.ui("FILE_FOLDER")
        ).filepath = active_folder
        box.prop(self, "use_custom_presets_path")
        if self.use_custom_presets_path:
            box.prop(self, "presets_path")

        layout.separator()

        layout.prop(self, "enable_logging")


def register():
    bpy.utils.register_class(Preferences)


def unregister():
    bpy.utils.unregister_class(Preferences)
