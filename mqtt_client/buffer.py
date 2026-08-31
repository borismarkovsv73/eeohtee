import threading
import time


class ReadingBuffer(object):
    """Thread-safe collection point for sensor/actuator readings.

    Producers (sensor callbacks) call add() from many different threads.
    The publisher daemon calls drain() once per batch interval. The lock
    only ever guards a single list append or a list swap, so no producer
    or consumer ever blocks for longer than that, and no other lock is
    ever acquired while this one is held - so deadlock is not reachable.
    """

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
