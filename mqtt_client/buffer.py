import threading
import time


class ReadingBuffer(object):
    def __init__(self):
        self._lock = threading.Lock()
        self._items = []

    def add(self, topic, reading):
        with self._lock:
            self._items.append((topic, reading))

    def drain(self):
        with self._lock:
            items, self._items = self._items, []
        return items


buffer = ReadingBuffer()


def enqueue_reading(topic, sensor_code, code, value, simulated, extra=None):
    reading = {
        "sensor": sensor_code,
        "code": code,
        "value": value,
        "simulated": simulated,
        "timestamp": time.time(),
    }
    if extra:
        reading.update(extra)
    buffer.add(topic, reading)
