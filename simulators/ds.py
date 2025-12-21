import random
import time

def run_ds_simulator(delay, callback, stop_event, name, dl_queue, db_queue):
    pressed = False
    while not stop_event.is_set():
        if random.random() > 0.85:
            pressed = not pressed
            if pressed:
                code = "DS_PRESSED"
                dl_queue.put("DOOR_UNLOCKED")
                db_queue.put("DOOR_UNLOCKED")
            else:
                code = "DS_RELEASED"
                dl_queue.put("DOOR_LOCKED")
                db_queue.put("DOOR_LOCKED")
            callback(pressed, code, name)
        time.sleep(delay)
