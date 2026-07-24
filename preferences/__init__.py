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
        name="Cache Compositor State",
        default=True,
        translation_context=PROP_TCTX,
    )

    def update_cache_current_cache_count(self, context):
        from ..coloring.history import apply_limit_change

        apply_limit_change(context)

    cache_current_cache_count: bpy.props.IntProperty(
        name="History Cache Limit",
        default=10,
        min=1,
        max=100,
        update=update_cache_current_cache_count,
        translation_context=PROP_TCTX,
    )

    cache_history_merge_seconds: bpy.props.IntProperty(
        name="History Merge Interval",
        description="Changes to the same asset made less than this many seconds apart are combined into one history entry; set to 0 to keep each change as a separate entry",
        default=5,
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
        from ..utils.icon import Icon

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        box = layout.box()
        box.label(text="General", icon=Icon.ui("PREFERENCES"))
        col = box.column(align=True)
        col.prop(self, "use_asset_color_space_pref")
        col.prop(self, "gizmo_offset")
        col.prop(self, "ui_icon_scale")

        box = layout.box()
        box.label(text="Compositor", icon=Icon.ui("NODE_COMPOSITING"))
        col = box.column(align=True)
        col.prop(self, "force_use_cpu_render_image")

        box = layout.box()
        box.label(text="History", icon=Icon.ui("RECOVER_LAST"))
        col = box.column(align=True)
        col.prop(self, "cache_current_compositor")
        history_col = col.column(align=True)
        history_col.active = self.cache_current_compositor
        history_col.prop(self, "cache_current_cache_count")
        history_col.prop(self, "cache_history_merge_seconds")

        box = layout.box()
        box.label(text="User Presets", icon=Icon.ui("PRESET"))
        col = box.column(align=True)
        col.prop(self, "use_custom_presets_path")
        custom_path_col = col.column(align=True)
        custom_path_col.active = self.use_custom_presets_path
        custom_path_col.prop(self, "presets_path")

        default_folder = get_default_user_presets_folder().as_posix()
        active_folder = resolve_user_presets_root(get_config().custom_presets_root).as_posix()
        folder = active_folder if self.use_custom_presets_path else default_folder
        row = col.row(align=True)
        row.label(text=folder, translate=False)
        row.operator(
            "wm.path_open", text="", icon=Icon.ui("FILE_FOLDER")
        ).filepath = active_folder

        box = layout.box()
        box.label(text="Advanced", icon=Icon.ui("SETTINGS"))
        col = box.column(align=True)
        col.prop(self, "main_node_group_name")
        col.prop(self, "enable_logging")


def register():
    bpy.utils.register_class(Preferences)


def unregister():
    bpy.utils.unregister_class(Preferences)
