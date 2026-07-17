"""Thin RNA operators — business logic lives in ``coloring.api``."""

from pathlib import Path

import bpy

from ..coloring.constants import OPS_TCTX, PRESET_NONE_ID
from ..coloring.preset.io import save_compositor_values_json
from ..src.translate import _T
from ..utils.icon import Icon
from ..utils.logger import logger
from ..utils.node import scene_uses_compositor
from ..utils.paths import get_asset_preset_dir, is_under_user_presets_root, is_user_preset_file
from ..coloring import catalog
from ..coloring import api as coloring
from ..coloring.config import get_config


def _custom_presets_root() -> str | None:
    return get_config().custom_presets_root


def _poll_coloring_enabled(cls, context: bpy.types.Context) -> bool:
    try:
        if not context.scene.colorista_prop.enable_coloring:
            cls.poll_message_set(_T("Enable Coloring first"))
            return False
    except AttributeError:
        cls.poll_message_set(_T("Enable Coloring first"))
        return False
    return True


class ColoristaSavePreset(bpy.types.Operator):
    bl_idname = "wm.colorista_save_preset"
    bl_description = "Save the current compositor values as a preset"
    bl_label = "Save preset"
    bl_translation_context = OPS_TCTX
    bl_options = {"REGISTER"}

    preset: bpy.props.StringProperty(default="", options={"HIDDEN", "SKIP_SAVE"})
    popup: bpy.props.BoolProperty(default=True, options={"HIDDEN", "SKIP_SAVE"})

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
        layout.label(
            text=_T("Overwrite preset: {}?").format(path.stem),
            icon=Icon.ui("QUESTION"),
        )

    def get_preset_path(self, context: bpy.types.Context | None = None):
        context = context or bpy.context
        prop = context.scene.colorista_prop
        asset = prop.get_asset_path(context)
        preset_name = prop.preset_save_name
        if self.preset:
            return Path(self.preset).with_suffix(".json")
        return get_asset_preset_dir(
            asset, custom_presets_root=_custom_presets_root()
        ).joinpath(preset_name).with_suffix(".json")

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        if not context.scene.colorista_prop.get_asset_path(context):
            self.report({"ERROR"}, _T("No asset selected"))
            return {"CANCELLED"}
        if not context.scene.colorista_prop.preset_save_name:
            self.report({"ERROR"}, _T("Enter a preset name"))
            return {"CANCELLED"}
        wm = context.window_manager
        path = self.get_preset_path(context)
        if not is_under_user_presets_root(path, custom_presets_root=_custom_presets_root()):
            self.report({"ERROR"}, _T("Preset path is outside the user presets folder"))
            return {"CANCELLED"}
        if path and path.exists() and self.popup:
            return wm.invoke_props_dialog(self, width=200)
        return self.execute(context)

    def execute(self, context: bpy.types.Context):
        path = self.get_preset_path(context)
        asset = context.scene.colorista_prop.get_asset_path(context)
        self.preset = ""
        if not is_under_user_presets_root(path, custom_presets_root=_custom_presets_root()):
            self.report({"ERROR"}, _T("Preset path is outside the user presets folder"))
            return {"CANCELLED"}
        try:
            save_compositor_values_json(path, context.scene, asset)
        except Exception as e:
            logger.exception("Failed to save preset")
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        catalog.invalidate(
            get_asset_preset_dir(asset, custom_presets_root=_custom_presets_root())
        )
        self.report({"INFO"}, _T("Preset saved: {}").format(path.stem))
        return {"FINISHED"}


class ColoristaDeletePreset(bpy.types.Operator):
    bl_idname = "wm.colorista_delete_preset"
    bl_description = "Delete the selected user preset"
    bl_label = "Delete preset"
    bl_translation_context = OPS_TCTX
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        prop = context.scene.colorista_prop
        if not prop.get_asset_path(context):
            cls.poll_message_set(_T("Select an asset first"))
            return False
        preset = prop.get_preset_path(context)
        if preset == PRESET_NONE_ID:
            cls.poll_message_set(_T("Select a preset to delete"))
            return False
        if not is_user_preset_file(preset, custom_presets_root=_custom_presets_root()):
            cls.poll_message_set(_T("Only user-saved presets can be deleted"))
            return False
        return True

    def draw(self, context: bpy.types.Context):
        layout = self.layout
        asset = Path(context.scene.colorista_prop.get_asset_path(context)).stem
        preset = Path(context.scene.colorista_prop.get_preset_path(context)).stem
        layout.alert = True
        layout.label(
            text=_T('Delete preset "{}" for asset "{}"?').format(preset, asset),
            icon=Icon.ui("TRASH"),
        )

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        return context.window_manager.invoke_props_dialog(self, width=200)

    def execute(self, context: bpy.types.Context):
        path = Path(context.scene.colorista_prop.get_preset_path(context))
        if not is_user_preset_file(path, custom_presets_root=_custom_presets_root()):
            self.report({"ERROR"}, _T("Only user-saved presets can be deleted"))
            return {"CANCELLED"}

        try:
            path.unlink(missing_ok=True)
        except OSError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        catalog.invalidate(path.parent)
        return {"FINISHED"}


