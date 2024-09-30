from __future__ import annotations
import bpy

PROP_TCTX = "ColoristaTCTX"


def get_package() -> str:
    return ".".join(__package__.split(".")[:-2])


def get_pref() -> Preferences:
    return bpy.context.preferences.addons[get_package()].preferences


class Preferences(bpy.types.AddonPreferences):
    bl_idname = get_package()

    use_asset_color_space_pref: bpy.props.BoolProperty(default=True,
                                                       name="Use Asset Color Space",
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

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "use_asset_color_space_pref")
        layout.prop(self, "gizmo_offset")
        layout.prop(self, "ui_icon_scale")
        row = layout.row()
        row.prop(self, "cache_current_compositor", toggle=True)
        row.prop(self, "cache_current_cache_count")


def register():
    bpy.utils.register_class(Preferences)


def unregister():
    bpy.utils.unregister_class(Preferences)
