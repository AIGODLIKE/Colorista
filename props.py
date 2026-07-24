import bpy

from .coloring.constants import PRESET_NONE_ID, PROP_TCTX
from .coloring.session import session
from .utils.logger import logger
from .coloring import catalog

_enable_update_guard = False


class ColoristaHistoryItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(default="")
    file: bpy.props.StringProperty(default="")


class Props(bpy.types.PropertyGroup):
    def update_enable_coloring(self, context: bpy.types.Context):
        global _enable_update_guard
        if _enable_update_guard:
            return
        from .coloring import api as coloring

        if self.enable_coloring:
            logger.info("Coloring enabled")
            try:
                ok = coloring.enable(context)
            except Exception:
                logger.exception("Failed to enable coloring")
                ok = False
            if not ok:
                # Roll back partial state so UI and handlers stay consistent.
                try:
                    coloring.disable(context)
                except Exception:
                    logger.exception("Failed to roll back coloring state")
                _enable_update_guard = True
                try:
                    self.enable_coloring = False
                finally:
                    _enable_update_guard = False
        else:
            logger.info("Coloring disabled")
            try:
                coloring.disable(context)
            except Exception:
                logger.exception("Failed to disable coloring")

    enable_coloring: bpy.props.BoolProperty(
        default=False,
        name="Enable Coloring",
        description="Enable the Colorista color grading panel",
        update=update_enable_coloring,
        translation_context=PROP_TCTX,
    )

    def pre_dir_items(self, context):
        return catalog.list_categories(context)

    def update_pre_dir(self, context):
        items = catalog.list_assets(self.pre_dir, context)
        if not items:
            return
        valid = {item[0] for item in items}
        if self.asset not in valid:
            self.asset = items[0][0]

    pre_dir: bpy.props.EnumProperty(
        name="Asset Category",
        items=pre_dir_items,
        update=update_pre_dir,
        translation_context=PROP_TCTX,
    )

    def asset_items(self, context):
        return catalog.list_assets(self.pre_dir, context)

    def get_asset_path(self, context) -> str:
        current = self.asset
        # Enum identifiers are full .blend paths; skip re-listing on the hot path.
        if current and current.lower().endswith(".blend"):
            return current
        items = self.asset_items(context)
        return catalog.resolve_enum_value(items, current)

    def update_asset(self, context):
        if session.suppress_asset_import:
            return
        if not self.enable_coloring:
            return
        from .coloring.api import schedule_load

        schedule_load()

    asset: bpy.props.EnumProperty(
        name="Asset",
        items=asset_items,
        update=update_asset,
        translation_context=PROP_TCTX,
    )

    def get_presets(self, context):
        return catalog.list_presets(self.get_asset_path(context), context)

    def get_preset_path(self, context) -> str:
        items = self.get_presets(context)
        if not items:
            return PRESET_NONE_ID
        return catalog.resolve_enum_value(items, self.preset) or PRESET_NONE_ID

    def update_preset(self, context):
        if self.preset == PRESET_NONE_ID:
            return
        if not self.enable_coloring:
            return
        from .coloring.api import schedule_load

        schedule_load(preset=self.preset)

    preset: bpy.props.EnumProperty(
        name="Preset",
        items=get_presets,
        update=update_preset,
        translation_context=PROP_TCTX,
    )

    preset_save_name: bpy.props.StringProperty(
        name="Preset Name",
        default="",
        translation_context=PROP_TCTX,
    )

    history_items: bpy.props.CollectionProperty(type=ColoristaHistoryItem)
    history_items_index: bpy.props.IntProperty(default=0)


clss = (
    ColoristaHistoryItem,
    Props,
)

reg, unreg = bpy.utils.register_classes_factory(clss)


def register():
    reg()
    bpy.types.Scene.colorista_prop = bpy.props.PointerProperty(type=Props)


def unregister():
    del bpy.types.Scene.colorista_prop
    unreg()
