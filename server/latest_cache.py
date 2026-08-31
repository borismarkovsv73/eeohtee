import threading

_lock = threading.Lock()
_latest = {}


def update(pi_id, sensor_code, reading):
    with _lock:
        _latest[f"{pi_id}/{sensor_code}"] = reading


def snapshot():
    with _lock:
        return dict(_latest)
