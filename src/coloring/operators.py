from typing import Set
import bpy
from bpy.types import Context, Event
from ...utils.logger import logger


class TestOperator(bpy.types.Operator):
    bl_idname = "xxxtest.operator"
    bl_description = "Test Operator Translation"
    bl_label = "Test Operator"

    def invoke(self, context: Context, event: Event) -> Set[int] | Set[str]:
        logger.info("test operator INVOKE")
        return self.execute(context)

    def execute(self, context):
        logger.info("test operator EXECUTE")
        return {"FINISHED"}
