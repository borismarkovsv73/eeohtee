from simulators.dl import run_dl_simulator
from actuators.dl import run_dl_loop
from mqtt_client.buffer import enqueue_reading
from mqtt_client.topics import resolve_topic
from verbosity import is_verbose
import threading
import time


def dl_callback(state, code, name):
    if not is_verbose():
        return
    t = time.localtime()
    led_state = "ON" if state else "OFF"
    print("="*20 + f"\nName: {name}\nTimestamp: {time.strftime('%H:%M:%S', t)}\nCode: {code}\nState: {led_state}\n")


def run_dl(settings, threads, stop_event, name, queue, mqtt_settings, device_settings):
    simulated = settings['simulated']
    topic = resolve_topic(mqtt_settings, settings, device_settings, name)

    def callback(state, code, sensor_name):
        dl_callback(state, code, sensor_name)
        enqueue_reading(topic, sensor_name, code, state, simulated)

    callback(False, "STARTUP", name)

    if simulated:
        print(f"Starting {name} simulator")
        led_thread = threading.Thread(
            target=run_dl_simulator, args=(5, callback, stop_event, name, queue)
        )
        led_thread.start()
        threads.append(led_thread)
        print(f"{name} simulator started")
    else:
        from actuators.dl import DL
        print(f"Starting {name} loop")
        dl = DL(settings['pin'])
        led_thread = threading.Thread(
            target=run_dl_loop, args=(dl, 5, callback, stop_event, name, queue)
        )
        led_thread.start()
        threads.append(led_thread)
        print(f"{name} loop started")
