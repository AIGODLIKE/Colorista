import bpy
from bpy.types import Context
from .utils import toggle_viewport_shading
from ..preference import get_pref


def calc_pixel_size():
    context = bpy.context
    dpi = context.preferences.system.dpi
    ui_line_width = context.preferences.system.ui_line_width
    pixelsize = max(1, int(dpi / 64))
    pixelsize = max(1, pixelsize + ui_line_width)
    return pixelsize


def calc_widget_unit():
    context = bpy.context
    pixel_size = bpy.context.preferences.system.pixel_size
    scale_factor = context.preferences.system.dpi / 72
    widget_unit = round(18 * scale_factor + 0.00001) + (2 * pixel_size)
    return widget_unit


def calc_icon_offset_from_axis():
    context = bpy.context
    view_pref = context.preferences.view
    pixel_size = context.preferences.system.pixel_size
    ui_scale = context.preferences.system.ui_scale
    widget_unit = calc_widget_unit()
    offset = (widget_unit * 2.5) + (view_pref.mini_axis_size * pixel_size * 2)
    return offset / ui_scale


class ColoristaGzOps(bpy.types.Operator):
    bl_idname = "colorista.gz_switch_compositor"
    bl_label = "Switch View Compositor"
    bl_description = "Switch View Compositor"

    @classmethod
    def poll(cls, context):
        return context.area.ui_type == "VIEW_3D"

    def execute(self, context):
        toggle_viewport_shading()
        return {'FINISHED'}


class ColoristaGizmos(bpy.types.GizmoGroup):
    bl_idname = "ColoristaGizmos"
    bl_label = "Colorista gizmos"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_options = {"PERSISTENT", "SCALE", "SHOW_MODAL_ALL"}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return True

    def get_n_panel_width(self, context: bpy.types.Context):
        for region in context.area.regions:
            if region.type == "UI":
                return region.width
        return 0

    def get_herder_height(self, context: bpy.types.Context):
        for region in context.area.regions:
            if region.type == "HEADER":
                return region.height
        return 0

    def get_navitation_height(self, context: bpy.types.Context):
        # 计算顶部控件高度
        ui_scale = context.preferences.system.ui_scale
        h = 0
        icon_offset_mini = 28 + 2
        icon_offset_from_axis = 0
        view_pref = context.preferences.view
        icon_offset = view_pref.gizmo_size_navigate_v3d / 2.0 + 10.0
        if view_pref.mini_axis_type == "MINIMAL":
            icon_offset_from_axis = calc_icon_offset_from_axis()
        elif view_pref.mini_axis_type == "GIZMO":
            icon_offset_from_axis = icon_offset * 2.1
        else:
            icon_offset_from_axis = icon_offset_mini * 0.75

        h = icon_offset_from_axis
        # 计算按钮控件高度: 当显示gizmo控件 且 显示漫游控件ui
        if bpy.context.space_data.show_gizmo_navigate and view_pref.show_navigate_ui:
            h += icon_offset_mini * 4
        h += icon_offset_mini * get_pref().gizmo_offset
        return h * ui_scale

    def draw_prepare(self, context: bpy.types.Context):
        ui_scale = context.preferences.system.ui_scale
        region = context.region

        x = region.width - (28 + 2) * 0.75 * ui_scale
        y = region.height

        if context.preferences.system.use_region_overlap:
            x -= self.get_n_panel_width(context)
            y -= self.get_herder_height(context) * 2
        y -= self.get_navitation_height(context)
        self.gz.matrix_basis[0][3] = x
        self.gz.matrix_basis[1][3] = y

        context.area.tag_redraw()

    def setup(self, context):
        gz = self.gizmos.new("GIZMO_GT_button_2d")
        gz.bl_idname = "ColoristaButton"
        gz.icon = "AREA_SWAP"
        gz.draw_options = {"BACKDROP", "OUTLINE"}
        gz.target_set_operator(ColoristaGzOps.bl_idname)
        gz.alpha = 0.5
        gz.scale_basis = (80 * 0.35) / 2
        gz.show_drag = False
        self.gz = gz

    def refresh(self, context: Context):
        self.gz.alpha = 0.5
        self.gz.color = 0.08, 0.08, 0.08
        self.gz.color_highlight = 0.317, 0.443, 0.682  # 0.3176470696926117, 0.4431372880935669, 0.6823529601097107
        if context.space_data.shading.use_compositor == "ALWAYS":
            self.gz.alpha = 1
            self.gz.color = 0.317, 0.443, 0.682
            self.gz.color_highlight = 0.517, 0.643, 0.882
        context.area.tag_redraw()


clss = (
    ColoristaGizmos,
    ColoristaGzOps,
)

register, unregister = bpy.utils.register_classes_factory(clss)
