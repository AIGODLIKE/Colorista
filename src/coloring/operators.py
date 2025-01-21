import bpy
from ..preference import get_pref
from ...utils.logger import logger
from ...utils.common import get_resource_dir_locale, get_resource_dir
from ...utils.node import copy_node_properties
from ..i18n import _T
from .properties import Props
from .utils import set_viewport_shading
from pathlib import Path
from datetime import datetime


class ColoristaSavePreset(bpy.types.Operator):
    bl_idname = "colorista.save_preset"
    bl_description = "Save preset"
    bl_label = "Save preset"

    preset: bpy.props.StringProperty(default="")
    popup: bpy.props.BoolProperty(default=True)

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return context.scene.use_nodes

    def draw(self, context):
        layout = self.layout
        path = self.get_preset_path()
        layout.alert = True
        layout.label(text=_T("Overwrite preset: {}?").format(path.stem), icon="QUESTION")

    def get_preset_path(self):
        asset = bpy.context.scene.colorista_prop.asset
        preset_name = bpy.context.scene.colorista_prop.preset_save_name
        preset = Path(asset).with_suffix("").joinpath(preset_name)
        if self.preset:
            preset = Path(self.preset)
        return preset.with_suffix(".blend")

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        if not context.scene.colorista_prop.asset:
            return {"CANCELLED"}
        if not context.scene.colorista_prop.preset_save_name:
            return {"CANCELLED"}
        wm = context.window_manager
        path = self.get_preset_path()
        if path and path.exists() and self.popup:
            return wm.invoke_props_dialog(self, width=200)
        return self.execute(context)

    def copy_node(self, nf: bpy.types.Node, nt: bpy.types.Node):
        if nt.type == "GROUP":
            nt.node_tree = nf.node_tree
        for prop_name in nf.bl_rna.properties.keys():
            if nt.type == "GROUP" and prop_name == "node_tree":
                continue
            try:
                setattr(nt, prop_name, getattr(nf, prop_name))
            except AttributeError:
                pass
        for inp in nf.inputs:
            nt.inputs[inp.identifier].default_value = inp.default_value
        # nt.name = nf.name
        # nt.label = nf.label
        # nt.location = nf.location
        # nt.width = nf.width
        # nt.height = nf.height

    def copy_compositor(self, sf: bpy.types.Scene, st: bpy.types.Scene):
        st.use_nodes = True
        st.node_tree.nodes.clear()
        node_map = {}
        for node in sf.node_tree.nodes:
            new_node = st.node_tree.nodes.new(type=node.bl_idname)
            if new_node.type == "GROUP":
                new_node.node_tree = node.node_tree
            copy_node_properties(node, new_node)
            # new_node.name = node.name
            # new_node.label = node.label
            # new_node.location = node.location
            # new_node.width = node.width
            # new_node.height = node.height
            node_map[node.name] = new_node
        for link in sf.node_tree.links:
            fnode = node_map[link.from_node.name]
            tnode = node_map[link.to_node.name]
            fsocket = fnode.outputs[link.from_socket.identifier]
            tsocket = tnode.inputs[link.to_socket.identifier]
            st.node_tree.links.new(tsocket, fsocket)
        for node in st.node_tree.nodes:
            if node.type == "R_LAYERS":
                node.scene = None

    def copy_scene_settings(self, sf: bpy.types.Scene, st: bpy.types.Scene):
        try:
            st.display_settings.display_device = sf.display_settings.display_device
            st.view_settings.view_transform = sf.view_settings.view_transform
        except TypeError:
            pass

    def copy_scene(self, sf: bpy.types.Scene, st: bpy.types.Scene):
        self.copy_scene_settings(sf, st)
        self.copy_compositor(sf, st)

    def execute(self, context: bpy.types.Context):
        path = self.get_preset_path()
        self.preset = ""
        path.parent.mkdir(parents=True, exist_ok=True)
        sce = bpy.data.scenes.new(name="AC-Coloring")
        self.copy_scene(context.scene, sce)
        bpy.data.libraries.write(filepath=path.as_posix(), datablocks={sce})
        bpy.data.scenes.remove(sce)
        return {"FINISHED"}


class ColoristaDeletePreset(bpy.types.Operator):
    bl_idname = "colorista.delete_preset"
    bl_description = "Delete preset"
    bl_label = "Delete preset"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return context.scene.colorista_prop.asset and context.scene.colorista_prop.preset

    def draw(self, context: bpy.types.Context):
        layout = self.layout
        asset = Path(context.scene.colorista_prop.asset).stem
        preset = Path(context.scene.colorista_prop.preset).stem
        layout.alert = True
        layout.label(text=_T("Delete {}'s preset: {}?").format(asset, preset), icon="TRASH")

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        wm = bpy.context.window_manager
        return wm.invoke_props_dialog(self, width=200)

    def execute(self, context: bpy.types.Context):
        path = Path(context.scene.colorista_prop.preset)
        if not path or not path.exists():
            logger.error("Cannot find preset!")
            return {"FINISHED"}

        path.unlink()
        return {"FINISHED"}


class ColoristaSwitchDevice(bpy.types.Operator):
    bl_idname = "colorista.switch_device"
    bl_description = "Switch device"
    bl_label = "Switch device"

    def execute(self, context):
        render = context.scene.render
        if render.compositor_device == "GPU":
            render.compositor_device = "CPU"
        else:
            render.compositor_device = "GPU"
        return {"FINISHED"}


