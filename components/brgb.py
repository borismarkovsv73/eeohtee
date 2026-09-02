from simulators.brgb import run_brgb_simulator
from actuators.brgb import run_brgb_loop
from mqtt_client.buffer import enqueue_reading
from mqtt_client.topics import resolve_topic
from verbosity import is_verbose
import threading
import time


def brgb_callback(color, code, name):
    if not is_verbose():
        return
    r, g, b = color
    t = time.localtime()
    print("="*20 + f"\nName: {name}\nTimestamp: {time.strftime('%H:%M:%S', t)}\nCode: {code}\nColor: rgb({r}, {g}, {b})\n")


def run_brgb(settings, threads, stop_event, name, queue, mqtt_settings, device_settings):
    simulated = settings['simulated']
    topic = resolve_topic(mqtt_settings, settings, device_settings, name)

    def callback(color, code, sensor_name):
        brgb_callback(color, code, sensor_name)
        r, g, b = color
        enqueue_reading(topic, sensor_name, code, r, simulated, extra={"field": "r"})
        enqueue_reading(topic, sensor_name, code, g, simulated, extra={"field": "g"})
        enqueue_reading(topic, sensor_name, code, b, simulated, extra={"field": "b"})

    callback((0, 0, 0), "STARTUP", name)

    if simulated:
        print(f"Starting {name} simulator")
        actuator_thread = threading.Thread(
            target=run_brgb_simulator, args=(5, callback, stop_event, name, queue)
        )
        actuator_thread.start()
        threads.append(actuator_thread)
        print(f"{name} simulator started")
    else:
        from actuators.brgb import BRGB
        print(f"Starting {name} loop")
        pins = settings['pins']
        brgb = BRGB(pins['r'], pins['g'], pins['b'])
        actuator_thread = threading.Thread(
            target=run_brgb_loop, args=(brgb, 5, callback, stop_event, name, queue)
        )
        actuator_thread.start()
        threads.append(actuator_thread)
        print(f"{name} loop started")
