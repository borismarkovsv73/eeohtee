import threading

_lock = threading.Lock()
_verbose = True


def set_verbose(value):
    global _verbose
    with _lock:
        _verbose = value


def is_verbose():
    with _lock:
        return _verbose
