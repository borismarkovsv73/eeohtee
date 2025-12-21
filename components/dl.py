from simulators.dl import run_dl_simulator
from actuators.dl import run_dl_loop
import threading
import time


def dl_callback(state, code, name):
    t = time.localtime()
    led_state = "ON" if state else "OFF"
    print("="*20 + f"\nName: {name}\nTimestamp: {time.strftime('%H:%M:%S', t)}\nCode: {code}\nState: {led_state}\n")


def run_dl(settings, threads, stop_event, name, queue):
    if settings['simulated']:
        print(f"Starting {name} simulator")
        led_thread = threading.Thread(
            target=run_dl_simulator, args=(5, dl_callback, stop_event, name, queue)
        )
        led_thread.start()
        threads.append(led_thread)
        print(f"{name} simulator started")
    else:
        from actuators.dl import DL
        print(f"Starting {name} loop")
        dl = DL(settings['pin'])
        led_thread = threading.Thread(
            target=run_dl_loop, args=(dl, 5, dl_callback, stop_event, name, queue)
        )
        led_thread.start()
        threads.append(led_thread)
        print(f"{name} loop started")
