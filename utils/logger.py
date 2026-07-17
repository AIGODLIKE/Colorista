import logging
from logging import handlers
from pathlib import Path

NAME = __package__

FMTDICT = {
    'DEBUG': ["[36m", "DBG"],
    'INFO': ["[37m", "INF"],
    'WARN': ["[33m", "WRN"],
    'WARNING': ["[33m", "WRN"],
    'ERROR': ["[31m", "ERR"],
    'CRITICAL': ["[35m", "CRT"],
}


def _get_logfile() -> Path | None:
    """User extension data only; never write into the install tree."""
    try:
        import bpy

        # Colorista.utils → Colorista (or bl_ext.*.Colorista)
        root = __package__.rsplit(".", 1)[0]
        return Path(bpy.utils.extension_path_user(root)).joinpath("logs", "runtime.log")
    except Exception:
        return None


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
        _detach_handlers(self)


_handlers_attached = False


def _attach_handlers(log: KcLogger) -> None:
    global _handlers_attached
    kc_filter = KcFilter()
    ch = KcHandler()
    ch.setFormatter(logging.Formatter('[%(name)s-%(levelname)s]: %(message)s', "%H:%M:%S"))
    ch.addFilter(kc_filter)
    for handler in log.handlers[:]:
        log.removeHandler(handler)
        try:
            handler.close()
        except (OSError, ValueError):
            pass
    logfile = _get_logfile()
    if logfile is not None:
        try:
            logfile.parent.mkdir(parents=True, exist_ok=True)
            dfh = handlers.TimedRotatingFileHandler(
                filename=logfile, when="D", backupCount=2
            )
            dfh.setFormatter(
                logging.Formatter(
                    "[%(levelname)s]:%(filename)s>%(lineno)s: %(message)s"
                )
            )
            log.addHandler(dfh)
        except OSError:
            pass
    log.addHandler(ch)
    _handlers_attached = True


def _detach_handlers(log: KcLogger) -> None:
    global _handlers_attached
    for handler in log.handlers[:]:
        try:
            handler.close()
        except (OSError, ValueError):
            pass
        log.removeHandler(handler)
    log.addHandler(logging.NullHandler())
    log.setLevel(logging.CRITICAL + 1)
    _handlers_attached = False


def configure_logger(enabled: bool = False) -> None:
    log = logger
    log.closed = False
    if enabled:
        if not _handlers_attached:
            _attach_handlers(log)
        log.setLevel(logging.DEBUG)
        for handler in log.handlers:
            if isinstance(handler, handlers.TimedRotatingFileHandler):
                handler.setLevel(logging.DEBUG)
            elif isinstance(handler, KcHandler):
                handler.setLevel(logging.DEBUG)
    else:
        if _handlers_attached:
            _detach_handlers(log)
        else:
            log.setLevel(logging.CRITICAL + 1)


logger = KcLogger(NAME)
logger.addHandler(logging.NullHandler())
logger.setLevel(logging.CRITICAL + 1)
