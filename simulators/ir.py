import random
import time

REMOTE_CODES = ["0x45", "0x46", "0x47", "0x44", "0x40", "0x43", "0x07", "0x15", "0x09", "0x19"]


def run_ir_simulator(delay, callback, stop_event, name):
    while not stop_event.is_set():
        if random.random() > 0.9:
            code = random.choice(REMOTE_CODES)
            callback(code, "IR_CODE", name)
        time.sleep(delay)
