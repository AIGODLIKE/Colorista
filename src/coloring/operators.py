import bpy
from datetime import datetime
from pathlib import Path

from ..i18n import _T
from ..preference import get_pref
from .serialize import (
    apply_scene_preset,
    read_preset_json,
    resolve_asset_path,
    save_compositor_values_json,
)
from . import state as coloring_state
from .state import loaded_node_groups, preset_key, set_loaded_asset, set_loaded_preset
from .utils import set_viewport_shading
from ...utils.common import (
    get_default_preset_path,
    get_user_cache_dir,
    get_asset_preset_dir,
    is_under_user_presets_root,
    is_user_preset_file,
)
from ...utils.logger import logger
from ...utils.node import (
    copy_node_properties,
    copy_node_tree_drivers,
    ensure_comp_node_tree,
    get_comp_node_tree,
    remap_scene_compositor_driver_paths,
    scene_uses_compositor,
)
from ...utils.timer import Timer

# Coalesce deferred imports from EnumProperty update callbacks.
_pending_import_kwargs: dict | None = None
_import_scheduled = False


def schedule_import_compositor(**kwargs) -> None:
    """Defer import_compositor out of RNA property updates (avoids nested ops / write crashes)."""
    global _pending_import_kwargs, _import_scheduled
    _pending_import_kwargs = kwargs
    if _import_scheduled:
        return
    _import_scheduled = True
    Timer.put(_flush_scheduled_import)


def _flush_scheduled_import() -> None:
    global _pending_import_kwargs, _import_scheduled
    _import_scheduled = False
    kwargs = _pending_import_kwargs
    _pending_import_kwargs = None
    if kwargs is None:
        return
    try:
        import_compositor(bpy.context, **kwargs)
    except Exception:
        logger.exception("Deferred compositor import failed")


def _current_asset_path(context: bpy.types.Context) -> Path | None:
    try:
        asset = context.scene.colorista_prop.get_asset_path(context)
    except AttributeError:
        return None
    if not asset:
        return None
    path = Path(asset)
    return path if path.exists() else None