class ColoristaSwitchPrecision(bpy.types.Operator):
    bl_idname = "colorista.switch_precision"
    bl_description = "Switch precision"
    bl_label = "Switch precision"

    def execute(self, context):
        render = context.scene.render
        if render.compositor_precision == "AUTO":
            render.compositor_precision = "FULL"
        else:
            render.compositor_precision = "AUTO"
        return {"FINISHED"}


class CompositorNodeTreeImport(bpy.types.Operator):
    bl_idname = "colorista.compositor_nodetree_import"
    bl_description = "Import a node tree"
    bl_label = "Import a node tre"

    use_default: bpy.props.BoolProperty(default=False)
    preset: bpy.props.StringProperty(default="")
    no_cache: bpy.props.BoolProperty(default=False)

    def rsc_used(self, rsc) -> bool:
        return (rsc.users >= 1 and not rsc.use_fake_user) or rsc.users >= 2

    def _load_compositor_scene(self, path):
        for group in list(Props.loaded_node_groups):
            if self.rsc_used(group):
                continue
            Props.loaded_node_groups.discard(group)
            bpy.data.node_groups.remove(group)

        old_groups = set(bpy.data.node_groups)
        old_scenes = set(bpy.data.scenes)
        load_sce_name = "AC-Coloring"
        with bpy.data.libraries.load(path, link=False) as (df, dt):
            if load_sce_name not in df.scenes:
                load_sce_name = ""
            if not load_sce_name and df.scenes:
                load_sce_name = df.scenes[0]
            if not load_sce_name:  # 没有找到任何场景
                return
            dt.scenes.append(load_sce_name)
        new_scenes = set(bpy.data.scenes) - old_scenes
        new_groups = set(bpy.data.node_groups) - old_groups
        for ngroup in new_groups:
            Props.loaded_node_groups.add(ngroup)
        if not new_scenes:
            return
        return new_scenes

    def load_compositor_sce(self, preset):
        bpy.context.scene.use_nodes = True
        data_path = Path(preset)
        if not data_path.exists():
            return
        try:
            sce = self._load_compositor_scene(data_path.as_posix())
        except Exception:
            sce = None
        return sce

    def sync_settings(self, current_sce: bpy.types.Scene, loaded_sce: bpy.types.Scene):
        if not get_pref().use_asset_color_space_pref:
            return
        try:
            current_sce.display_settings.display_device = loaded_sce.display_settings.display_device
            current_sce.view_settings.view_transform = loaded_sce.view_settings.view_transform
        except TypeError:
            pass

    def load_compositor_node_tree(self, load_sces: set[bpy.types.Scene]):
        if not load_sces:
            return
        all_scenes = list(load_sces)
        load_sce = all_scenes[0]
        for ls in load_sces:
            if ls.name == "AC-Coloring":
                load_sce = ls
                break
        # 从 load_scene 复制 compositor节点树到当前场景
        sce = bpy.context.scene
        node_map = {}
        r_layer: bpy.types.CompositorNodeRLayers = None
        for nf in load_sce.node_tree.nodes:
            nt = sce.node_tree.nodes.new(type=nf.bl_idname)
            if nt.type == "GROUP":
                nt.node_tree = nf.node_tree
            if nf.type == "R_LAYERS":
                r_layer = nt
            copy_node_properties(nf, nt)
            node_map[nf.name] = nt
        for link in load_sce.node_tree.links:
            fnode = node_map[link.from_node.name]
            tnode = node_map[link.to_node.name]
            fsocket = fnode.outputs[link.from_socket.identifier]
            tsocket = tnode.inputs[link.to_socket.identifier]
            sce.node_tree.links.new(tsocket, fsocket)
        if r_layer:
            r_layer.scene = sce
            r_layer.layer = bpy.context.view_layer.name
        self.sync_settings(sce, load_sce)
        # 暂时不做缓存, 直接删除
        for ls in all_scenes:
            bpy.data.scenes.remove(ls)

    def enable_coloring_f(self, preset):
        sce = bpy.context.scene
        # 1. 如果开启缓存当前合成器 则 调用备份
        if get_pref().cache_current_compositor and not self.no_cache and sce.use_nodes:
            from .cache_history import update_history
            name = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            path = get_resource_dir() / f"cache/{name}.blend"
            bpy.ops.colorista.save_preset(preset=path.as_posix(), popup=False)
            update_history()

        # sce.view_settings.view_transform = "AgX"
        # 2. 判断软件版本如果是4.2默认合成模式切换到gpu
        if (4, 2) <= bpy.app.version <= (4, 3):
            sce.render.compositor_device = "GPU"
        # 4. 状态开启
        set_viewport_shading("ALWAYS")
        bpy.context.scene.use_nodes = True
        sce.node_tree.nodes.clear()  # 加载前清理节点树
        load_sce = self.load_compositor_sce(preset)
        self.load_compositor_node_tree(load_sce)
        if load_sce:
            logger.info(_T("Load Compositor: {}").format(preset))

    def execute(self, context: bpy.types.Context):
        preset = bpy.context.scene.colorista_prop.asset
        if self.use_default:
            preset = get_resource_dir_locale() / "Default/default.blend"
        if self.preset:
            preset = Path(self.preset)
            self.preset = ""
        self.enable_coloring_f(preset)
        return {'FINISHED'}


clss = (
    ColoristaSavePreset,
    ColoristaDeletePreset,
    ColoristaSwitchDevice,
    ColoristaSwitchPrecision,
    CompositorNodeTreeImport,
)

register, unregister = bpy.utils.register_classes_factory(clss)
