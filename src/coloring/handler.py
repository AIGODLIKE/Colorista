import bpy
import re
import traceback

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
def update_custom_color_space(_):
    tree = bpy.context.scene.node_tree
    if not tree:
        return
    color_space_control = tree.nodes.get("clorista-Color Space")
    if not color_space_control:
        return
    space = color_space_control.inputs.get("Space")
    if not space:
        return
    try:
        color_space = float(space.default_value)
        ori_space_type = bpy.context.scene.display_settings.display_device
        space_type = ori_space_type
        if abs(color_space) < 0.001:
            # AgX
            space_type = "AgX"
        elif abs(color_space - 0.1) < 0.001:
            space_type = "Standard"
        elif abs(color_space - 0.2) < 0.001:
            space_type = "Filmic"
        elif abs(color_space - 0.3) < 0.001:
            space_type = "Khronos PBR Neutral"
        if space_type != ori_space_type:
            bpy.context.scene.display_settings.display_device = space_type
    except Exception:
        pass


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


def register():
    DepsgraphPostHandler.add(update_node_group)
    DepsgraphPostHandler.add(update_custom_color_space)
    DepsgraphPostHandler.add(update_others)
    DepsgraphPostHandler.register()


def unregister():
    DepsgraphPostHandler.unregister()
