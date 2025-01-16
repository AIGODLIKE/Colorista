from .watcher import FSWatcher
from .timer import Timer
from pathlib import Path

IMG_SUFFIX = {".png", ".jpg", ".jpeg"}


class PrevMgr:
    import bpy
    __PREV__: dict[int, bpy.utils.previews.ImagePreviewCollection] = {}

    @staticmethod
    def new() -> bpy.utils.previews.ImagePreviewCollection:
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

    @staticmethod
    def clear():
        for prev in PrevMgr.__PREV__.values():
            prev.clear()
            prev.close()
        PrevMgr.__PREV__.clear()


class MetaIn(type):
    def __contains__(cls, name):
        return cls.__contains__(cls, name)


class Icon(metaclass=MetaIn):
    PREV_DICT = PrevMgr.new()
    NONE_IMAGE = ""
    IMG_STATUS = {}
    PIX_STATUS = {}
    PATH2BPY = {}
    ENABLE_HQ_PREVIEW = True
    INSTANCE = None

    def __init__(self) -> None:
        if Icon.NONE_IMAGE and Icon.NONE_IMAGE not in Icon:
            Icon.NONE_IMAGE = FSWatcher.to_str(Icon.NONE_IMAGE)
            self.reg_icon(Icon.NONE_IMAGE)

    def __new__(cls, *args, **kwargs):
        if cls.INSTANCE is None:
            cls.INSTANCE = object.__new__(cls, *args, **kwargs)
        return cls.INSTANCE

    @staticmethod
    def update_path2bpy():
        import bpy
        Icon.PATH2BPY.clear()
        for i in bpy.data.images:
            Icon.PATH2BPY[FSWatcher.to_str(i.filepath)] = i

    @staticmethod
    def apply_alpha(img):
        if img.file_format != "PNG" or img.channels < 4:
            return
        # 预乘alpha 到rgb
        import numpy as np
        pixels = np.zeros(img.size[0] * img.size[1] * 4, dtype=np.float32)
        img.pixels.foreach_get(pixels)
        sized_pixels = pixels.reshape(-1, 4)
        sized_pixels[:, :3] *= sized_pixels[:, 3].reshape(-1, 1)
        img.pixels.foreach_set(pixels)

    @staticmethod
    def clear():
        Icon.PREV_DICT.clear()
        Icon.IMG_STATUS.clear()
        Icon.PIX_STATUS.clear()
        Icon.PATH2BPY.clear()
        Icon.reg_icon(Icon.NONE_IMAGE)

    @staticmethod
    def set_hq_preview():
        # from .preference import get_pref
        # Icon.ENABLE_HQ_PREVIEW = get_pref().enable_hq_preview
        return

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
    def can_mark_pixel(prev, name) -> bool:
        name = FSWatcher.to_str(name)
        if Icon.PIX_STATUS.get(name) == hash(prev.pixels):
            return False
        Icon.PIX_STATUS[name] = hash(prev.pixels)
        return True

    @staticmethod
    def remove_mark(name) -> bool:
        name = FSWatcher.to_str(name)
        Icon.IMG_STATUS.pop(name)
        Icon.PIX_STATUS.pop(name)
        Icon.PREV_DICT.pop(name)
        return True

    @staticmethod
    def reg_none(none: Path):
        none = FSWatcher.to_str(none)
        if none in Icon:
            return
        Icon.NONE_IMAGE = none
        Icon.reg_icon(Icon.NONE_IMAGE)

    @staticmethod
    def reg_icon(path, reload=False, hq=False):
        path = FSWatcher.to_str(path)
        if not Icon.can_mark_image(path):
            return Icon[path]
        if Icon.ENABLE_HQ_PREVIEW and hq:
            try:
                Icon.reg_icon_hq(path)
            except BaseException:
                Timer.put((Icon.reg_icon_hq, path))
            return Icon[path]
        else:
            if path not in Icon:
                Icon.PREV_DICT.load(path, path, 'IMAGE')
            if reload:
                Timer.put(Icon.PREV_DICT[path].reload)
            return Icon[path]

    @staticmethod
    def reg_icon_hq(path):
        import bpy
        p = FSWatcher.to_path(path)
        path = FSWatcher.to_str(path)
        if path in Icon:
            return
        if p.exists() and p.suffix.lower() in IMG_SUFFIX:
            img = bpy.data.images.load(path)
            Icon.apply_alpha(img)
            Icon.reg_icon_by_pixel(img, path)
            Timer.put((bpy.data.images.remove, img))  # 直接使用 bpy.data.images.remove 会导致卡死

    @staticmethod
    def find_image(path):
        img = Icon.PATH2BPY.get(FSWatcher.to_str(path), None)
        if not img:
            return None
        try:
            _ = img.name  # hack ref detect
            return img
        except ReferenceError:
            Icon.update_path2bpy()
        return None

    @staticmethod
    def load_icon(path):
        import bpy
        p = FSWatcher.to_path(path)
        path = FSWatcher.to_str(path)

        if not Icon.can_mark_image(path):
            return

        # if p.name[:63] in bpy.data.images:
        #     img = bpy.data.images[p.name[:63]]
        #     Icon.update_icon_pixel(img.name, img)
        if img := Icon.find_image(path):
            Icon.update_icon_pixel(path, img)
            return img
        elif p.suffix.lower() in IMG_SUFFIX:
            img = bpy.data.images.load(path)
            img.filepath = path
            Icon.apply_alpha(img)
            Icon.update_path2bpy()
            # img.name = path
            return img

    @staticmethod
    def reg_icon_by_pixel(prev, name):
        name = FSWatcher.to_str(name)
        if not Icon.can_mark_pixel(prev, name):
            return
        if name in Icon:
            return
        p = Icon.PREV_DICT.new(name)
        p.icon_size = (32, 32)
        p.image_size = (prev.size[0], prev.size[1])
        p.image_pixels_float[:] = prev.pixels[:]

    @staticmethod
    def get_icon_id(name: Path):
        import bpy
        p: bpy.types.ImagePreview = Icon.PREV_DICT.get(FSWatcher.to_str(name), None)
        if not p:
            p = Icon.PREV_DICT.get(FSWatcher.to_str(Icon.NONE_IMAGE), None)
        return p.icon_id if p else 0

    @staticmethod
    def update_icon_pixel(name, prev):
        """
        更新bpy.data.image 时一并更新(因为pixel 的hash 不变)
        """
        prev.reload()
        p = Icon.PREV_DICT.get(name, None)
        if not p:
            # logger.error("No")
            return
        p.icon_size = (32, 32)
        p.image_size = (prev.size[0], prev.size[1])
        p.image_pixels_float[:] = prev.pixels[:]

    def __getitem__(self, name):
        return Icon.get_icon_id(name)

    def __contains__(self, name):
        return FSWatcher.to_str(name) in Icon.PREV_DICT

    def __class_getitem__(cls, name):
        return cls.__getitem__(cls, name)
