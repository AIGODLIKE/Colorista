import bpy
from .operators import TestOperator
from .panels import ColoringPanel
from .properties import Props


def register():
    bpy.utils.register_class(TestOperator)
    bpy.utils.register_class(ColoringPanel)
    bpy.utils.register_class(Props)
    bpy.types.Scene.ac_prop = bpy.props.PointerProperty(type=Props)
    bpy.types.Node.ac_expand = bpy.props.BoolProperty(name="Expand", default=True)


def unregister():
    del bpy.types.Node.ac_expand
    del bpy.types.Scene.ac_prop
    bpy.utils.unregister_class(ColoringPanel)
    bpy.utils.unregister_class(Props)
    bpy.utils.unregister_class(TestOperator)
