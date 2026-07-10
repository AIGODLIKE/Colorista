import bpy
from datetime import datetime
from pathlib import Path

from ..i18n import _T
from ..preference import get_pref
from .state import loaded_node_groups
from .utils import set_viewport_shading
from ...utils.common import (
    get_default_preset_path,
    get_resource_dir,
    get_resource_dir_locale,
    get_user_cache_dir,
)
from ...utils.logger import logger
from ...utils.node import (
    copy_comp_node_tree,
    copy_node_properties,
    copy_node_tree_drivers,
    ensure_comp_node_tree,
    get_comp_node_tree,
    remap_scene_compositor_driver_paths,
    scene_uses_compositor,
)


def _poll_coloring_enabled(cls, context: bpy.types.Context) -> bool:
    try:
        if not context.scene.colorista_prop.enable_coloring:
            cls.poll_message_set(_T("Enable coloring first"))
            return False
    except AttributeError:
        cls.poll_message_set(_T("Enable coloring first"))
        return False
    return True


class ColoristaSavePreset(bpy.types.Operator):
    bl_idname = "wm.colorista_save_preset"
    bl_description = "Save preset"
    bl_label = "Save preset"
    bl_options = {'REGISTER', 'UNDO'}

    preset: bpy.props.StringProperty(default="")
    popup: bpy.props.BoolProperty(default=True)

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        if not scene_uses_compositor(context.scene):
            cls.poll_message_set(_T("Compositor nodes are not enabled for this scene"))
            return False
        return True

    def draw(self, context):
        layout = self.layout
        path = self.get_preset_path(context)
        layout.alert = True
        layout.label(text=_T("Overwrite preset: {}?").format(path.stem), icon="QUESTION")

    def get_preset_path(self, context: bpy.types.Context | None = None):
        context = context or bpy.context
        prop = context.scene.colorista_prop
        asset = prop.get_asset_path(context)
        preset_name = prop.preset_save_name
        preset = Path(asset).with_suffix("").joinpath(preset_name)
        if self.preset:
            preset = Path(self.preset)
        return preset.with_suffix(".blend")

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        if not context.scene.colorista_prop.get_asset_path(context):
            self.report({'ERROR'}, _T("No asset selected"))
            return {"CANCELLED"}
        if not context.scene.colorista_prop.preset_save_name:
            self.report({'ERROR'}, _T("Enter a preset name"))
            return {"CANCELLED"}
        wm = context.window_manager
        path = self.get_preset_path(context)
        if path and path.exists() and self.popup:
            return wm.invoke_props_dialog(self, width=200)
        return self.execute(context)

    def copy_drivers(self, sf: bpy.types.Scene, st: bpy.types.Scene):
        copy_node_tree_drivers(sf, st)

    def copy_compositor(self, sf: bpy.types.Scene, st: bpy.types.Scene):
        copy_comp_node_tree(sf, st)

    def copy_scene_settings(self, sf: bpy.types.Scene, st: bpy.types.Scene):
        try:
            st.display_settings.display_device = sf.display_settings.display_device
            st.view_settings.view_transform = sf.view_settings.view_transform
        except TypeError:
            pass

    def copy_scene(self, sf: bpy.types.Scene, st: bpy.types.Scene):
        self.copy_scene_settings(sf, st)
        self.copy_compositor(sf, st)
        self.copy_drivers(sf, st)

    def execute(self, context: bpy.types.Context):
        path = self.get_preset_path(context)
        self.preset = ""
        path.parent.mkdir(parents=True, exist_ok=True)
        sce = bpy.data.scenes.new(name="AC-Coloring")
        self.copy_scene(context.scene, sce)
        bpy.data.libraries.write(filepath=path.as_posix(), datablocks={sce})
        bpy.data.scenes.remove(sce)
        return {"FINISHED"}


class ColoristaDeletePreset(bpy.types.Operator):
    bl_idname = "wm.colorista_delete_preset"
    bl_description = "Delete preset"
    bl_label = "Delete preset"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        prop = context.scene.colorista_prop
        if not prop.get_asset_path(context):
            cls.poll_message_set(_T("Select an asset first"))
            return False
        if prop.get_preset_path(context) == prop.PRESET_NONE_ID:
            cls.poll_message_set(_T("Select a preset to delete"))
            return False
        return True

    def draw(self, context: bpy.types.Context):
        layout = self.layout
        asset = Path(context.scene.colorista_prop.get_asset_path(context)).stem
        preset = Path(context.scene.colorista_prop.get_preset_path(context)).stem
        layout.alert = True
        layout.label(text=_T("Delete {}'s preset: {}?").format(asset, preset), icon="TRASH")

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        return context.window_manager.invoke_props_dialog(self, width=200)

    def execute(self, context: bpy.types.Context):
        path = Path(context.scene.colorista_prop.get_preset_path(context))
        if not path or not path.exists():
            self.report({'ERROR'}, _T("Cannot find preset"))
            return {"CANCELLED"}

        path.unlink()
        return {"FINISHED"}