class ColoristaSwitchDevice(bpy.types.Operator):
    bl_idname = "wm.colorista_switch_device"
    bl_description = "Toggle compositor device between CPU and GPU"
    bl_label = "Switch device"
    bl_translation_context = OPS_TCTX
    bl_options = {"REGISTER", "UNDO"}

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
    bl_description = "Toggle compositor precision between Auto and Full"
    bl_label = "Switch precision"
    bl_options = {"REGISTER", "UNDO"}
    bl_translation_context = OPS_TCTX

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


class ColoristaResetDefaults(bpy.types.Operator):
    bl_idname = "wm.colorista_reset_defaults"
    bl_description = "Reset node values to asset defaults"
    bl_label = "Reset to defaults"
    bl_translation_context = OPS_TCTX
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return _poll_coloring_enabled(cls, context)

    def execute(self, context: bpy.types.Context):
        if not coloring.reset_to_defaults(context, reporter=self.report):
            self.report({"ERROR"}, _T("No asset selected"))
            return {"CANCELLED"}
        return {"FINISHED"}


class ColoristaSwitchAsset(bpy.types.Operator):
    bl_idname = "wm.colorista_switch_asset"
    bl_description = "Switch to the previous or next asset"
    bl_label = "Switch asset"
    bl_translation_context = OPS_TCTX
    bl_options = {"INTERNAL"}

    direction: bpy.props.EnumProperty(
        items=(
            ("PREV", "Previous", "Previous asset"),
            ("NEXT", "Next", "Next asset"),
        ),
        default="NEXT",
    )

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return _poll_coloring_enabled(cls, context)

    def execute(self, context: bpy.types.Context):
        delta = -1 if self.direction == "PREV" else 1
        if not coloring.switch_asset(context, delta):
            return {"CANCELLED"}
        return {"FINISHED"}


class ColoristaSwitchPreset(bpy.types.Operator):
    bl_idname = "wm.colorista_switch_preset"
    bl_description = "Switch to the previous or next preset"
    bl_label = "Switch preset"
    bl_translation_context = OPS_TCTX
    bl_options = {"INTERNAL"}

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
        delta = -1 if self.direction == "PREV" else 1
        ok, message = coloring.switch_preset(context, delta)
        if not ok:
            self.report({"INFO"}, message)
            return {"CANCELLED"}
        return {"FINISHED"}


class CompositorNodeTreeImport(bpy.types.Operator):
    bl_idname = "wm.colorista_compositor_import"
    bl_description = "Import a compositor node tree from a file"
    bl_label = "Import node tree"
    bl_translation_context = OPS_TCTX
    bl_options = {"REGISTER", "UNDO"}

    use_default: bpy.props.BoolProperty(default=False)
    preset: bpy.props.StringProperty(default="")
    no_cache: bpy.props.BoolProperty(default=False)

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return _poll_coloring_enabled(cls, context)

    def execute(self, context: bpy.types.Context):
        preset = self.preset or None
        if coloring.load(
            context,
            preset=preset,
            use_default=self.use_default,
            cache=not self.no_cache,
            force=bool(self.preset),
            reporter=self.report,
        ):
            self.preset = ""
            return {"FINISHED"}
        return {"CANCELLED"}


clss = (
    ColoristaSavePreset,
    ColoristaDeletePreset,
    ColoristaSwitchAsset,
    ColoristaSwitchPreset,
    ColoristaSwitchDevice,
    ColoristaSwitchPrecision,
    ColoristaResetDefaults,
    CompositorNodeTreeImport,
)

register, unregister = bpy.utils.register_classes_factory(clss)