class CompositorImportHelper:
    """Plain helper for compositor import. Do not instantiate bpy.types.Operator."""

    def __init__(self, *, no_cache: bool = False, reporter=None):
        self.no_cache = no_cache
        self._reporter = reporter

    def report(self, type_set, message: str) -> None:
        if self._reporter is not None:
            self._reporter(type_set, message)
            return
        if "INFO" in type_set:
            logger.info("%s", message)
        else:
            logger.error("%s", message)

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
            if not load_sce_name:
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
            # Assign the loaded tree directly. .copy() would create Foo.001 / Group.001
            # on every topology load and break stable panel ids / group names.
            old_tree = sce.compositing_node_group
            sce.compositing_node_group = from_tree
            to_tree = sce.compositing_node_group
            if old_tree is not None and old_tree != to_tree:
                try:
                    if old_tree.users == 0:
                        bpy.data.node_groups.remove(old_tree)
                except ReferenceError:
                    pass
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

    def _cache_history_json(self, context: bpy.types.Context, sce: bpy.types.Scene) -> None:
        pref = get_pref()
        if not pref or not pref.cache_current_compositor or self.no_cache:
            return
        if not scene_uses_compositor(sce):
            return
        asset_path = _current_asset_path(context)
        if asset_path is None and coloring_state.last_loaded_asset:
            asset_path = Path(coloring_state.last_loaded_asset)
        if asset_path is None:
            return
        from .cache_history import update_history

        name = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        path = get_user_cache_dir().joinpath(f"{name}.json")
        try:
            save_compositor_values_json(path, sce, asset_path)
        except Exception as e:
            logger.error(e)
        update_history(context)

    def _finish_load(self, sce: bpy.types.Scene, label: str) -> bool:
        from .handler import update_node_group
        from .timer import update_custom_vt

        logger.info(_T("Load Compositor: {}").format(label))
        update_node_group(sce)
        update_custom_vt()
        return True

    def _load_blend_topology(self, blend_path: Path, context: bpy.types.Context) -> bool:
        sce = context.scene
        if (4, 2) <= bpy.app.version <= (4, 3):
            sce.render.compositor_device = "GPU"
        set_viewport_shading("ALWAYS", context)
        ensure_comp_node_tree(sce)
        sce_tree = get_comp_node_tree(sce)
        if sce_tree and bpy.app.version < (5, 0, 0):
            sce_tree.nodes.clear()
        old_nts = set(bpy.data.node_groups)
        load_sce = self.load_compositor_sce(blend_path, context)
        if not load_sce:
            self.report({'ERROR'}, _T("Failed to load compositor from {}").format(blend_path))
            return False
        new_nts = set(bpy.data.node_groups) - old_nts
        self.load_compositor_node_tree(load_sce, context)
        for nt in new_nts:
            self.reset_driver_with_scene_ref(nt.animation_data, load_sce)
        for ls in load_sce:
            bpy.data.scenes.remove(ls)
        current_tree = get_comp_node_tree(sce)
        if current_tree is not None:
            new_nts.add(current_tree)
        for nt in list(new_nts):
            try:
                if nt is not None:
                    self.reload_drivers(nt.animation_data)
            except ReferenceError:
                continue
        set_loaded_asset(blend_path)
        return True

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

        self._cache_history_json(context, sce)

        if preset_path.suffix.lower() == ".json":
            try:
                data = read_preset_json(preset_path)
            except Exception:
                logger.exception("Failed to read preset JSON: %s", preset_path)
                self.report({'ERROR'}, _T("Failed to load compositor from {}").format(preset_path))
                return False
            asset_path = resolve_asset_path(data.get("asset", ""))
            if asset_path is None or not asset_path.exists():
                self.report({'ERROR'}, _T("Preset not found: {}").format(data.get("asset", "")))
                return False

            same_asset = (
                coloring_state.last_loaded_asset == preset_key(asset_path)
                and scene_uses_compositor(sce)
                and get_comp_node_tree(sce) is not None
            )
            if not same_asset:
                if not self._load_blend_topology(asset_path, context):
                    return False
            else:
                set_viewport_shading("ALWAYS", context)

            try:
                apply_scene_preset(sce, data)
            except Exception:
                logger.exception("Failed to apply preset JSON: %s", preset_path)
                self.report({'ERROR'}, _T("Failed to load compositor from {}").format(preset_path))
                return False

            # Keep UI asset selector aligned with the template used by this JSON.
            try:
                prop = sce.colorista_prop
                asset_id = asset_path.as_posix()
                items = prop.asset_items(context)
                valid = {item[0] for item in items}
                if asset_id in valid and prop.asset != asset_id:
                    coloring_state.set_suppress_asset_import(True)
                    try:
                        prop.asset = asset_id
                    finally:
                        coloring_state.set_suppress_asset_import(False)
            except Exception:
                pass

            return self._finish_load(sce, preset_path.as_posix())

        if not self._load_blend_topology(preset_path, context):
            return False
        return self._finish_load(sce, preset_path.as_posix())

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


