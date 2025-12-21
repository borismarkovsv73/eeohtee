from simulators.dms import run_dms_simulator
from sensors.dms import run_dms_loop
import threading
import time


def dms_callback(key, code, name):
    t = time.localtime()
    print("="*20 + f"\nName: {name}\nTimestamp: {time.strftime('%H:%M:%S', t)}\nCode: {code}\nKey: {key}\n")


def run_dms(settings, threads, stop_event, name):
    if settings['simulated']:
        print(f"Starting {name} simulator")
        keypad_thread = threading.Thread(
            target=run_dms_simulator, args=(2, dms_callback, stop_event, name)
        )
        keypad_thread.start()
        threads.append(keypad_thread)
        print(f"{name} simulator started")
    else:
        from sensors.dms import DMS
        print(f"Starting {name} loop")
        pins = settings['pins']
        row_pins = [pins['R1'], pins['R2'], pins['R3'], pins['R4']]
        col_pins = [pins['C1'], pins['C2'], pins['C3'], pins['C4']]
        dms = DMS(row_pins, col_pins)
        keypad_thread = threading.Thread(
            target=run_dms_loop, args=(dms, 0.1, dms_callback, stop_event, name)
        )
        keypad_thread.start()
        threads.append(keypad_thread)
        print(f"{name} loop started")
