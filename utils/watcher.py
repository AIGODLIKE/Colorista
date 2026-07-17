"""Path normalization helpers used by icon cache keys."""

from functools import lru_cache
from pathlib import Path

from .logger import logger


class FSWatcher:
    """Normalize paths for consistent dict keys (no filesystem watching)."""

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

    @classmethod
    def clear_caches(cls) -> None:
        cls.to_str.cache_clear()
        cls.to_path.cache_clear()


def register():
    pass


def unregister():
    FSWatcher.clear_caches()
