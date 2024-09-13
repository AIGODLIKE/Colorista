import bpy
from bpy.types import Context
# from .operators import TestOperator


class ColoringPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_coloring_panel"
    bl_label = "Coloring Panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Colorista"
    bl_translation_context = "ColoristaPanelTCTX"

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

    def draw(self, context):
        layout = self.layout
        # layout.operator(TestOperator.bl_idname)
        prop = bpy.context.scene.ac_prop
        layout.prop(prop, "enable_coloring", toggle=True)
        if not context.scene.ac_prop.enable_coloring:
            return
        if (4, 2) <= bpy.app.version <= (4, 3):
            col = layout.row().column()
            col.prop(context.scene.render, "compositor_device", text="Device")
            col.prop(context.scene.render, "compositor_precision", text="Precision")
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
            box.separator(type="LINE")
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
        layout = self.layout
        layout.operator("wm.url_open", text="", icon="URL").url = "https://github.com/AIGODLIKE/Colorista"
