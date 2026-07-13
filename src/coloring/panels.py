import bpy
from .operators import (
    ColoristaSavePreset,
    ColoristaDeletePreset,
    ColoristaSwitchPreset,
    ColoristaSwitchDevice,
    ColoristaSwitchPrecision,
)
from .cache_history import update_history
from ..preference import get_pref
from ...utils.icon import Icon
from ...utils.common import get_icons_dir
from ...utils.node import get_comp_node_tree, scene_uses_compositor
from .utils import (
    draw_layout_panel,
    find_ui_node_inputs,
    iter_ui_coloring_nodes,
    node_panel_id,
)


class ColoringPanel(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_colorista"
    bl_label = "Coloring Panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Colorista"
    bl_translation_context = "ColoristaPanelTCTX"

    def draw(self, context):
        layout = self.layout
        prop = context.scene.colorista_prop
        if not prop.enable_coloring:
            col = layout.column()
            col.alert = True
            col.scale_y = 2
            col.prop(prop, "enable_coloring", icon="PLAY", toggle=True)
            return
        box = layout.box()
        self.show_assets(box, context)
        if not scene_uses_compositor(context.scene):
            return
        comp_tree = get_comp_node_tree(context.scene)
        if comp_tree is None:
            return
        for node in iter_ui_coloring_nodes(comp_tree):
            if len(node.inputs) == 0:
                continue
            sockets = find_ui_node_inputs(node)
            panel_id = node_panel_id(comp_tree, node)
            header, body = draw_layout_panel(layout, panel_id, default_closed=False)
            if node.type != "GROUP":
                header.label(text=node.name)
            elif node.node_tree:
                header.label(text=node.node_tree.name)
            else:
                header.label(text=node.name)
            if not body:
                continue
            if bpy.app.version >= (4, 2):
                body.separator(type="LINE")
            else:
                body.separator()
            node.draw_buttons(context, body)
            bbox = body
            for inp in sockets:
                if inp.name.startswith("——"):
                    bbox = body.box()
                    row = bbox.row()
                    row.alert = True
                    row.alignment = "CENTER"
                    row.label(text=inp.name)
                    continue
                bbox.template_node_view(comp_tree, node, inp)

    def draw_header(self, context: bpy.types.Context):
        self.layout.template_icon(icon_value=Icon.reg_icon(get_icons_dir().joinpath("color.png")))

    def draw_header_preset(self, context: bpy.types.Context):
        layout = self.layout.row(align=True)
        row = layout.row(align=True)
        prop = context.scene.colorista_prop
        render = context.scene.render

        row.alert = prop.enable_coloring
        row.prop(prop, "enable_coloring", toggle=True, icon="QUIT", text="")

        if (4, 2) <= bpy.app.version:
            auto = render.compositor_precision == "AUTO"
            row.alert = not auto
            ipath = get_icons_dir()
            icon = Icon.reg_icon(ipath.joinpath("precision50.png")) if auto else Icon.reg_icon(ipath.joinpath("precision100.png"))
            row.operator(ColoristaSwitchPrecision.bl_idname, icon_value=icon, text="")

            gpu = render.compositor_device == "GPU"
            row.alert = gpu
            icon = Icon.reg_icon(ipath.joinpath("gpu.png")) if gpu else Icon.reg_icon(ipath.joinpath("cpu.png"))
            row.operator(ColoristaSwitchDevice.bl_idname, icon_value=icon, text="")

            row.alert = False
        pref = get_pref()
        if pref:
            row.alert = pref.use_asset_color_space_pref
            row.prop(pref, "use_asset_color_space_pref", text="", icon="FILE_REFRESH")
            row.alert = pref.cache_current_compositor
            row.prop(pref, "cache_current_compositor", text="", icon="DOCUMENTS")
            row.alert = pref.force_use_cpu_render_image
            row.prop(pref, "force_use_cpu_render_image", text="", icon="GEOMETRY_SET")
        row.alert = False
        row.popover("COLORISTA_PT_History", text="", icon="RECOVER_LAST")
        row.operator("wm.url_open", text="", icon="URL").url = "https://github.com/AIGODLIKE/Colorista"

    def show_assets(self, layout: bpy.types.UILayout, context: bpy.types.Context):
        prop = context.scene.colorista_prop
        row = layout.row(align=True)
        row.prop(prop, "pre_dir", text="")
        row.prop(prop, "asset", text="")
        row = layout.row()
        pref = get_pref()
        row.scale_y = pref.ui_icon_scale if pref else 8
        row.scale_x = 1.05
        row.prop(prop, "last_asset", text="", icon="TRIA_LEFT")
        sub = row.row()
        sub.scale_y = 0.17
        sub.template_icon_view(prop, "asset", show_labels=True, scale_popup=5)
        row.prop(prop, "next_asset", text="", icon="TRIA_RIGHT")
        row = layout.row(align=True)
        op = row.operator(ColoristaSwitchPreset.bl_idname, text="", icon="TRIA_LEFT")
        op.direction = "PREV"
        row.prop(prop, "preset", text="")
        op = row.operator(ColoristaSwitchPreset.bl_idname, text="", icon="TRIA_RIGHT")
        op.direction = "NEXT"
        row = layout.row(align=True)
        row.prop(prop, "preset_save_name")
        row.operator(ColoristaSavePreset.bl_idname, text="", icon="IMPORT")
        row.operator(ColoristaDeletePreset.bl_idname, text="", icon="CANCEL")


class ColoristaHistoryPanel(bpy.types.Panel):
    bl_label = "Colorista History"
    bl_idname = "COLORISTA_PT_History"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_options = {"INSTANCED"}

    def draw(self, context: bpy.types.Context):
        update_history(context)
        prop = context.scene.colorista_prop
        layout = self.layout
        layout.template_list(
            "COLORISTA_HISTORY_UL_UIList",
            "",
            prop,
            "history_items",
            prop,
            "history_items_index",
        )


clss = (
    ColoringPanel,
    ColoristaHistoryPanel,
)

register, unregister = bpy.utils.register_classes_factory(clss)
