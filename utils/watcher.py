import queue
import time
import platform
from threading import Thread
from pathlib import Path
from functools import lru_cache
from .logger import logger


class FSWatcher:
    """
    监听文件/文件夹变化的工具类
        register: 注册监听, 传入路径和回调函数(可空)
        unregister: 注销监听
        run: 监听循环, 使用单例,只在第一次初始化时调用
        stop: 停止监听, 释放资源
        consume_change: 消费变化, 当监听对象发生变化时记录为changed, 主动消费后置False, 用于自定义回调函数
    """
    _watcher_path: dict[Path, bool] = {}
    _watcher_stat = {}
    _watcher_callback = {}
    _watcher_queue = queue.Queue()
    _running = False

    @classmethod
    def init(cls) -> None:
        cls._run()

    @classmethod
    def register(cls, path, callback=None):
        path = cls.to_path(path)
        if path in cls._watcher_path:
            return
        cls._watcher_path[path] = False
        cls._watcher_callback[path] = callback

    @classmethod
    def unregister(cls, path):
        path = cls.to_path(path)
        cls._watcher_path.pop(path)
        cls._watcher_callback.pop(path)

    @classmethod
    def _run(cls):
        if cls._running:
            return
        cls._running = True
        Thread(target=cls._loop, daemon=True).start()
        Thread(target=cls._run_ex, daemon=True).start()

    @classmethod
    def _run_ex(cls):
        while cls._running:
            try:
                path = cls._watcher_queue.get(timeout=0.1)
                if path not in cls._watcher_path:
                    continue
                if callback := cls._watcher_callback[path]:
                    callback(path)
            except queue.Empty:
                pass

    @classmethod
    def _loop(cls):
        """
            监听所有注册的路径, 有变化时记录为changed
        """
        while cls._running:
            # list() avoid changed while iterating
            for path, changed in list(cls._watcher_path.items()):
                if changed:
                    continue
                if not path.exists():
                    continue
                mtime = path.stat().st_mtime_ns
                if cls._watcher_stat.get(path, None) == mtime:
                    continue
                cls._watcher_stat[path] = mtime
                cls._watcher_path[path] = True
                cls._watcher_queue.put(path)
            time.sleep(0.5)

    @classmethod
    def stop(cls):
        cls._watcher_queue.put(None)
        cls._running = False

    @classmethod
    def consume_change(cls, path) -> bool:
        path = cls.to_path(path)
        if path in cls._watcher_path and cls._watcher_path[path]:
            cls._watcher_path[path] = False
            return True
        return False

    @classmethod
    @lru_cache(maxsize=1024)
    def get_nas_mapping(cls):
        if platform.system() != "Windows":
            return {}
        import subprocess
        try:
            result = subprocess.run("net use", capture_output=True, text=True, encoding="gbk", check=True)
        except subprocess.CalledProcessError as e:
            logger.warning(e)
            return {}
        if result.returncode != 0 or result.stdout is None:
            return {}
        nas_mapping = {}
        try:
            lines = result.stdout.strip().split("\n")[4:]
            for line in lines:
                columns = line.split()
                if len(columns) < 3:
                    continue
                local_drive = columns[1] + "/"
                nas_path = Path(columns[2]).resolve().as_posix()
                nas_mapping[local_drive] = nas_path
        except Exception:
            ...
        return nas_mapping

    @classmethod
    @lru_cache(maxsize=1024)
    def to_str(cls, path: Path):
        p = Path(path)
        try:
            res_str = p.resolve().as_posix()
        except FileNotFoundError as e:
            res_str = p.as_posix()
            logger.warning(e)
        # 处理nas路径
        for local_drive, nas_path in cls.get_nas_mapping().items():
            if not res_str.startswith(nas_path):
                continue
            return res_str.replace(nas_path, local_drive)
        return res_str

    @classmethod
    @lru_cache(maxsize=1024)
    def to_path(cls, path: Path):
        return Path(path)


FSWatcher.init()
