from simulators.pir import run_pir_simulator
from sensors.pir import run_pir_loop
import threading
import time


def pir_callback(motion, code, name):
    t = time.localtime()
    motion_state = "Motion detected" if motion else "No motion"
    print("="*20 + f"\nName: {name}\nTimestamp: {time.strftime('%H:%M:%S', t)}\nCode: {code}\nState: {motion_state}\n")


def run_pir(settings, threads, stop_event, name):
    if settings['simulated']:
        print(f"Starting {name} simulator")
        sensor_thread = threading.Thread(
            target=run_pir_simulator, args=(3, pir_callback, stop_event, name)
        )
        sensor_thread.start()
        threads.append(sensor_thread)
        print(f"{name} simulator started")
    else:
        from sensors.pir import DPIR1
        print(f"Starting {name} loop")
        pir = DPIR1(settings['pin'])
        sensor_thread = threading.Thread(
            target=run_pir_loop, args=(pir, 0.5, pir_callback, stop_event, name)
        )
        sensor_thread.start()
        threads.append(sensor_thread)
        print(f"{name} loop started")
