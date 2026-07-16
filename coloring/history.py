"""History service: indexed cache, atomic writes, deferred flush, dedupe."""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import bpy

from .preset import io as preset_io
from ..utils.logger import logger
from ..utils.node import scene_uses_compositor
from ..utils.paths import get_user_cache_dir
from ..utils.timer import Timer
from .config import get_config

INDEX_NAME = "index.json"
INDEX_VERSION = 1
THROTTLE_SECONDS = 1.0


@dataclass
class HistoryEntry:
    id: str
    file: str
    name: str
    asset: str = ""
    hash: str = ""
    mtime: float = 0.0


@dataclass
class _PendingSnapshot:
    scene_name: str
    asset_path: str
    data: dict[str, Any]
    content_hash: str
    created_at: float = field(default_factory=time.monotonic)


_pending: _PendingSnapshot | None = None
_flush_scheduled = False


def _index_path(cache_dir: Path | None = None) -> Path:
    return (cache_dir or get_user_cache_dir()).joinpath(INDEX_NAME)


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _atomic_write_json(path: Path, data: Any) -> None:
    _atomic_write_text(path, json.dumps(data, indent=2, ensure_ascii=False))


def _content_hash(data: dict) -> str:
    payload = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def _cleanup_legacy_blend(cache_dir: Path) -> None:
    for file in cache_dir.glob("*.blend"):
        if file.is_file():
            try:
                file.unlink()
            except OSError:
                pass


