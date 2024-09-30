import bpy
from pathlib import Path
from .operators import CompositorNodeTreeImport
from ...utils.common import get_resource_dir
from ..preference import get_pref


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
    bl_idname = "colorista.delete_history"
    bl_description = "Delete history"
    bl_label = "Delete history"

    file: bpy.props.StringProperty(default="")

    def execute(self, context: bpy.types.Context):
        if not self.file:
            return {"FINISHED"}
        file = Path(self.file)
        if not file.exists():
            return {"FINISHED"}
        if file.is_dir():
            return {"FINISHED"}
        if not file.with_suffix(".blend"):
            return {"FINISHED"}
        Path(self.file).unlink()
        update_history()
        return {"FINISHED"}


@bpy.app.handlers.persistent
def update_history(_=None):
    try:
        cache_dir = get_resource_dir().joinpath("cache")
        cache_dir.mkdir(exist_ok=True)
        sce = bpy.context.scene
        files = sorted(cache_dir.glob("*.blend"), reverse=True)
        count = get_pref().cache_current_cache_count
        sce.colorista_items.clear()
        for file in files[:count]:
            item = sce.colorista_items.add()
            item.name = file.stem
            item.file = file.as_posix()
        # 只保留最新的, 其余删除
        for file in files[count:]:
            file.unlink()
    except Exception as e:
        print("Update History Error: ", e)
    return 1


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
    bpy.app.handlers.load_post.append(update_history)


def unregister():
    del bpy.types.Scene.colorista_items_index
    del bpy.types.Scene.colorista_items
    unreg()
    bpy.app.handlers.load_post.remove(update_history)
