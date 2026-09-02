import threading

_lock = threading.Lock()
_latest = {}


def update(pi_id, sensor_code, reading):
    field = reading.get("field", "value")
    with _lock:
        _latest[f"{pi_id}/{sensor_code}/{field}"] = reading


def snapshot():
    with _lock:
        flat = dict(_latest)

    grouped = {}
    for key, reading in flat.items():
        pi_id, sensor_code, field = key.split("/", 2)
        device_key = f"{pi_id}/{sensor_code}"
        grouped.setdefault(device_key, {})[field] = reading
    return grouped
