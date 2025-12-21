import random
import time

def run_uds_simulator(delay, callback, stop_event, name):
    while not stop_event.is_set():
        distance = random.uniform(10, 200)
        code = "UDS_OK"
        callback(distance, code, name)
        time.sleep(delay)
