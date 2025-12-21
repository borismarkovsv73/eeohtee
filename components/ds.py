from simulators.ds import run_ds_simulator
from sensors.ds import run_ds_loop
import threading
import time


def ds_callback(state, code, name):
    t = time.localtime()
    door_state = "Pressed" if state else "Released"
    print("="*20 + f"\nName: {name}\nTimestamp: {time.strftime('%H:%M:%S', t)}\nCode: {code}\nState: {door_state}\n")


def run_ds(settings, threads, stop_event, name, dl_queue, db_queue):
    if settings['simulated']:
        print(f"Starting {name} simulator")
        sensor_thread = threading.Thread(
            target=run_ds_simulator, args=(3, ds_callback, stop_event, name, dl_queue, db_queue)
        )
        sensor_thread.start()
        threads.append(sensor_thread)
        print(f"{name} simulator started")
    else:
        from sensors.ds import DS1
        print(f"Starting {name} loop")
        ds = DS1(settings['pin'])
        sensor_thread = threading.Thread(
            target=run_ds_loop, args=(ds, 0.1, ds_callback, stop_event, name, dl_queue, db_queue)
        )
        sensor_thread.start()
        threads.append(sensor_thread)
        print(f"{name} loop started")
