import logging
from logging import handlers
from pathlib import Path

NAME = __package__

L = logging.WARNING

FMTDICT = {
    'DEBUG': ["[36m", "DBG"],
    'INFO': ["[37m", "INF"],
    'WARN': ["[33m", "WRN"],
    'WARNING': ["[33m", "WRN"],
    'ERROR': ["[31m", "ERR"],
    'CRITICAL': ["[35m", "CRT"],
}


def _get_logfile() -> Path:
    try:
        import bpy
        parts = __package__.rsplit(".", 1)
        root = parts[0] if parts else __package__
        return Path(bpy.utils.extension_path_user(root)).joinpath("logs", "runtime.log")
    except Exception:
        return Path(__file__).resolve().parent.joinpath("logs", "runtime.log")


LOGFILE = _get_logfile()


class KcHandler(logging.StreamHandler):
    with_same_line = False

    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream

            is_same_line = getattr(record, "same_line", False)
            was_same_line = self.with_same_line
            self.with_same_line = is_same_line

            if was_same_line and not is_same_line:
                stream.write(self.terminator)

            end = "" if is_same_line else self.terminator
            stream.write(msg + end)
            self.flush()
        except RecursionError:
            raise
        except Exception:
            self.handleError(record)


class KcFilter(logging.Filter):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.translate_func = lambda _: _

    def fill_color(self, color_code="[37m", msg=""):
        return f'\033{color_code}{msg}\033[0m'

    def filter(self, record: logging.LogRecord) -> bool:
        color_code, level_shortname = FMTDICT.get(record.levelname, ["[37m", "UN"])
        record.msg = self.translate_func(record.msg)
        record.msg = self.fill_color(color_code, record.msg)
        record.levelname = self.fill_color(color_code, level_shortname)
        return True


class KcLogger(logging.Logger):
    def __init__(self, name, level=logging.NOTSET):
        self.closed = False
        super().__init__(name, level)

    def set_translate(self, translate_func):
        for handler in self.handlers:
            for filter in handler.filters:
                if not isinstance(filter, KcFilter):
                    continue
                filter.translate_func = translate_func

    def close(self):
        if self.closed:
            return
        self.closed = True
        for h in reversed(self.handlers[:]):
            try:
                try:
                    h.acquire()
                    h.flush()
                    h.close()
                except (OSError, ValueError):
                    pass
                finally:
                    h.release()
            except BaseException:
                ...

    def __del__(self):
        self.close()


def getLogger(name="CLOG", level=logging.WARNING, fmt='[%(name)s-%(levelname)s]: %(message)s', fmt_date="%H:%M:%S") -> KcLogger:
    fmter = logging.Formatter('[%(levelname)s]:%(filename)s>%(lineno)s: %(message)s')
    logfile = _get_logfile()
    if not logfile.parent.exists():
        logfile.parent.mkdir(parents=True, exist_ok=True)
    dfh = handlers.TimedRotatingFileHandler(filename=logfile, when='D', backupCount=2)
    dfh.setLevel(logging.CRITICAL + 1)
    dfh.setFormatter(fmter)
    filter = KcFilter()
    fmter = logging.Formatter(fmt, fmt_date)
    ch = KcHandler()
    ch.setLevel(level)
    ch.setFormatter(fmter)
    ch.addFilter(filter)

    l = KcLogger(name)
    l.setLevel(level)
    if not l.hasHandlers():
        l.addHandler(dfh)
        l.addHandler(ch)
    return l


def configure_logger(enabled: bool = False) -> None:
    level = logging.DEBUG if enabled else logging.WARNING
    logger.setLevel(level)
    for handler in logger.handlers:
        if isinstance(handler, handlers.TimedRotatingFileHandler):
            handler.setLevel(logging.DEBUG if enabled else logging.CRITICAL + 1)
        elif isinstance(handler, KcHandler):
            handler.setLevel(level)


logger = getLogger(NAME, L)
