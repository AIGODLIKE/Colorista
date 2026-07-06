from pathlib import Path

import bpy

from ...utils.common import get_resource_dir_locale, get_resource_dir
from ...utils.icon import Icon
from ...utils.logger import logger
from ...utils.watcher import FSWatcher

PROP_TCTX = "ColoristaTCTX"
PANEL_TCTX = "ColoristaPanelTCTX"


def _enum_index(items, value: str) -> int:
    for i, item in enumerate(items):
        if item[0] == value:
            return i
    return 0


class Props(bpy.types.PropertyGroup):
    loaded_node_groups = set()
    PRESET_NONE_ID = "__NONE__"

    def enable_coloring_f(self):
        bpy.ops.wm.colorista_compositor_import(use_default=True)

    def disable_coloring_f(self, context: bpy.types.Context):
        from .runtime import deactivate

        deactivate()

    def update_enable_coloring(self, context: bpy.types.Context):
        if self.enable_coloring:
            logger.info("Coloring enabled")
            self.enable_coloring_f()
            from .runtime import activate

            activate()
        else:
            logger.info("Coloring disabled")
            self.disable_coloring_f(context)

    enable_coloring: bpy.props.BoolProperty(default=False,
                                            name="Enable Coloring",
                                            description="Enable Coloring",
                                            update=update_enable_coloring,
                                            translation_context=PROP_TCTX)

    _ref_items = {}

    def pre_dir_items(self, context):
        rdir = get_resource_dir_locale()
        FSWatcher.register(rdir)
        if not FSWatcher.consume_change(rdir) and rdir in self._ref_items:
            return self._ref_items.get(rdir, [])
        items = []
        self._ref_items[rdir] = items
        for f in rdir.iterdir():
            if f.is_file():
                continue
            items.append((f.as_posix(), f.name, f.name, 0, len(items)))
        items.sort(key=lambda x: x[1])
        return self._ref_items.get(rdir, [])

    pre_dir: bpy.props.EnumProperty(name="Asset Category",
                                    items=pre_dir_items,
                                    translation_context=PROP_TCTX)

    def find_icon(self, name: str, path: Path) -> Path:
        SUFFIXES = [".png", ".jpg", ".jpeg", ".tiff"]
        for suf in SUFFIXES:
            img = path.joinpath(name).with_suffix(suf)
            if not img.exists():
                continue
            return img
        return get_resource_dir().joinpath("icons/None.png")

    def asset_items(self, context):
        if not self.pre_dir:
            return []
        rdir = Path(self.pre_dir)
        FSWatcher.register(rdir)
        if not FSWatcher.consume_change(rdir) and rdir in self._ref_items:
            return self._ref_items.get(rdir, [])
        items = []
        self._ref_items[rdir] = items
        for f in sorted(rdir.glob("*.blend"), key=lambda x: x.name):
            icon_path = self.find_icon(f.stem, rdir)
            Icon.reg_icon(icon_path.as_posix(), hq=True)
            icon_id = Icon.get_icon_id(icon_path)
            items.append((f.as_posix(), f.stem, f.stem, icon_id, len(items)))
        return self._ref_items.get(rdir, [])

    def set_asset(self, value):
        self["asset"] = value
        bpy.ops.wm.colorista_compositor_import()

    def get_asset(self):
        try:
            items = self.asset_items(bpy.context)
        except AttributeError:
            return ""

        valid = {item[0] for item in items}
        current = self.get("asset", "")
        if current not in valid:
            current = items[0][0] if items else ""
            self["asset"] = current
        return current

    asset: bpy.props.EnumProperty(name="Asset",
                                  items=asset_items,
                                  get=get_asset,
                                  set=set_asset,
                                  translation_context=PROP_TCTX)

    def update_last_asset(self, context):
        if not self.last_asset:
            return
        self.last_asset = False
        items = self.asset_items(context)
        if not items:
            return
        idx = _enum_index(items, self.asset)
        self.asset = items[(idx - 1) % len(items)][0]

    last_asset: bpy.props.BoolProperty(default=False,
                                       name="Last Asset",
                                       update=update_last_asset,
                                       translation_context=PROP_TCTX,
                                       )

    def update_next_asset(self, context):
        if not self.next_asset:
            return
        self.next_asset = False
        items = self.asset_items(context)
        if not items:
            return
        idx = _enum_index(items, self.asset)
        self.asset = items[(idx + 1) % len(items)][0]

    next_asset: bpy.props.BoolProperty(default=False,
                                       name="Next Asset",
                                       update=update_next_asset,
                                       translation_context=PROP_TCTX,
                                       )

    def get_presets(self, context):
        asset = self.asset
        if not asset:
            return [(self.PRESET_NONE_ID, "None", "No preset available", 0)]
        rdir = Path(asset).with_suffix("")
        FSWatcher.register(rdir)
        if not FSWatcher.consume_change(rdir) and rdir in self._ref_items:
            return self._ref_items.get(rdir, [])
        items = []
        self._ref_items[rdir] = items
        for file in sorted(rdir.glob("*.blend"), key=lambda x: x.name):
            items.append((file.as_posix(), file.stem, file.stem, len(items)))
        if not items:
            items.append((self.PRESET_NONE_ID, "None", "No preset available", 0))
        return self._ref_items.get(rdir, [])

    def set_preset(self, value):
        self["preset"] = value
        if self.preset != self.PRESET_NONE_ID:
            bpy.ops.wm.colorista_compositor_import(preset=self.preset)

    def get_preset(self):
        try:
            items = self.get_presets(bpy.context)
        except AttributeError:
            return self.PRESET_NONE_ID

        valid = {item[0] for item in items}
        current = self.get("preset", self.PRESET_NONE_ID)
        if current not in valid:
            current = items[0][0] if items else self.PRESET_NONE_ID
            self["preset"] = current
        return current

    preset: bpy.props.EnumProperty(name="Preset",
                                   items=get_presets,
                                   get=get_preset,
                                   set=set_preset,
                                   translation_context=PROP_TCTX,
                                   )

    def update_last_preset(self, context):
        if not self.last_preset:
            return
        self.last_preset = False
        items = self.get_presets(context)
        if not items:
            return
        idx = _enum_index(items, self.preset)
        self.preset = items[(idx - 1) % len(items)][0]

    last_preset: bpy.props.BoolProperty(default=False,
                                        name="Last Preset",
                                        update=update_last_preset,
                                        translation_context=PROP_TCTX,
                                        )

    def update_next_preset(self, context):
        if not self.next_preset:
            return
        self.next_preset = False
        items = self.get_presets(context)
        if not items:
            return
        idx = _enum_index(items, self.preset)
        self.preset = items[(idx + 1) % len(items)][0]

    next_preset: bpy.props.BoolProperty(default=False,
                                        name="Next Preset",
                                        update=update_next_preset,
                                        translation_context=PROP_TCTX,
                                        )

    preset_save_name: bpy.props.StringProperty(name="Save Name",
                                               default="",
                                               translation_context=PROP_TCTX,
                                               )


@bpy.app.handlers.persistent
def reload_handler(sce):
    Props.loaded_node_groups.clear()
    try:
        if sce.colorista_prop.enable_coloring:
            from .runtime import activate

            activate()
    except AttributeError:
        pass


clss = (
    Props,
)

reg, unreg = bpy.utils.register_classes_factory(clss)


def register():
    reg()
    bpy.types.Scene.colorista_prop = bpy.props.PointerProperty(type=Props)
    bpy.types.Node.ac_expand = bpy.props.BoolProperty(name="Expand", default=True)
    bpy.app.handlers.load_post.append(reload_handler)


def unregister():
    from .runtime import deactivate

    deactivate()
    unreg()
    bpy.app.handlers.load_post.remove(reload_handler)
    del bpy.types.Node.ac_expand
    del bpy.types.Scene.colorista_prop
