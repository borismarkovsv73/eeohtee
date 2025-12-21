import random
import time

def run_dms_simulator(delay, callback, stop_event, name):
    keys = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '*', '#', 'A', 'B', 'C', 'D']
    
    while not stop_event.is_set():
        if random.random() > 0.9:
            key = random.choice(keys)
            code = "DMS_KEY"
            callback(key, code, name)
        time.sleep(delay)
