import bpy
from collections import deque
from typing import Any
from .logger import logger


class Timer:
    """Deferred main-thread callbacks via ``bpy.app.timers``.

    Used to run work *after* the current RNA update / draw finishes
    (nested ID writes from property updates are unsafe).
    Unregisters itself when the queue is empty.
    """

    TimerQueue = deque()
    _registered = False

    @classmethod
    def put(cls, delegate: Any):
        cls.TimerQueue.append(delegate)
        if not cls._registered:
            cls.reg()
            cls._registered = True

    @classmethod
    def executor(cls, t):
        if isinstance(t, (list, tuple)):
            t[0](*t[1:])
        else:
            t()

    @classmethod
    def run(cls):
        return cls.run_ex(cls.TimerQueue)

    @classmethod
    def run_ex(cls, queue: deque):
        while queue:
            t = queue.popleft()
            try:
                cls.executor(t)
            except Exception as e:
                logger.error("%s: %s", type(e).__name__, e)
            except KeyboardInterrupt:
                ...
        # Stop the timer; next put() will register again.
        cls._registered = False
        return None

    @classmethod
    def clear(cls):
        cls.TimerQueue.clear()

    @classmethod
    def reg(cls):
        bpy.app.timers.register(cls.run, persistent=True)

    @classmethod
    def unreg(cls):
        cls.clear()
        cls._registered = False
        try:
            bpy.app.timers.unregister(cls.run)
        except Exception:
            ...


def register():
    pass


def unregister():
    Timer.unreg()
