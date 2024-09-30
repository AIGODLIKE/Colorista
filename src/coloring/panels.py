import bpy
from bpy.types import Context
from .operators import ColoristaSavePreset, ColoristaDeletePreset, ColoristaSwitchDevice, ColoristaSwitchPrecision
from ..preference import get_pref
from ...utils.icon import Icon
from ...utils.common import grd


class ColoringPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_coloring_panel"
    bl_label = "Coloring Panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Colorista"
    bl_translation_context = "ColoristaPanelTCTX"

    def draw(self, context):
        layout = self.layout
        prop = bpy.context.scene.colorista_prop
        if not context.scene.colorista_prop.enable_coloring:
            col = layout.column()
            col.alert = True
            col.scale_y = 2
            col.prop(prop, "enable_coloring", icon="PLAY", toggle=True)
            return
        box = layout.box()
        self.show_assets(box)
        if not context.scene.use_nodes:
            return
        nodes: list[bpy.types.Node] = []
        for node in context.scene.node_tree.nodes:
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
            box = layout.box()
            row = box.row()
            row.prop(node, "ac_expand", icon="TRIA_DOWN" if node.ac_expand else "TRIA_RIGHT", text="", emboss=False)
            if node.type != "GROUP":
                row.label(text=node.name)
            elif node.node_tree:
                row.label(text=node.node_tree.name)
            if node.ac_expand is False:
                continue
            if bpy.app.version >= (4, 2):
                box.separator(type="LINE")
            else:
                box.separator()
            node.draw_buttons(context, box)
            bbox = box
            for inp in sockets:
                if inp.name.startswith("——"):
                    bbox = box.box()
                    row = bbox.row()
                    row.alert = True
                    row.alignment = "CENTER"
                    row.label(text=inp.name)
                    continue
                bbox.template_node_view(context.scene.node_tree, node, inp)

    def draw_header(self, context: Context):
        self.layout.template_icon(icon_value=Icon.reg_icon(grd() / "icons/color.png"))

    def draw_header_preset(self, context: Context):
        layout = self.layout.row(align=True)
        row = layout.row(align=True)
        prop = bpy.context.scene.colorista_prop
        render = context.scene.render

        row.alert = prop.enable_coloring
        row.prop(prop, "enable_coloring", toggle=True, icon="QUIT", text="")

        if (4, 2) <= bpy.app.version:
            auto = render.compositor_precision == "AUTO"
            row.alert = not auto
            ipath = grd() / "icons"
            icon = Icon.reg_icon(ipath / "precision50.png") if auto else Icon.reg_icon(ipath / "precision100.png")
            row.operator(ColoristaSwitchPrecision.bl_idname, icon_value=icon, text="")

            gpu = render.compositor_device == "GPU"
            row.alert = gpu
            icon = Icon.reg_icon(ipath / "gpu.png") if gpu else Icon.reg_icon(ipath / "cpu.png")
            row.operator(ColoristaSwitchDevice.bl_idname, icon_value=icon, text="")

            row.alert = False
        row.alert = get_pref().use_asset_color_space_pref
        row.prop(get_pref(), "use_asset_color_space_pref", text="", icon="FILE_REFRESH")
        row.alert = get_pref().cache_current_compositor
        row.prop(get_pref(), "cache_current_compositor", text="", icon="DOCUMENTS")
        row.alert = False
        row.popover(ColoristaHistoryPanel.bl_idname, text="", icon="RECOVER_LAST")
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

    def show_assets(self, layout: bpy.types.UILayout):
        row = layout.row(align=True)
        sce = bpy.context.scene
        prop = sce.colorista_prop
        row.prop(prop, "pre_dir", text="")
        row.prop(prop, "asset", text="")
        row = layout.row()
        row.scale_y = get_pref().ui_icon_scale
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
    bl_region_type = "HUD"  # hack hide panel

    def draw(self, context: Context):
        sce = bpy.context.scene
        layout = self.layout
        layout.template_list("COLORISTA_HISTORY_UL_UIList", "", sce, "colorista_items", sce, "colorista_items_index")


clss = (
    ColoringPanel,
    ColoristaHistoryPanel,
)

register, unregister = bpy.utils.register_classes_factory(clss)
