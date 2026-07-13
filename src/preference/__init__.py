# type: ignore
from __future__ import annotations

import bpy

PROP_TCTX = "ColoristaTCTX"


def get_package() -> str:
    return __package__.rsplit(".", 2)[0]


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

    use_asset_color_space_pref: bpy.props.BoolProperty(default=False,
                                                       name="Use Asset Color Management",
                                                       translation_context=PROP_TCTX)

    ui_icon_scale: bpy.props.FloatProperty(default=8,
                                           name="UI Icon Scale",
                                           min=1,
                                           max=20,
                                           translation_context=PROP_TCTX)

    gizmo_offset: bpy.props.IntProperty(default=0,
                                        name="Gizmo Offset",
                                        min=0,
                                        max=100,
                                        translation_context=PROP_TCTX)

    cache_current_compositor: bpy.props.BoolProperty(name="Cache Compositor",
                                                     default=True,
                                                     translation_context=PROP_TCTX)

    def update_cache_current_cache_count(self, context):
        from ..coloring.cache_history import update_history
        update_history()

    cache_current_cache_count: bpy.props.IntProperty(name="Cache Count",
                                                     default=10,
                                                     min=1,
                                                     max=100,
                                                     update=update_cache_current_cache_count,
                                                     translation_context=PROP_TCTX)

    force_use_cpu_render_image: bpy.props.BoolProperty(name="Force Use CPU Render Image", default=False,
                                                       translation_context=PROP_TCTX)

    main_node_group_name: bpy.props.StringProperty(
        name="Main Node Group Name",
        default="Basic adjustment nodes for colorists",
        translation_context=PROP_TCTX,
    )

    def update_enable_logging(self, context):
        from ...utils.logger import configure_logger
        configure_logger(self.enable_logging)

    enable_logging: bpy.props.BoolProperty(name="Enable Logging", default=False,
                                           update=update_enable_logging,
                                           translation_context=PROP_TCTX)

    use_custom_presets_path: bpy.props.BoolProperty(
        name="Use custom presets folder",
        description="Save user presets to a custom folder instead of the default",
        default=False,
        translation_context=PROP_TCTX,
    )

    presets_path: bpy.props.StringProperty(
        name="Custom presets folder",
        description="Folder for user-saved presets when custom path is enabled",
        subtype="DIR_PATH",
        default="",
        translation_context=PROP_TCTX,
    )

    def draw(self, context):
        from ...utils.common import get_default_user_presets_folder, resolve_user_presets_root

        layout = self.layout
        layout.prop(self, "use_asset_color_space_pref")
        layout.prop(self, "gizmo_offset")
        layout.prop(self, "main_node_group_name")
        layout.prop(self, "ui_icon_scale")
        row = layout.row()
        row.prop(self, "cache_current_compositor", toggle=True)
        row.prop(self, "cache_current_cache_count")

        layout.separator()

        box = layout.box()
        box.label(text="User presets")
        default_folder = get_default_user_presets_folder().as_posix()
        active_folder = resolve_user_presets_root().as_posix()
        row = box.row(align=True)
        row.label(text=default_folder, translate=False)
        row.operator("wm.path_open", text="", icon="FILE_FOLDER").filepath = active_folder
        box.prop(self, "use_custom_presets_path")
        if self.use_custom_presets_path:
            box.prop(self, "presets_path")

        layout.separator()

        layout.prop(self, "enable_logging")


def register():
    bpy.utils.register_class(Preferences)


def unregister():
    bpy.utils.unregister_class(Preferences)