class ColoristaSwitchDevice(bpy.types.Operator):
    bl_idname = "wm.colorista_switch_device"
    bl_description = "Switch device"
    bl_label = "Switch device"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return _poll_coloring_enabled(cls, context)

    def execute(self, context):
        render = context.scene.render
        if render.compositor_device == "GPU":
            render.compositor_device = "CPU"
        else:
            render.compositor_device = "GPU"
        return {"FINISHED"}


class ColoristaSwitchPrecision(bpy.types.Operator):
    bl_idname = "wm.colorista_switch_precision"
    bl_description = "Switch precision"
    bl_label = "Switch precision"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return _poll_coloring_enabled(cls, context)

    def execute(self, context):
        render = context.scene.render
        if render.compositor_precision == "AUTO":
            render.compositor_precision = "FULL"
        else:
            render.compositor_precision = "AUTO"
        return {"FINISHED"}


class CompositorNodeTreeImport(bpy.types.Operator):
    bl_idname = "wm.colorista_compositor_import"
    bl_description = "Import a node tree"
    bl_label = "Import a node tree"
    bl_options = {'REGISTER', 'UNDO'}

    use_default: bpy.props.BoolProperty(default=False)
    preset: bpy.props.StringProperty(default="")
    no_cache: bpy.props.BoolProperty(default=False)

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return _poll_coloring_enabled(cls, context)

    def rsc_used(self, rsc) -> bool:
        try:
            return (rsc.users >= 1 and not rsc.use_fake_user) or rsc.users >= 2
        except ReferenceError:
            return False

    def _load_compositor_scene(self, path):
        for group in list(loaded_node_groups):
            if self.rsc_used(group):
                continue
            loaded_node_groups.discard(group)
            try:
                bpy.data.node_groups.remove(group)
            except ReferenceError:
                pass

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
            loaded_node_groups.add(ngroup)
        if not new_scenes:
            return
        return new_scenes

    def load_compositor_sce(self, preset, context: bpy.types.Context):
        ensure_comp_node_tree(context.scene)
        data_path = Path(preset)
        if not data_path.exists():
            return None
        try:
            sce = self._load_compositor_scene(data_path.as_posix())
        except Exception:
            sce = None
            logger.exception("Failed to load compositor scene from %s", data_path)
        return sce

    def sync_settings(self, current_sce: bpy.types.Scene, loaded_sce: bpy.types.Scene):
        pref = get_pref()
        if not pref or not pref.use_asset_color_space_pref:
            return
        try:
            current_sce.display_settings.display_device = loaded_sce.display_settings.display_device
            current_sce.view_settings.view_transform = loaded_sce.view_settings.view_transform
        except TypeError:
            pass

    def load_compositor_node_tree(self, from_sces: set[bpy.types.Scene], context: bpy.types.Context):
        if not from_sces:
            return
        all_scenes = list(from_sces)
        from_sce = all_scenes[0]
        for ls in from_sces:
            if ls.name == "AC-Coloring":
                from_sce = ls
                break
        sce = context.scene
        context.view_layer.update()
        node_map = {}
        r_layer: bpy.types.CompositorNodeRLayers = None
        from_tree = get_comp_node_tree(from_sce)
        to_tree = get_comp_node_tree(sce)
        if bpy.app.version >= (5, 0, 0):
            if not from_tree:
                return
            sce.compositing_node_group = from_tree.copy()
            to_tree = sce.compositing_node_group
            for n in to_tree.nodes:
                if n.type == "R_LAYERS":
                    r_layer = n
            if r_layer:
                r_layer.scene = sce
                r_layer.layer = context.view_layer.name
            self.sync_settings(sce, from_sce)
            return
        for nf in from_tree.nodes:
            if nf.bl_idname == "NodeUndefined":
                logger.error(f"NodeUndefined: {nf.name}")
                continue
            nt = to_tree.nodes.new(type=nf.bl_idname)
            if nt.type == "GROUP":
                nt.node_tree = nf.node_tree
            if nf.type == "R_LAYERS":
                r_layer = nt
            if nf.bl_idname == "CompositorNodeOutputFile":
                nt.file_slots.clear()
                for i, inp in enumerate(nf.inputs):
                    nt.file_slots.new(inp.identifier)
                    # _ = nt.inputs.new(inp.bl_idname, inp.name, identifier=inp.identifier)
                    nt.file_slots[i].path = nf.file_slots[i].path
                    nt.file_slots[i].use_node_format = nf.file_slots[i].use_node_format
            copy_node_properties(nf, nt)
            node_map[nf.name] = nt
        for link in from_tree.links:
            if link.from_node.bl_idname == "NodeUndefined" or link.to_node.bl_idname == "NodeUndefined":
                logger.error(f"NodeUndefined link: {link.from_node.name} -> {link.to_node.name}")
                continue
            if link.from_node.name not in node_map or link.to_node.name not in node_map:
                continue
            fnode = node_map[link.from_node.name]
            tnode = node_map[link.to_node.name]
            fsocket = fnode.outputs.get(link.from_socket.identifier)
            tsocket = tnode.inputs.get(link.to_socket.identifier)
            if not fsocket:
                logger.error(f"Socket not found: {link.from_socket.identifier}")
                continue
            if not tsocket:
                logger.error(f"Socket not found: {link.to_socket.identifier}")
                continue
            to_tree.links.new(tsocket, fsocket)
        if r_layer:
            r_layer.scene = sce
            r_layer.layer = context.view_layer.name
        self.sync_settings(sce, from_sce)
        self.copy_drivers(from_sce, sce)

    def enable_coloring_f(self, preset, context=None) -> bool:
        context = context or bpy.context
        sce = context.scene
        if preset is None:
            self.report({'ERROR'}, _T("No default preset found"))
            return False
        preset_path = Path(preset)
        if not preset_path.exists():
            self.report({'ERROR'}, _T("Preset not found: {}").format(preset_path))
            return False

        pref = get_pref()
        if pref and pref.cache_current_compositor and not self.no_cache and scene_uses_compositor(sce):
            from .cache_history import update_history

            name = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            path = get_user_cache_dir().joinpath(f"{name}.blend")
            try:
                bpy.ops.wm.colorista_save_preset(preset=path.as_posix(), popup=False)
            except Exception as e:
                logger.error(e)
            update_history(context)

        if (4, 2) <= bpy.app.version <= (4, 3):
            sce.render.compositor_device = "GPU"
        set_viewport_shading("ALWAYS", context)
        ensure_comp_node_tree(sce)
        sce_tree = get_comp_node_tree(sce)
        if sce_tree and bpy.app.version < (5, 0, 0):
            sce_tree.nodes.clear()
        old_nts = set(bpy.data.node_groups)
        load_sce = self.load_compositor_sce(preset, context)
        if not load_sce:
            self.report({'ERROR'}, _T("Failed to load compositor from {}").format(preset_path))
            return False
        new_nts = set(bpy.data.node_groups) - old_nts
        self.load_compositor_node_tree(load_sce, context)
        for nt in new_nts:
            self.reset_driver_with_scene_ref(nt.animation_data, load_sce)
        for ls in load_sce:
            bpy.data.scenes.remove(ls)
        logger.info(_T("Load Compositor: {}").format(preset))
        if sce_tree is not None:
            new_nts.add(sce_tree)
        for nt in new_nts:
            if nt is not None:
                self.reload_drivers(nt.animation_data)
        from .handler import update_node_group
        from .timer import update_custom_vt

        update_node_group(sce)
        update_custom_vt()
        return True

    def copy_drivers(self, sf: bpy.types.Scene, st: bpy.types.Scene):
        copy_node_tree_drivers(sf, st)

    def reset_driver_with_scene_ref(self, an: bpy.types.AnimData, scenes: set[bpy.types.Scene]):
        if not an or not scenes:
            return

        def is_scene_ref(v: bpy.types.ChannelDriverVariables, scenes: set[bpy.types.Scene]):
            if v.type != "SINGLE_PROP":
                return False
            for t in v.targets:
                if t.id_type == "SCENE" and t.id in scenes:
                    return True
            return False

        for d in an.drivers:
            for v in d.driver.variables:
                if not is_scene_ref(v, scenes):
                    continue
                v.type = "CONTEXT_PROP"

    def reload_drivers(self, an: bpy.types.AnimData):
        if not an:
            return
        remap_scene_compositor_driver_paths(an)
        targets = [t for d in an.drivers for v in d.driver.variables for t in v.targets if v.type == "CONTEXT_PROP"]
        for t in targets:
            t.data_path = t.data_path

    def execute(self, context: bpy.types.Context):
        prop = context.scene.colorista_prop
        preset = prop.get_asset_path(context)
        if self.use_default:
            preset = get_default_preset_path()
            if preset is None:
                self.report({'ERROR'}, _T("No default preset found"))
                return {"CANCELLED"}
        if self.preset:
            preset = Path(self.preset)
            self.preset = ""
        if not self.enable_coloring_f(preset, context):
            return {"CANCELLED"}
        return {"FINISHED"}


clss = (
    ColoristaSavePreset,
    ColoristaDeletePreset,
    ColoristaSwitchDevice,
    ColoristaSwitchPrecision,
    CompositorNodeTreeImport,
)

register, unregister = bpy.utils.register_classes_factory(clss)
