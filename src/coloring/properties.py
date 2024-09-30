import bpy
from ...utils.logger import logger
from ...utils.watcher import FSWatcher
from ...utils.common import get_resource_dir_locale, get_resource_dir
from ...utils.icon import Icon
from ...utils.node import copy_node_properties
from pathlib import Path

PROP_TCTX = "ColoristaTCTX"
PANEL_TCTX = "ColoristaPanelTCTX"


class Props(bpy.types.PropertyGroup):
    loaded_node_groups = set()

    def enable_coloring_f(self):
        bpy.ops.colorista.compositor_nodetree_import(use_default=True)

    def update_enable_coloring(self, context: bpy.types.Context):
        logger.info("调色开启" if self.enable_coloring else "调色关闭")
        if self.enable_coloring:
            self.enable_coloring_f()

    enable_coloring: bpy.props.BoolProperty(default=False,
                                            name="Enable Coloring",
                                            description="Enable Coloring",
                                            update=update_enable_coloring,
                                            translation_context=PROP_TCTX)

    _ref_items = {}

    def pre_dir_items(self, context):
        rdir = get_resource_dir_locale()
        # TODO: exist检查速度非常慢, 慢到足已影响UI的流畅
        # if not rdir.exists():
        #     return []
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
        # TODO: exist检查速度非常慢, 慢到足已影响UI的流畅
        # if not rdir.exists():
        #     return []
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
        bpy.ops.colorista.compositor_nodetree_import()

    def get_asset(self):
        if "asset" not in self:
            self["asset"] = 0
        return self["asset"]

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
        self.asset = items[(self["asset"] - 1) % len(items)][0]

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
        self.asset = items[(self["asset"] + 1)  % len(items)][0]

    next_asset: bpy.props.BoolProperty(default=False,
                                       name="Next Asset",
                                       update=update_next_asset,
                                       translation_context=PROP_TCTX,
                                       )

    def get_presets(self, context):
        asset = self.asset
        if not asset:
            return []
        rdir = Path(asset).with_suffix("")
        # TODO: exist检查速度非常慢, 慢到足已影响UI的流畅
        # if not rdir.exists():
        #     return []
        FSWatcher.register(rdir)
        if not FSWatcher.consume_change(rdir) and rdir in self._ref_items:
            return self._ref_items.get(rdir, [])
        items = []
        self._ref_items[rdir] = items
        for file in sorted(rdir.glob("*.blend"), key=lambda x: x.name):
            items.append((file.as_posix(), file.stem, file.stem, len(items)))
        return self._ref_items.get(rdir, [])

    def set_preset(self, value):
        self["preset"] = value
        bpy.ops.colorista.compositor_nodetree_import(preset=self.preset)

    def get_preset(self):
        if "preset" not in self:
            self["preset"] = 0
        return self["preset"]

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
        self.preset = items[(self["preset"] - 1) % len(items)][0]

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
        self.preset = items[(self["preset"] + 1) % len(items)][0]

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


@bpy.app.handlers.persistent
def coloring_checker(_):
    try:
        for area in bpy.context.screen.areas:
            if area.type != "VIEW_3D":
                continue
            area.tag_redraw()
    except Exception:
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
    bpy.app.handlers.depsgraph_update_post.append(coloring_checker)


def unregister():
    unreg()
    bpy.app.handlers.load_post.remove(reload_handler)
    bpy.app.handlers.depsgraph_update_post.remove(coloring_checker)
    del bpy.types.Node.ac_expand
    del bpy.types.Scene.colorista_prop