def _entry_from_dict(raw: dict) -> HistoryEntry | None:
    try:
        return HistoryEntry(
            id=str(raw["id"]),
            file=str(raw["file"]),
            name=str(raw.get("name") or raw["id"]),
            asset=str(raw.get("asset") or ""),
            hash=str(raw.get("hash") or ""),
            mtime=float(raw.get("mtime") or 0.0),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _load_index(cache_dir: Path | None = None) -> list[HistoryEntry]:
    cache_dir = cache_dir or get_user_cache_dir()
    path = _index_path(cache_dir)
    if path.is_file():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            entries_raw = raw.get("entries") if isinstance(raw, dict) else None
            if isinstance(entries_raw, list):
                entries = []
                for item in entries_raw:
                    if not isinstance(item, dict):
                        continue
                    entry = _entry_from_dict(item)
                    if entry is None:
                        continue
                    if not Path(entry.file).is_file():
                        continue
                    entries.append(entry)
                return entries
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning("History index corrupt, rebuilding: %s", e)
    return _rebuild_index_from_files(cache_dir)


def _rebuild_index_from_files(cache_dir: Path) -> list[HistoryEntry]:
    _cleanup_legacy_blend(cache_dir)
    entries: list[HistoryEntry] = []
    for file in sorted(cache_dir.glob("*.json"), reverse=True):
        if file.name == INDEX_NAME or not file.is_file():
            continue
        asset = ""
        digest = ""
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                asset = str(data.get("asset") or "")
                digest = _content_hash(data)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            logger.warning("Skipping corrupt history file: %s", file)
            continue
        try:
            mtime = file.stat().st_mtime
        except OSError:
            mtime = 0.0
        entries.append(
            HistoryEntry(
                id=file.stem,
                file=file.as_posix(),
                name=file.stem,
                asset=asset,
                hash=digest,
                mtime=mtime,
            )
        )
    _save_index(entries, cache_dir)
    return entries


def _save_index(entries: list[HistoryEntry], cache_dir: Path | None = None) -> None:
    cache_dir = cache_dir or get_user_cache_dir()
    payload = {
        "version": INDEX_VERSION,
        "entries": [
            {
                "id": e.id,
                "file": e.file,
                "name": e.name,
                "asset": e.asset,
                "hash": e.hash,
                "mtime": e.mtime,
            }
            for e in entries
        ],
    }
    try:
        _atomic_write_json(_index_path(cache_dir), payload)
    except OSError as e:
        logger.error("Failed to write history index: %s", e)


def _trim_entries(entries: list[HistoryEntry], limit: int) -> list[HistoryEntry]:
    if limit < 1:
        limit = 1
    keep = entries[:limit]
    for old in entries[limit:]:
        path = Path(old.file)
        if path.is_file():
            try:
                path.unlink()
            except OSError:
                pass
    return keep


def sync_ui_list(context: bpy.types.Context | None = None, *, entries: list[HistoryEntry] | None = None) -> None:
    """Incrementally sync Scene.history_items to the index (full replace only here)."""
    try:
        context = context or bpy.context
        prop = context.scene.colorista_prop
    except Exception:
        return
    if entries is None:
        entries = _load_index()
    cfg = get_config()
    entries = _trim_entries(entries, cfg.cache_current_cache_count)
    try:
        prop.history_items.clear()
        for entry in entries:
            item = prop.history_items.add()
            item.name = entry.name
            item.file = entry.file
    except Exception as e:
        logger.error("Sync history UI failed: %s", e)


def refresh_from_disk(context: bpy.types.Context | None = None) -> None:
    """Rebuild index from files and refresh UI (load_post / pref count change)."""
    cache_dir = get_user_cache_dir()
    _cleanup_legacy_blend(cache_dir)
    entries = _rebuild_index_from_files(cache_dir)
    cfg = get_config()
    entries = _trim_entries(entries, cfg.cache_current_cache_count)
    _save_index(entries, cache_dir)
    sync_ui_list(context, entries=entries)


def prepend_ui_item(context: bpy.types.Context | None, entry: HistoryEntry) -> None:
    try:
        context = context or bpy.context
        prop = context.scene.colorista_prop
        item = prop.history_items.add()
        item.name = entry.name
        item.file = entry.file
        last = len(prop.history_items) - 1
        if last > 0:
            prop.history_items.move(last, 0)
        limit = get_config().cache_current_cache_count
        while len(prop.history_items) > limit:
            prop.history_items.remove(len(prop.history_items) - 1)
    except Exception as e:
        logger.error("Prepend history UI failed: %s", e)


def remove_entry(context: bpy.types.Context | None, file: Path | str) -> bool:
    target = Path(file)
    cache_dir = get_user_cache_dir()
    entries = _load_index(cache_dir)
    new_entries = []
    removed_from_index = False
    for entry in entries:
        if Path(entry.file).as_posix() == target.as_posix() or entry.id == target.stem:
            removed_from_index = True
            path = Path(entry.file)
            if path.is_file():
                try:
                    path.unlink()
                except OSError:
                    pass
            continue
        new_entries.append(entry)
    if removed_from_index:
        _save_index(new_entries, cache_dir)
    elif target.is_file():
        try:
            target.unlink()
        except OSError:
            pass

    removed_from_ui = False
    try:
        context = context or bpy.context
        prop = context.scene.colorista_prop
        target_posix = target.as_posix()
        for i, item in enumerate(list(prop.history_items)):
            if item.file == target_posix or Path(item.file).as_posix() == target_posix:
                prop.history_items.remove(i)
                removed_from_ui = True
                break
    except Exception as e:
        logger.error("Remove history UI failed: %s", e)
    return removed_from_index or removed_from_ui


def capture_pending_snapshot(
    context: bpy.types.Context,
    scene: bpy.types.Scene,
    asset_path: Path | str,
) -> None:
    """Build an in-memory snapshot before a load (no disk I/O)."""
    global _pending
    cfg = get_config()
    if not cfg.cache_current_compositor:
        _pending = None
        return
    if not scene_uses_compositor(scene):
        return
    try:
        data = preset_io.dump_scene_preset(scene, asset_path)
    except Exception:
        logger.exception("Failed to capture history snapshot")
        return
    digest = _content_hash(data)
    _pending = _PendingSnapshot(
        scene_name=scene.name,
        asset_path=str(asset_path),
        data=data,
        content_hash=digest,
    )


def schedule_flush(context: bpy.types.Context | None = None) -> None:
    """Defer writing the pending snapshot to disk."""
    global _flush_scheduled
    if _pending is None:
        return
    if _flush_scheduled:
        return
    _flush_scheduled = True
    Timer.put(_flush_pending)


def _flush_pending() -> None:
    global _pending, _flush_scheduled
    _flush_scheduled = False
    snap = _pending
    _pending = None
    if snap is None:
        return
    try:
        _commit_snapshot(snap, bpy.context)
    except Exception:
        logger.exception("Deferred history flush failed")


def _commit_snapshot(snap: _PendingSnapshot, context: bpy.types.Context) -> None:
    cfg = get_config()
    if not cfg.cache_current_compositor:
        return
    cache_dir = get_user_cache_dir()
    entries = _load_index(cache_dir)
    if entries and entries[0].hash == snap.content_hash:
        return
    # Throttle: replace a very recent same-asset pending write by skipping near-duplicates.
    now = time.time()
    if entries and entries[0].asset == snap.data.get("asset", "") and (now - entries[0].mtime) < THROTTLE_SECONDS:
        if entries[0].hash == snap.content_hash:
            return

    name = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    # Avoid collisions when multiple snaps land in the same second.
    path = cache_dir.joinpath(f"{name}.json")
    if path.exists():
        name = datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")
        path = cache_dir.joinpath(f"{name}.json")

    try:
        _atomic_write_json(path, snap.data)
    except OSError as e:
        logger.error("Failed to write history file: %s", e)
        return

    entry = HistoryEntry(
        id=path.stem,
        file=path.as_posix(),
        name=path.stem,
        asset=str(snap.data.get("asset") or ""),
        hash=snap.content_hash,
        mtime=time.time(),
    )
    entries.insert(0, entry)
    entries = _trim_entries(entries, cfg.cache_current_cache_count)
    _save_index(entries, cache_dir)
    prepend_ui_item(context, entry)


def apply_limit_change(context: bpy.types.Context | None = None) -> None:
    cache_dir = get_user_cache_dir()
    entries = _trim_entries(_load_index(cache_dir), get_config().cache_current_cache_count)
    _save_index(entries, cache_dir)
    sync_ui_list(context, entries=entries)


# Back-compat aliases used during migration
def update_history(context=None) -> None:
    refresh_from_disk(context)


def append_history_item(context, file: Path) -> None:
    entry = HistoryEntry(id=file.stem, file=file.as_posix(), name=file.stem, mtime=time.time())
    entries = _load_index()
    entries.insert(0, entry)
    entries = _trim_entries(entries, get_config().cache_current_cache_count)
    _save_index(entries)
    prepend_ui_item(context, entry)


def remove_history_item(context, file: Path | str) -> None:
    remove_entry(context, file)
