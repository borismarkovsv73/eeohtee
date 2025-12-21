from simulators.uds import run_uds_simulator
from sensors.uds import run_uds_loop
import threading
import time


def uds_callback(distance, code, name):
    t = time.localtime()
    print("="*20 + f"\nName: {name}\nTimestamp: {time.strftime('%H:%M:%S', t)}\nCode: {code}\nDistance: {distance:.2f} cm\n")


def run_uds(settings, threads, stop_event, name):
    if settings['simulated']:
        print(f"Starting {name} simulator")
        sensor_thread = threading.Thread(
            target=run_uds_simulator, args=(2, uds_callback, stop_event, name)
        )
        sensor_thread.start()
        threads.append(sensor_thread)
        print(f"{name} simulator started")
    else:
        from sensors.uds import DUS1
        print(f"Starting {name} loop")
        uds = DUS1(settings['trig_pin'], settings['echo_pin'])
        sensor_thread = threading.Thread(
            target=run_uds_loop, args=(uds, 0.5, uds_callback, stop_event, name)
        )
        sensor_thread.start()
        threads.append(sensor_thread)
        print(f"{name} loop started")
