import threading

_lock = threading.Lock()
_latest = {}


def update(pi_id, sensor_code, reading):
    """Keyed by (pi_id, sensor_code, field) rather than just (pi_id,
    sensor_code) - a multi-field device like DHT (temperature+humidity)
    or BRGB (r/g/b) would otherwise have each new field overwrite the
    last, losing everything but whichever field happened to arrive most
    recently.
    """
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
