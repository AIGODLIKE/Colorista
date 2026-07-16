"""Read preference values for services (single place that imports prefs)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ColoristaConfig:
    use_asset_color_space_pref: bool = False
    cache_current_compositor: bool = True
    cache_current_cache_count: int = 10
    force_use_cpu_render_image: bool = False
    main_node_group_name: str = "Basic adjustment nodes for colorists"
    use_custom_presets_path: bool = False
    presets_path: str = ""
    ui_icon_scale: float = 8.0
    gizmo_offset: int = 0
    enable_logging: bool = False

    @property
    def custom_presets_root(self) -> str | None:
        if self.use_custom_presets_path and self.presets_path.strip():
            return self.presets_path
        return None


def get_config() -> ColoristaConfig:
    from ..preferences import get_pref

    pref = get_pref()
    if pref is None:
        return ColoristaConfig()
    return ColoristaConfig(
        use_asset_color_space_pref=bool(pref.use_asset_color_space_pref),
        cache_current_compositor=bool(pref.cache_current_compositor),
        cache_current_cache_count=int(pref.cache_current_cache_count),
        force_use_cpu_render_image=bool(pref.force_use_cpu_render_image),
        main_node_group_name=pref.main_node_group_name or ColoristaConfig.main_node_group_name,
        use_custom_presets_path=bool(pref.use_custom_presets_path),
        presets_path=pref.presets_path or "",
        ui_icon_scale=float(pref.ui_icon_scale),
        gizmo_offset=int(pref.gizmo_offset),
        enable_logging=bool(pref.enable_logging),
    )
