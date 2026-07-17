import bpy
from pathlib import Path

from ..coloring.constants import OPS_TCTX
from ..src.translate import _T
from ..coloring import history as history_svc
from ..utils.icon import Icon
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
        op = row.operator(
            CompositorNodeTreeImport.bl_idname, text="", icon=Icon.ui("TIME")
        )
        op.preset = item.file
        op.no_cache = True
        row.operator(
            ColoristaDeleteHistory.bl_idname, text="", icon=Icon.ui("X")
        ).file = item.file


class ColoristaDeleteHistory(bpy.types.Operator):
    bl_idname = "wm.colorista_delete_history"
    bl_description = "Delete this history entry"
    bl_label = "Delete history"
    bl_translation_context = OPS_TCTX
    bl_options = {"INTERNAL"}

    file: bpy.props.StringProperty(default="", options={"HIDDEN", "SKIP_SAVE"})

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        try:
            if not context.scene.colorista_prop.enable_coloring:
                cls.poll_message_set(_T("Enable Coloring first"))
                return False
        except AttributeError:
            cls.poll_message_set(_T("Enable Coloring first"))
            return False
        return True

    def execute(self, context: bpy.types.Context):
        if not self.file:
            return {"CANCELLED"}
        file = Path(self.file)
        if file.is_dir() or file.suffix.lower() != ".json":
            return {"CANCELLED"}
        if not history_svc.remove_entry(context, file):
            self.report({"WARNING"}, _T("History file not found"))
            return {"CANCELLED"}
        return {"FINISHED"}


clss = (
    COLORISTA_HISTORY_UL_UIList,
    ColoristaDeleteHistory,
)

reg, unreg = bpy.utils.register_classes_factory(clss)


def register():
    reg()


def unregister():
    unreg()
