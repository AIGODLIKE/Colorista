# Changelog

## 2026-7-16

重构: 架构分层（api / catalog / load / transfer / session / handlers）；统一资产与预设切换操作符；合成树迁移与 4.x/5.x 兼容集中；精简 Icon / 路径工具；清理死代码

---

## 2026-7-10 v1.2.2

修复: zip 安装后找不到默认预设（default.blend 路径解析）；预设列表无图标；开启调色失败时 RuntimeError 未捕获导致崩溃；资产/预设枚举缩略图异步加载后缓存仍指向 NONE 占位图

---

## 2026-7-7 v1.2.1

修复: Blender 5.1 历史记录 popover 报错（改用 layout.popover）

---

## 2026-7-7 v1.2.0

优化: 按需激活 Handler/监听；单 timer 轮询；图标与缩略图懒加载；历史记录按需刷新；视口合成按窗口独立控制

修改: Extension 格式迁移；Blender 5.x 合成器适配；layout.panel 折叠节点；操作符规范与 i18n；调色失败回滚；日志默认关闭

删除: bl_info；自定义节点 expand；历史删除 redo 弹窗

---

## 2025 v1.1.9

修改: 预设与节点绘制修复；调试偏好

## 2025 v1.1.8

修改: 四视图 Gizmo 修复；Blender 5.0 适配
