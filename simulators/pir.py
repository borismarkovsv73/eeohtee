import random
import time

def run_pir_simulator(delay, callback, stop_event, name):
    motion = False
    while not stop_event.is_set():
        if random.random() > 0.8:
            motion = not motion
            code = "PIR_MOTION" if motion else "PIR_CLEAR"
            callback(motion, code, name)
        time.sleep(delay)
