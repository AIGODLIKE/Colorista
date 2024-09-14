import bpy
from ...utils.logger import logger
from pathlib import Path

LANG_SUFFIXES = {
    "en_US": "EN",
    "zh_CN": "CN",
    "zh_HANS": "CN",
}


class Props(bpy.types.PropertyGroup):
    ovt = ""

    def _get_locale(self):
        if not bpy.context.preferences.view.use_translate_interface:
            return "en_US"
        return bpy.app.translations.locale

    def _get_locale_suffix(self):
        return LANG_SUFFIXES.get(self._get_locale(), "EN")

    def _sce_name(self):
        return f".AC-Coloring-{self._get_locale_suffix()}"

    def _load_compositor_scene(self, path):
        sce_name = self._sce_name()
        if sce_name not in bpy.data.scenes:
            with bpy.data.libraries.load(path, link=False) as (df, dt):
                if "AC-Coloring" not in df.scenes:
                    return None
                dt.scenes.append("AC-Coloring")
            sce = bpy.data.scenes["AC-Coloring"]
            sce.name = sce_name
        return bpy.data.scenes[sce_name]

    def load_compositor_sce(self):
        bpy.context.scene.use_nodes = True
        lang_suffix = self._get_locale_suffix()
        data_path = Path(__file__).parent.parent.parent / f"resource/data_{lang_suffix}.blend"
        if not data_path.exists():
            return
        return self._load_compositor_scene(data_path.as_posix())

    def load_compositor_node_tree(self, load_sce: bpy.types.Scene):
        if not load_sce:
            return
        # 从 load_scene 复制 compositor节点树到当前场景
        sce = bpy.context.scene
        sce.node_tree.nodes.clear()
        node_map = {}
        r_layer: bpy.types.CompositorNodeRLayers = None
        for node in load_sce.node_tree.nodes:
            new_node = sce.node_tree.nodes.new(type=node.bl_idname)
            if new_node.type == "GROUP":
                new_node.node_tree = node.node_tree
            if node.type == "R_LAYERS":
                r_layer = new_node
            new_node.name = node.name
            new_node.label = node.label
            new_node.location = node.location
            new_node.width = node.width
            new_node.height = node.height
            node_map[node.name] = new_node
        for link in load_sce.node_tree.links:
            fnode = node_map[link.from_node.name]
            tnode = node_map[link.to_node.name]
            fsocket = fnode.outputs[link.from_socket.identifier]
            tsocket = tnode.inputs[link.to_socket.identifier]
            sce.node_tree.links.new(tsocket, fsocket)
        r_layer.scene = sce
        r_layer.layer = bpy.context.view_layer.name

    def enable_coloring_f(self):
        sce = bpy.context.scene
        if sce.view_settings.view_transform != "AgX":
            Props.ovt = sce.view_settings.view_transform
        sce.view_settings.view_transform = "AgX"
        # 2. 判断软件版本如果是4.2默认合成模式切换到gpu
        if (4, 2) <= bpy.app.version <= (4, 3):
            sce.render.compositor_device = "GPU"
        # 4. 状态开启
        bpy.context.space_data.shading.use_compositor = "ALWAYS"
        bpy.context.scene.use_nodes = True
        load_sce = self.load_compositor_sce()
        self.load_compositor_node_tree(load_sce)

    def update_enable_coloring(self, context: bpy.types.Context):
        logger.info("调色开启" if self.enable_coloring else "调色关闭")
        if self.enable_coloring:
            self.enable_coloring_f()
        elif Props.ovt and context.scene.view_settings.view_transform == "AgX":
            context.scene.view_settings.view_transform = Props.ovt

    enable_coloring: bpy.props.BoolProperty(default=False,
                                            name="Enable Coloring",
                                            description="Enable Coloring",
                                            update=update_enable_coloring,
                                            translation_context="ColoristaTCTX")


@bpy.app.handlers.persistent
def reload_handler(sce):
    Props.ovt = ""


def coloring_checker():
    try:
        sce = bpy.context.scene
        if sce.view_settings.view_transform != "AgX" and sce.ac_prop.enable_coloring:
            sce.ac_prop.enable_coloring = False
        for area in bpy.context.screen.areas:
            if area.type != "VIEW_3D":
                continue
            area.tag_redraw()
    except Exception:
        pass
    return 0.1


bpy.app.timers.register(coloring_checker, first_interval=0.1, persistent=True)
bpy.app.handlers.load_post.append(reload_handler)
