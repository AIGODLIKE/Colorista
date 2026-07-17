"""Preview-collection icon registry (enum thumbnails + panel icons)."""

from __future__ import annotations

from pathlib import Path

from .timer import Timer
from .watcher import FSWatcher

_UI_ICON_NAMES: frozenset[str] | None = None
_FALLBACK_UI_ICON = "ERROR"


def _ui_icon_names() -> frozenset[str]:
    global _UI_ICON_NAMES
    if _UI_ICON_NAMES is None:
        import bpy

        try:
            items = bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items
            _UI_ICON_NAMES = frozenset(items.keys())
        except Exception:
            _UI_ICON_NAMES = frozenset()
    return _UI_ICON_NAMES


class PrevMgr:
    import bpy
    __PREV__: dict[int, "bpy.utils.previews.ImagePreviewCollection"] = {}

    @staticmethod
    def new() -> "bpy.utils.previews.ImagePreviewCollection":
        import bpy.utils.previews
        import random

        prev = bpy.utils.previews.new()
        while (i := random.randint(0, 999999999)) in PrevMgr.__PREV__:
            continue
        PrevMgr.__PREV__[i] = prev
        return prev

    @staticmethod
    def remove(prev):
        import bpy.utils.previews

        bpy.utils.previews.remove(prev)


class MetaIn(type):
    def __contains__(cls, name):
        return cls.__contains__(cls, name)


