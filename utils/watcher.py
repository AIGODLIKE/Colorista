from functools import lru_cache
from pathlib import Path

from .logger import logger


class FSWatcher:
    """On-demand path mtime checks (no background timer / polling).

    register: seed a path for later comparisons
    consume_change: compare mtime now; True if changed since last consume/seed
    """
    _watcher_path: dict[Path, bool] = {}
    _watcher_stat: dict[Path, int | None] = {}
    _enabled = False

    @classmethod
    def enable(cls) -> None:
        cls._enabled = True

    @classmethod
    def disable(cls) -> None:
        cls._enabled = False
        cls.clear()

    @classmethod
    def clear(cls) -> None:
        cls._watcher_path.clear()
        cls._watcher_stat.clear()

    @classmethod
    def register(cls, path, callback=None):
        del callback  # unused; kept for call-site compatibility
        path = cls.to_path(path)
        if not path or path in cls._watcher_path:
            return
        cls._watcher_path[path] = False
        cls._watcher_stat[path] = cls._read_mtime(path)

    @classmethod
    def unregister(cls, path):
        path = cls.to_path(path)
        cls._watcher_path.pop(path, None)
        cls._watcher_stat.pop(path, None)

    @classmethod
    def _read_mtime(cls, path: Path) -> int | None:
        try:
            if path.exists():
                return path.stat().st_mtime_ns
        except OSError:
            pass
        return None

    @classmethod
    def _poll_one(cls, path: Path) -> None:
        if path not in cls._watcher_path:
            return
        if cls._watcher_path[path]:
            return
        mtime = cls._read_mtime(path)
        if cls._watcher_stat.get(path) == mtime:
            return
        cls._watcher_stat[path] = mtime
        cls._watcher_path[path] = True

    @classmethod
    def consume_change(cls, path) -> bool:
        if not cls._enabled:
            return False
        path = cls.to_path(path)
        if not path:
            return False
        if path not in cls._watcher_path:
            cls.register(path)
        cls._poll_one(path)
        if cls._watcher_path.get(path):
            cls._watcher_path[path] = False
            return True
        return False

    @classmethod
    def stop(cls):
        cls.clear()

    @classmethod
    @lru_cache(maxsize=1024)
    def to_str(cls, path: Path):
        p = Path(path)
        try:
            return p.resolve().as_posix()
        except FileNotFoundError as e:
            logger.warning(e)
            return p.as_posix()

    @classmethod
    @lru_cache(maxsize=1024)
    def to_path(cls, path: Path):
        if not path:
            return ""
        return Path(path)


def register():
    pass


def unregister():
    FSWatcher.stop()
