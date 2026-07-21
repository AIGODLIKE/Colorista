import bpy

from ..coloring.compositor.ui_nodes import (
    draw_layout_panel,
    iter_ui_coloring_nodes,
    node_panel_id,
)
from ..coloring.constants import PANEL_TCTX
from ..utils.icon import Icon
from ..utils.node import get_comp_node_tree, scene_uses_compositor
from ..preferences import get_pref
from ..ops.operators import (
    ColoristaDeletePreset,
    ColoristaResetDefaults,
    ColoristaSavePreset,
    ColoristaSwitchAsset,
    ColoristaSwitchDevice,
    ColoristaSwitchPrecision,
    ColoristaSwitchPreset,
)


class ColoringPanel(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_colorista"
    bl_label = ""
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Colorista"
    bl_translation_context = PANEL_TCTX
    bl_options = {"HEADER_LAYOUT_EXPAND"}

    def draw(self, context):
        layout = self.layout
        prop = context.scene.colorista_prop
        if not prop.enable_coloring:
            col = layout.column()
            col.alert = True
            col.scale_y = 2
            col.prop(prop, "enable_coloring", icon=Icon.ui("PLAY"), toggle=True)
            return
        box = layout.box()
        self.show_assets(box, context)
        if not scene_uses_compositor(context.scene):
            return
        comp_tree = get_comp_node_tree(context.scene)
        if comp_tree is None:
            return
        first_panel = True
        for node, sockets in iter_ui_coloring_nodes(comp_tree):
            if len(node.inputs) == 0:
                continue
            panel_id = node_panel_id(node)
            header, body = draw_layout_panel(layout, panel_id, default_closed=False)
            if node.type != "GROUP":
                header.label(text=node.name)
            elif node.node_tree:
                header.label(text=node.node_tree.name)
            else:
                header.label(text=node.name)
            if first_panel:
                header.operator(
                    ColoristaResetDefaults.bl_idname,
                    text="",
                    icon=Icon.ui("FILE_REFRESH"),
                    emboss=False,
                )
                first_panel = False
            if not body:
                continue
            body.separator(type="LINE")
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
        row = self.layout.row(align=True)
        row.template_icon(icon_value=Icon.resource("color.png"))
        row.label(text="Coloring Panel", text_ctxt=PANEL_TCTX)

    def draw_header_preset(self, context: bpy.types.Context):
        row = self.layout.row(align=True)
        prop = context.scene.colorista_prop
        render = context.scene.render
        enabled = prop.enable_coloring

        row.alert = enabled
        row.prop(prop, "enable_coloring", toggle=True, icon=Icon.ui("QUIT"), text="")

        auto = render.compositor_precision == "AUTO"
        row.alert = enabled and not auto
        icon = Icon.resource("precision50.png" if auto else "precision100.png")
        row.operator(ColoristaSwitchPrecision.bl_idname, icon_value=icon, text="")

        gpu = render.compositor_device == "GPU"
        row.alert = enabled and gpu
        icon = Icon.resource("gpu.png" if gpu else "cpu.png")
        row.operator(ColoristaSwitchDevice.bl_idname, icon_value=icon, text="")

        row.alert = False
        pref = get_pref()
        if pref:
            row.alert = enabled and pref.use_asset_color_space_pref
            row.prop(pref, "use_asset_color_space_pref", text="", icon=Icon.ui("COLOR"))
            row.alert = enabled and pref.cache_current_compositor
            row.prop(pref, "cache_current_compositor", text="", icon=Icon.ui("DOCUMENTS"))
            row.alert = enabled and pref.force_use_cpu_render_image
            row.prop(
                pref,
                "force_use_cpu_render_image",
                text="",
                icon=Icon.ui("GEOMETRY_SET"),
            )
        row.alert = False
        row.popover("COLORISTA_PT_History", text="", icon=Icon.ui("RECOVER_LAST"))
        row.operator("wm.url_open", text="", icon=Icon.ui("URL")).url = (
            "https://github.com/AIGODLIKE/Colorista"
        )

    def show_assets(self, layout: bpy.types.UILayout, context: bpy.types.Context):
        prop = context.scene.colorista_prop
        row = layout.row(align=True)
        row.prop(prop, "pre_dir", text="")
        row.prop(prop, "asset", text="")
        row = layout.row()
        pref = get_pref()
        row.scale_y = pref.ui_icon_scale if pref else 8
        row.scale_x = 1.05
        op = row.operator(
            ColoristaSwitchAsset.bl_idname, text="", icon=Icon.ui("TRIA_LEFT")
        )
        op.direction = "PREV"
        sub = row.row()
        sub.scale_y = 0.17
        sub.template_icon_view(prop, "asset", show_labels=True, scale_popup=5)
        op = row.operator(
            ColoristaSwitchAsset.bl_idname, text="", icon=Icon.ui("TRIA_RIGHT")
        )
        op.direction = "NEXT"
        row = layout.row(align=True)
        op = row.operator(
            ColoristaSwitchPreset.bl_idname, text="", icon=Icon.ui("TRIA_LEFT")
        )
        op.direction = "PREV"
        row.prop(prop, "preset", text="")
        op = row.operator(
            ColoristaSwitchPreset.bl_idname, text="", icon=Icon.ui("TRIA_RIGHT")
        )
        op.direction = "NEXT"
        row = layout.row(align=True)
        row.prop(prop, "preset_save_name")
        row.operator(ColoristaSavePreset.bl_idname, text="", icon=Icon.ui("IMPORT"))
        row.operator(ColoristaDeletePreset.bl_idname, text="", icon=Icon.ui("CANCEL"))


class ColoristaHistoryPanel(bpy.types.Panel):
    bl_label = "Colorista History"
    bl_idname = "COLORISTA_PT_History"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_translation_context = PANEL_TCTX
    bl_options = {"INSTANCED"}

    def draw(self, context: bpy.types.Context):
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
