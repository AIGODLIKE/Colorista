import bpy
from pathlib import Path

from ..i18n import _T
from .constants import OPS_TCTX
from ..preference import get_pref
from ...utils.logger import logger
from ...utils.paths import get_user_cache_dir
from .operators import CompositorNodeTreeImport


class COLORISTA_HISTORY_UL_UIList(bpy.types.UIList):

    def draw_item(
        self,
        context: bpy.types.Context,
        layout: bpy.types.UILayout,
        data,
        item,
        icon,
        active_data,
        active_property,
        index=0,
        flt_flag=0,
    ):
        row = layout.row(align=True)
        row.label(text=item.name)
        op = row.operator(CompositorNodeTreeImport.bl_idname, text="", icon="TIME")
        op.preset = item.file
        op.no_cache = True
        row.operator(ColoristaDeleteHistory.bl_idname, text="", icon="X").file = item.file


class ColoristaDeleteHistory(bpy.types.Operator):
    bl_idname = "wm.colorista_delete_history"
    bl_description = "Delete this history entry"
    bl_label = "Delete history"
    bl_translation_context = OPS_TCTX
    bl_options = {"INTERNAL"}

    file: bpy.props.StringProperty(default="", options={"HIDDEN", "SKIP_SAVE"})

    def execute(self, context: bpy.types.Context):
        if not self.file:
            return {"CANCELLED"}
        file = Path(self.file)
        if not file.exists():
            update_history(context)
            self.report({"WARNING"}, _T("History file not found"))
            return {"FINISHED"}
        if file.is_dir():
            return {"CANCELLED"}
        if file.suffix.lower() != ".json":
            return {"CANCELLED"}
        file.unlink()
        update_history(context)
        return {"FINISHED"}


def _cleanup_legacy_blend_history(cache_dir: Path) -> None:
    for file in cache_dir.glob("*.blend"):
        if file.is_file():
            try:
                file.unlink()
            except OSError:
                pass


def _iter_history_files(cache_dir: Path) -> list[Path]:
    files = [f for f in cache_dir.glob("*.json") if f.is_file()]
    return sorted(files, reverse=True)


def update_history(context=None):
    try:
        context = context or bpy.context
        cache_dir = get_user_cache_dir()
        _cleanup_legacy_blend_history(cache_dir)
        prop = context.scene.colorista_prop
        files = _iter_history_files(cache_dir)
        pref = get_pref()
        count = pref.cache_current_cache_count if pref else 10
        prop.history_items.clear()
        for file in files[:count]:
            item = prop.history_items.add()
            item.name = file.stem
            item.file = file.as_posix()
        for file in files[count:]:
            file.unlink()
    except Exception as e:
        logger.error("Update history failed: %s", e)


clss = (
    COLORISTA_HISTORY_UL_UIList,
    ColoristaDeleteHistory,
)

reg, unreg = bpy.utils.register_classes_factory(clss)


def register():
    reg()


def unregister():
    unreg()
