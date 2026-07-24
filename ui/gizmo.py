import bpy

from ..coloring.compositor.viewport import toggle_viewport_shading
from ..coloring.constants import OPS_TCTX
from ..preferences import get_pref


def calc_widget_unit(context: bpy.types.Context) -> float:
    """Match Blender's U.widget_unit (interface_intern DPI math)."""
    system = context.preferences.system
    scale_factor = system.dpi / 72
    return round(18 * scale_factor + 0.00001) + (2 * system.pixel_size)


# Matches Blender view3d_gizmo_navigate.cc
GIZMO_OFFSET = 10.0
GIZMO_MINI_SIZE = 28.0
GIZMO_MINI_OFFSET = 2.0


def _visible_rect(context: bpy.types.Context):
    """Approximate ED_region_visible_rect for region-overlap layouts."""
    region = context.region
    xmin, ymin = 0.0, 0.0
    xmax = float(region.width)
    ymax = float(region.height)
    if not context.preferences.system.use_region_overlap:
        return xmin, ymin, xmax, ymax
    area = context.area
    if area is None:
        return xmin, ymin, xmax, ymax
    for r in area.regions:
        if r.width <= 0 or r.height <= 0:
            continue
        if r.type == "UI":
            xmax = min(xmax, float(r.x - region.x))
        elif r.type in {"HEADER", "TOOL_HEADER"}:
            local_y = float(r.y - region.y)
            if local_y + r.height >= region.height - 2:
                ymax = min(ymax, local_y)
        elif r.type == "FOOTER":
            local_y = float(r.y - region.y)
            if local_y <= 2:
                ymin = max(ymin, local_y + r.height)
    return xmin, ymin, xmax, ymax


def _icon_offset_from_axis(context: bpy.types.Context, icon_offset_mini: float) -> float:
    """Scaled pixel offset below the mini-axis / rotate gizmo (Blender 5.x)."""
    view_pref = context.preferences.view
    ui_scale = context.preferences.system.ui_scale
    show_rotate = view_pref.mini_axis_type == "GIZMO"
    icon_offset = ui_scale * (GIZMO_OFFSET + (
        view_pref.gizmo_size_navigate_v3d / 2.0 if show_rotate else 0.0
    ))

    if view_pref.mini_axis_type == "GIZMO":
        return icon_offset * 2.2
    if view_pref.mini_axis_type == "MINIMAL":
        return (calc_widget_unit(context) * 2.0) + (
            view_pref.mini_axis_size * ui_scale * 1.6
        )
    return icon_offset_mini * 0.75


def _navigate_button_slots(context: bpy.types.Context) -> int:
    """How many mini navigate buttons Blender currently shows."""
    view_pref = context.preferences.view
    space = context.space_data
    if not view_pref.show_navigate_ui:
        return 0
    if space is None or not getattr(space, "show_gizmo", True):
        return 0
    if not getattr(space, "show_gizmo_navigate", True):
        return 0

    rv3d = context.region_data
    slots = 0
    slots += 1  # zoom
    slots += 1  # pan
    slots += 1  # camera
    if rv3d is not None and getattr(rv3d, "view_perspective", None) != "CAMERA":
        slots += 1  # persp / ortho
    elif rv3d is not None and getattr(rv3d, "view_perspective", None) == "CAMERA":
        slots += 1  # camera lock
    return slots


class ColoristaGzOps(bpy.types.Operator):
    bl_idname = "wm.colorista_gz_switch_compositor"
    bl_label = "Toggle viewport compositor"
    bl_description = "Toggle viewport compositor for this window"
    bl_translation_context = OPS_TCTX
    # View setting only: an UNDO push here would add no-op steps to the stack.
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        if context.area.ui_type != "VIEW_3D":
            return False
        try:
            return context.scene.colorista_prop.enable_coloring
        except AttributeError:
            return False

    def execute(self, context):
        toggle_viewport_shading(context)
        return {"FINISHED"}


class ColoristaGizmos(bpy.types.GizmoGroup):
    bl_idname = "ColoristaGizmos"
    bl_label = "Colorista gizmo"
    bl_translation_context = OPS_TCTX
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_options = {"PERSISTENT", "SCALE", "SHOW_MODAL_ALL"}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        try:
            if not context.scene.colorista_prop.enable_coloring:
                return False
        except AttributeError:
            return False
        if context.space_data and context.space_data.region_quadviews:
            return context.region_data == context.space_data.region_quadviews[-1]
        return True

    def draw_prepare(self, context: bpy.types.Context):
        ui_scale = context.preferences.system.ui_scale
        icon_offset_mini = (GIZMO_MINI_SIZE + GIZMO_MINI_OFFSET) * ui_scale
        _xmin, _ymin, xmax, ymax = _visible_rect(context)

        icon_offset_from_axis = _icon_offset_from_axis(context, icon_offset_mini)
        slot = _navigate_button_slots(context) + 1
        pref = get_pref()
        if pref:
            slot += pref.gizmo_offset

        x = round(xmax - icon_offset_mini * 0.75)
        y = round(ymax - icon_offset_from_axis - icon_offset_mini * slot)
        self.gz.matrix_basis[0][3] = x
        self.gz.matrix_basis[1][3] = y

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

    def refresh(self, context: bpy.types.Context):
        self.gz.alpha = 0.5
        self.gz.color = 0.08, 0.08, 0.08
        self.gz.color_highlight = 0.317, 0.443, 0.682
        if context.space_data.shading.use_compositor == "ALWAYS":
            self.gz.alpha = 1
            self.gz.color = 0.317, 0.443, 0.682
            self.gz.color_highlight = 0.517, 0.643, 0.882


clss = (
    ColoristaGizmos,
    ColoristaGzOps,
)

register, unregister = bpy.utils.register_classes_factory(clss)
