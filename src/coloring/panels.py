import bpy
from .operators import (
    ColoristaSavePreset,
    ColoristaDeletePreset,
    ColoristaSwitchDevice,
    ColoristaSwitchPrecision,
)
from .cache_history import update_history
from ..preference import get_pref
from ...utils.icon import Icon
from ...utils.common import get_icons_dir
from ...utils.node import get_comp_node_tree, scene_uses_compositor
from .utils import node_panel_id, draw_layout_panel


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
        nodes: list[bpy.types.Node] = []
        for node in comp_tree.nodes:
            if node.type in {"VIEWER", "R_LAYERS"}:
                continue
            if not node.label:
                continue
            nodes.append(node)
        nodes.sort(key=lambda x: x.label)
        for node in nodes:
            if len(node.inputs) == 0:
                continue
            sockets = self.find_node_input(node)
            if len(sockets) == 0 and node.type == "GROUP":
                continue
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

    def find_node_input(self, node) -> list[bpy.types.NodeSocket]:
        sockets = []
        for inp in node.inputs:
            if inp.is_linked:
                continue
            if inp.enabled is False or inp.hide:
                continue
            if inp.type == "RGBA" and inp.hide_value:
                continue
            sockets.append(inp)
        return sockets

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
        row.prop(prop, "last_preset", text="", icon="TRIA_LEFT")
        row.prop(prop, "preset", text="")
        row.prop(prop, "next_preset", text="", icon="TRIA_RIGHT")

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
        sce = context.scene
        layout = self.layout
        layout.template_list("COLORISTA_HISTORY_UL_UIList", "", sce, "colorista_items", sce, "colorista_items_index")


clss = (
    ColoringPanel,
    ColoristaHistoryPanel,
)

register, unregister = bpy.utils.register_classes_factory(clss)