class Icon(metaclass=MetaIn):
    PREV_DICT = None
    NONE_IMAGE = ""
    IMG_STATUS = {}
    INSTANCE = None
    _VALIDATED: set[str] = set()
    _RELOAD_SCHEDULED: set[str] = set()
    _RELOAD_RETRY: dict[str, int] = {}
    _RELOAD_DELAY = 0.2
    _RELOAD_MAX_RETRY = 3

    @classmethod
    def _ensure_prev(cls):
        if cls.PREV_DICT is None:
            cls.PREV_DICT = PrevMgr.new()
        return cls.PREV_DICT

    def __init__(self) -> None:
        if Icon.NONE_IMAGE and Icon.NONE_IMAGE not in Icon:
            Icon.NONE_IMAGE = FSWatcher.to_str(Icon.NONE_IMAGE)
            self.reg_icon(Icon.NONE_IMAGE)

    def __new__(cls, *args, **kwargs):
        if cls.INSTANCE is None:
            cls.INSTANCE = object.__new__(cls, *args, **kwargs)
        return cls.INSTANCE

    @staticmethod
    def clear():
        prev = Icon._ensure_prev()
        prev.clear()
        Icon.IMG_STATUS.clear()
        Icon._VALIDATED.clear()
        Icon._RELOAD_SCHEDULED.clear()
        Icon._RELOAD_RETRY.clear()
        if Icon.NONE_IMAGE:
            Icon.reg_icon(Icon.NONE_IMAGE)

    @staticmethod
    def cleanup():
        if Icon.PREV_DICT is not None:
            PrevMgr.remove(Icon.PREV_DICT)
        Icon.PREV_DICT = None
        Icon.IMG_STATUS.clear()
        Icon._VALIDATED.clear()
        Icon._RELOAD_SCHEDULED.clear()
        Icon._RELOAD_RETRY.clear()
        Icon.NONE_IMAGE = ""
        Icon.INSTANCE = None

    @staticmethod
    def try_mark_image(path) -> bool:
        p = FSWatcher.to_path(path)
        path = FSWatcher.to_str(path)
        if not p.exists():
            return False
        if Icon.IMG_STATUS.get(path, -1) == p.stat().st_mtime_ns:
            return False
        return True

    @staticmethod
    def can_mark_image(path) -> bool:
        p = FSWatcher.to_path(path)
        path = FSWatcher.to_str(path)
        if not Icon.try_mark_image(p):
            return False
        Icon.IMG_STATUS[path] = p.stat().st_mtime_ns
        return True

    @staticmethod
    def remove_mark(name) -> bool:
        name = FSWatcher.to_str(name)
        Icon.IMG_STATUS.pop(name, None)
        Icon._VALIDATED.discard(name)
        Icon._ensure_prev().pop(name, None)
        return True

    @staticmethod
    def reg_none(none: Path):
        none = FSWatcher.to_str(none)
        if none in Icon:
            return
        Icon.NONE_IMAGE = none
        Icon.reg_icon(Icon.NONE_IMAGE)

    @staticmethod
    def reg_icon(path, reload=False):
        path = FSWatcher.to_str(path)
        # Hot path: panel draw / enum items call this every redraw.
        if not reload and path in Icon._VALIDATED:
            return Icon[path]
        if not Icon.can_mark_image(path) and not reload:
            Icon._ensure_valid_preview(path)
            return Icon[path]
        prev = Icon._ensure_prev()
        if path not in Icon:
            prev.load(path, path, "IMAGE")
        if reload:
            Timer.put(prev[path].reload)
        Icon._ensure_valid_preview(path)
        return Icon[path]

    @staticmethod
    def resource(name: str, *, reload: bool = False) -> int:
        """Register an icon from ``resource/icons`` by filename (e.g. ``\"color.png\"``)."""
        from .paths import get_icons_dir

        path = get_icons_dir().joinpath(name)
        if not path.suffix:
            path = path.with_suffix(".png")
        return Icon.reg_icon(path, reload=reload)

    @staticmethod
    def ui(name: str, fallback: str = _FALLBACK_UI_ICON) -> str:
        """Return a builtin UI icon identifier, falling back if unsupported in this Blender."""
        names = _ui_icon_names()
        if name in names:
            return name
        if fallback in names:
            return fallback
        return "NONE"

    @staticmethod
    def _is_preview_empty(preview) -> bool:
        """One-time emptiness check (callers must cache via _VALIDATED)."""
        try:
            w, h = preview.icon_size
            if w <= 0 or h <= 0:
                return True
            pixels = preview.image_pixels_float
            if not pixels:
                return True
            # Early-exit scan; only runs until the path is marked validated.
            return not any(value != 0.0 for value in pixels)
        except (AttributeError, TypeError, ReferenceError):
            return True

    @staticmethod
    def _ensure_valid_preview(path):
        path = FSWatcher.to_str(path)
        if path in Icon._VALIDATED:
            return
        if Icon._RELOAD_RETRY.get(path, 0) >= Icon._RELOAD_MAX_RETRY:
            return
        preview = Icon._ensure_prev().get(path)
        icon_id = Icon.get_icon_id(path)
        if preview and not Icon._is_preview_empty(preview) and icon_id != 0:
            Icon._RELOAD_RETRY.pop(path, None)
            Icon._VALIDATED.add(path)
            return
        Icon._schedule_delayed_reload(path)

    @staticmethod
    def _schedule_delayed_reload(path):
        import bpy

        path = FSWatcher.to_str(path)
        if path in Icon._RELOAD_SCHEDULED:
            return
        Icon._RELOAD_SCHEDULED.add(path)

        def _reload():
            Icon._RELOAD_SCHEDULED.discard(path)
            Icon._RELOAD_RETRY[path] = Icon._RELOAD_RETRY.get(path, 0) + 1
            Icon.remove_mark(path)
            try:
                Icon.reg_icon(path, reload=True)
            except Exception:
                pass
            try:
                for window in bpy.context.window_manager.windows:
                    for area in window.screen.areas:
                        if area.type == "VIEW_3D":
                            area.tag_redraw()
            except Exception:
                pass
            return None

        bpy.app.timers.register(_reload, first_interval=Icon._RELOAD_DELAY)

    @staticmethod
    def get_icon_id(name: Path):
        import bpy

        prev = Icon._ensure_prev()
        p: bpy.types.ImagePreview = prev.get(FSWatcher.to_str(name), None)
        if not p:
            p = prev.get(FSWatcher.to_str(Icon.NONE_IMAGE), None)
        return p.icon_id if p else 0

    def __getitem__(self, name):
        return Icon.get_icon_id(name)

    def __contains__(self, name):
        return FSWatcher.to_str(name) in Icon._ensure_prev()

    def __class_getitem__(cls, name):
        return cls.__getitem__(cls, name)
