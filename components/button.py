from simulators.button import run_button_simulator
from sensors.button import run_button_loop
from mqtt_client.buffer import enqueue_reading
from mqtt_client.topics import resolve_topic
from verbosity import is_verbose
import threading
import time


def button_callback(pressed, code, name):
    if not is_verbose():
        return
    t = time.localtime()
    state = "Pressed" if pressed else "Released"
    print("="*20 + f"\nName: {name}\nTimestamp: {time.strftime('%H:%M:%S', t)}\nCode: {code}\nState: {state}\n")


def run_button(settings, threads, stop_event, name, mqtt_settings, device_settings, on_press=None):
    simulated = settings['simulated']
    topic = resolve_topic(mqtt_settings, settings, device_settings, name)

    def callback(pressed, code, sensor_name):
        button_callback(pressed, code, sensor_name)
        enqueue_reading(topic, sensor_name, code, pressed, simulated)
        if pressed and on_press:
            on_press()

    if simulated:
        print(f"Starting {name} simulator")
        sensor_thread = threading.Thread(
            target=run_button_simulator, args=(3, callback, stop_event, name)
        )
        sensor_thread.start()
        threads.append(sensor_thread)
        print(f"{name} simulator started")
    else:
        from sensors.button import Button
        print(f"Starting {name} loop")
        button = Button(settings['pin'])
        sensor_thread = threading.Thread(
            target=run_button_loop, args=(button, 0.1, callback, stop_event, name)
        )
        sensor_thread.start()
        threads.append(sensor_thread)
        print(f"{name} loop started")

    return callback
