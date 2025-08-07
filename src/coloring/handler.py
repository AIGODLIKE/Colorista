import bpy
import re
import traceback
from ..preference import get_pref
# 主节点组名称
main_node_group_name = "Basic adjustment nodes for colorists"


class DepsgraphPostHandler:
    handlers: dict[callable, None] = {}

    @classmethod
    def add(self, handler: callable):
        self.handlers[handler] = None

    @classmethod
    def remove(self, handler: callable):
        self.handlers.pop(handler, None)

    @classmethod
    @bpy.app.handlers.persistent
    def update(self, scene, deps):
        for handler in self.handlers:
            try:
                handler(scene)
            except Exception:
                traceback.print_exc()

    @classmethod
    def register(self):
        bpy.app.handlers.depsgraph_update_post.append(self.update)

    @classmethod
    def unregister(self):
        bpy.app.handlers.depsgraph_update_post.remove(self.update)
        self.handlers.clear()


@bpy.app.handlers.persistent
def update_others(_):
    from .timer import update_color_manager

    update_color_manager()


@bpy.app.handlers.persistent
def update_custom_vt(_):
    from .timer import update_custom_vt

    update_custom_vt()


@bpy.app.handlers.persistent
def update_node_group(scene):
    # 获取当前场景的节点树，并找到主节点组
    main_node_tree = scene.node_tree
    if not main_node_tree:
        # print("未找到场景的节点树")
        return
    main_node_group = main_node_tree.nodes.get(main_node_group_name)

    if not main_node_group:
        # print("未找到指定的主节点组")
        return
    # 遍历主节点组的 node_tree 中的所有节点
    for node in main_node_group.node_tree.nodes:
        # 检查子节点是否具有编号格式的名称
        match = re.match(r"inputs\[(\d+)\]", node.name)
        if not match:
            continue
        input_index = int(match.group(1))

        # 检查输入编号是否在范围内
        if input_index < len(main_node_group.inputs):
            # 获取指定的输入端口
            input_socket = main_node_group.inputs[input_index]

            # 获取输入端口的名称
            input_name = input_socket.name

            # 检查参数是否为 0
            if input_socket.default_value == 0:
                node.mute = True  # 将子节点组屏蔽
                print(f"子节点 {node.name} 已屏蔽，因为参数为 0")
            else:
                # 设置标签为参数名称
                node.label = f"已绑定（{input_name}）"
                node.mute = False  # 确保子节点组未屏蔽
                print(f"子节点的新标签为: {node.label}")
        else:
            print(f"输入编号 {input_index} 超出范围")


class RenderHandler:
    handlers: dict[str, dict[callable, None]] = {
        "pre": {},
        "post": {},
        "init": {},
        "complete": {},
    }
    ctx = {}

    @classmethod
    def add(self, handler: callable, stage="pre"):
        if stage not in self.handlers:
            raise ValueError(f"Invalid stage: {stage}")
        self.handlers[stage][handler] = None

    @classmethod
    @bpy.app.handlers.persistent
    def update_pre(self, scene, deps):
        self.update_ex(scene, deps, "pre")

    @classmethod
    @bpy.app.handlers.persistent
    def update_init(self, scene, deps):
        self.update_ex(scene, deps, "init")

    @classmethod
    @bpy.app.handlers.persistent
    def update_post(self, scene, deps):
        self.update_ex(scene, deps, "post")

    @classmethod
    @bpy.app.handlers.persistent
    def update_complete(self, scene, deps):
        self.update_ex(scene, deps, "complete")

    @classmethod
    def update_ex(self, scene, deps, stage):
        for handler in self.handlers[stage]:
            try:
                handler(self, scene)
            except Exception:
                traceback.print_exc()

    @classmethod
    def register(self):
        bpy.app.handlers.render_init.append(self.update_init)
        bpy.app.handlers.render_pre.append(self.update_pre)
        bpy.app.handlers.render_post.append(self.update_post)
        bpy.app.handlers.render_complete.append(self.update_complete)

    @classmethod
    def unregister(self):
        bpy.app.handlers.render_init.remove(self.update_init)
        bpy.app.handlers.render_pre.remove(self.update_pre)
        bpy.app.handlers.render_post.remove(self.update_post)
        bpy.app.handlers.render_complete.remove(self.update_complete)
        self.handlers.clear()


def switch_to_cpu_device(self: RenderHandler, scene: bpy.types.Scene):
    self.ctx["old_compositor_device"] = scene.render.compositor_device
    if get_pref().force_use_cpu_render_image:
        scene.render.compositor_device = "CPU"


def restore_render_device(self: RenderHandler, scene: bpy.types.Scene):
    scene.render.compositor_device = self.ctx.get("old_compositor_device", "GPU")


def register():
    DepsgraphPostHandler.add(update_node_group)
    DepsgraphPostHandler.add(update_custom_vt)
    DepsgraphPostHandler.add(update_others)
    DepsgraphPostHandler.register()
    RenderHandler.add(switch_to_cpu_device, "pre")
    RenderHandler.add(restore_render_device, "complete")
    RenderHandler.register()


def unregister():
    DepsgraphPostHandler.unregister()
    RenderHandler.unregister()
