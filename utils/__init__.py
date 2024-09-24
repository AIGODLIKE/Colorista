from .timer import timer_reg, timer_unreg


def register_util():
    """Register all the utils."""
    timer_reg()


def unregister_util():
    """Unregister all the utils."""
    timer_unreg()
