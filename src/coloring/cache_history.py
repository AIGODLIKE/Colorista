import bpy
from pathlib import Path
from .operators import CompositorNodeTreeImport
from ...utils.common import get_user_cache_dir
from ..preference import get_pref
from ...utils.logger import logger


class ColoristaHistoryItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(default="")
    file: bpy.props.StringProperty(default="")


class COLORISTA_HISTORY_UL_UIList(bpy.types.UIList):

    def draw_item(self,
                  context: bpy.types.Context,
                  layout: bpy.types.UILayout,
                  data, item, icon, active_data, active_property, index=0, flt_flag=0):
        row = layout.row(align=True)
        row.label(text=item.name)
        op = row.operator(CompositorNodeTreeImport.bl_idname, text="", icon="TIME")
        op.preset = item.file
        op.no_cache = True
        row.operator(ColoristaDeleteHistory.bl_idname, text="", icon="X").file = item.file


class ColoristaDeleteHistory(bpy.types.Operator):
    bl_idname = "wm.colorista_delete_history"
    bl_description = "Delete history"
    bl_label = "Delete history"
    bl_options = {'REGISTER', 'UNDO'}

    file: bpy.props.StringProperty(default="")

    def execute(self, context: bpy.types.Context):
        if not self.file:
            return {"CANCELLED"}
        file = Path(self.file)
        if not file.exists():
            self.report({'ERROR'}, "History file not found")
            return {"CANCELLED"}
        if file.is_dir():
            return {"CANCELLED"}
        if file.suffix.lower() != ".blend":
            return {"CANCELLED"}
        file.unlink()
        update_history()
        return {"FINISHED"}


@bpy.app.handlers.persistent
def update_history(_=None):
    try:
        cache_dir = get_user_cache_dir()
        sce = bpy.context.scene
        files = sorted(cache_dir.glob("*.blend"), reverse=True)
        pref = get_pref()
        count = pref.cache_current_cache_count if pref else 10
        sce.colorista_items.clear()
        for file in files[:count]:
            item = sce.colorista_items.add()
            item.name = file.stem
            item.file = file.as_posix()
        for file in files[count:]:
            file.unlink()
    except Exception as e:
        logger.error("Update history failed: %s", e)


clss = (
    ColoristaHistoryItem,
    COLORISTA_HISTORY_UL_UIList,
    ColoristaDeleteHistory,
)

reg, unreg = bpy.utils.register_classes_factory(clss)


def register():
    reg()
    bpy.types.Scene.colorista_items = bpy.props.CollectionProperty(type=ColoristaHistoryItem)
    bpy.types.Scene.colorista_items_index = bpy.props.IntProperty(default=0)


def unregister():
    del bpy.types.Scene.colorista_items_index
    del bpy.types.Scene.colorista_items
    unreg()
