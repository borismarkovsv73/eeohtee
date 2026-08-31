from simulators.sd4 import run_sd4_simulator
from actuators.sd4 import run_sd4_loop
from mqtt_client.buffer import enqueue_reading
from mqtt_client.topics import resolve_topic
from verbosity import is_verbose
import threading
import time


def sd4_callback(state, code, name):
    if not is_verbose():
        return
    value, blinking = state
    t = time.localtime()
    print("="*20 + f"\nName: {name}\nTimestamp: {time.strftime('%H:%M:%S', t)}\nCode: {code}\nDisplay: {value}\nBlinking: {blinking}\n")


def run_sd4(settings, threads, stop_event, name, queue, mqtt_settings, device_settings):
    simulated = settings['simulated']
    topic = resolve_topic(mqtt_settings, settings, device_settings, name)

    def callback(state, code, sensor_name):
        sd4_callback(state, code, sensor_name)
        value, blinking = state
        enqueue_reading(topic, sensor_name, code, value, simulated, extra={"field": "display"})
        enqueue_reading(topic, sensor_name, code, blinking, simulated, extra={"field": "blinking"})

    if simulated:
        print(f"Starting {name} simulator")
        actuator_thread = threading.Thread(
            target=run_sd4_simulator, args=(2, callback, stop_event, name, queue)
        )
        actuator_thread.start()
        threads.append(actuator_thread)
        print(f"{name} simulator started")
    else:
        from actuators.sd4 import FourDigitDisplay
        print(f"Starting {name} loop")
        pins = settings['pins']
        display = FourDigitDisplay(pins['segments'], pins['digits'])
        actuator_thread = threading.Thread(
            target=run_sd4_loop, args=(display, 2, callback, stop_event, name, queue)
        )
        actuator_thread.start()
        threads.append(actuator_thread)
        print(f"{name} loop started")