def import_compositor(
    context: bpy.types.Context,
    *,
    preset: str | Path | None = None,
    use_default: bool = False,
    no_cache: bool = False,
    force: bool = False,
    operator=None,
) -> bool:
    reporter = operator.report if operator is not None else None
    helper = CompositorImportHelper(no_cache=no_cache, reporter=reporter)

    preset_path: Path | None
    if use_default:
        preset_path = get_default_preset_path()
        if preset_path is None:
            helper.report({'ERROR'}, _T("No default preset found"))
            return False
    elif preset:
        preset_path = Path(preset)
    else:
        asset = context.scene.colorista_prop.get_asset_path(context)
        preset_path = Path(asset) if asset else None

    if preset_path is None:
        helper.report({'ERROR'}, _T("No default preset found"))
        return False
    if not preset_path.exists():
        helper.report({'ERROR'}, _T("Preset not found: {}").format(preset_path))
        return False

    key = preset_key(preset_path)
    # use_default / force always reload; otherwise skip duplicate path (avoids appending nodes)
    if not force and not use_default and coloring_state.last_loaded_preset == key:
        helper.report({'INFO'}, _T("Already on this preset"))
        return True

    if not helper.enable_coloring_f(preset_path, context):
        return False
    set_loaded_preset(preset_path)
    return True


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
    bl_options = {'REGISTER'}

    preset: bpy.props.StringProperty(default="", options={'HIDDEN', 'SKIP_SAVE'})
    popup: bpy.props.BoolProperty(default=True, options={'HIDDEN', 'SKIP_SAVE'})

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
        if self.preset:
            return Path(self.preset).with_suffix(".json")
        return get_asset_preset_dir(asset).joinpath(preset_name).with_suffix(".json")

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        if not context.scene.colorista_prop.get_asset_path(context):
            self.report({'ERROR'}, _T("No asset selected"))
            return {"CANCELLED"}
        if not context.scene.colorista_prop.preset_save_name:
            self.report({'ERROR'}, _T("Enter a preset name"))
            return {"CANCELLED"}
        wm = context.window_manager
        path = self.get_preset_path(context)
        if not is_under_user_presets_root(path):
            self.report({'ERROR'}, _T("Preset path is outside the user presets folder"))
            return {"CANCELLED"}
        if path and path.exists() and self.popup:
            return wm.invoke_props_dialog(self, width=200)
        return self.execute(context)

    def execute(self, context: bpy.types.Context):
        path = self.get_preset_path(context)
        asset = context.scene.colorista_prop.get_asset_path(context)
        self.preset = ""
        if not is_under_user_presets_root(path):
            self.report({'ERROR'}, _T("Preset path is outside the user presets folder"))
            return {"CANCELLED"}
        try:
            save_compositor_values_json(path, context.scene, asset)
        except Exception as e:
            logger.exception("Failed to save preset")
            self.report({'ERROR'}, str(e))
            return {"CANCELLED"}
        from .properties import Props
        Props._ref_items.pop(get_asset_preset_dir(asset), None)
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
        preset = prop.get_preset_path(context)
        if preset == prop.PRESET_NONE_ID:
            cls.poll_message_set(_T("Select a preset to delete"))
            return False
        if not is_user_preset_file(preset):
            cls.poll_message_set(_T("Only user-saved presets can be deleted"))
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
        if not is_user_preset_file(path):
            self.report({'ERROR'}, _T("Only user-saved presets can be deleted"))
            return {"CANCELLED"}

        path.unlink()
        from .properties import Props
        Props._ref_items.pop(path.parent, None)
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


class ColoristaSwitchPreset(bpy.types.Operator):
    bl_idname = "wm.colorista_switch_preset"
    bl_description = "Switch preset"
    bl_label = "Switch preset"
    bl_options = {'INTERNAL'}

    direction: bpy.props.EnumProperty(
        items=(
            ("PREV", "Previous", "Previous preset"),
            ("NEXT", "Next", "Next preset"),
        ),
        default="NEXT",
    )

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return _poll_coloring_enabled(cls, context)

    def execute(self, context: bpy.types.Context):
        prop = context.scene.colorista_prop
        items = [item for item in prop.get_presets(context) if item[0] != prop.PRESET_NONE_ID]
        if len(items) <= 1:
            self.report({'INFO'}, _T("Only one preset available"))
            return {"CANCELLED"}

        step = -1 if self.direction == "PREV" else 1
        pos = 0
        for index, item in enumerate(items):
            if item[0] == prop.preset:
                pos = index
                break
        new_preset = items[(pos + step) % len(items)][0]
        if preset_key(new_preset) == preset_key(prop.preset):
            self.report({'INFO'}, _T("Only one preset available"))
            return {"CANCELLED"}

        prop.preset = new_preset
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

    def execute(self, context: bpy.types.Context):
        preset = self.preset or None
        if import_compositor(
            context,
            preset=preset,
            use_default=self.use_default,
            no_cache=self.no_cache,
            force=bool(self.preset),
            operator=self,
        ):
            self.preset = ""
            return {"FINISHED"}
        return {"CANCELLED"}


clss = (
    ColoristaSavePreset,
    ColoristaDeletePreset,
    ColoristaSwitchPreset,
    ColoristaSwitchDevice,
    ColoristaSwitchPrecision,
    CompositorNodeTreeImport,
)

register, unregister = bpy.utils.register_classes_factory(clss)
