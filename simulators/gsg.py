import random
import time


def run_gsg_simulator(delay, callback, stop_event, name):
    moved = False
    while not stop_event.is_set():
        if random.random() > 0.92:
            moved = not moved
            code = "GSG_MOTION" if moved else "GSG_CLEAR"
            callback(moved, code, name)
        time.sleep(delay)
