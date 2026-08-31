import random
import time


def run_button_simulator(delay, callback, stop_event, name):
    pressed = False
    while not stop_event.is_set():
        if random.random() > 0.85:
            pressed = not pressed
            code = "BTN_PRESSED" if pressed else "BTN_RELEASED"
            callback(pressed, code, name)
        time.sleep(delay)
