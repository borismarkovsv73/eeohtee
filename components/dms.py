from simulators.dms import run_dms_simulator
from sensors.dms import run_dms_loop
from mqtt_client.buffer import enqueue_reading
from mqtt_client.topics import resolve_topic
from verbosity import is_verbose
import threading
import time


def dms_callback(key, code, name):
    if not is_verbose():
        return
    t = time.localtime()
    print("="*20 + f"\nName: {name}\nTimestamp: {time.strftime('%H:%M:%S', t)}\nCode: {code}\nKey: {key}\n")


def run_dms(settings, threads, stop_event, name, mqtt_settings, device_settings):
    simulated = settings['simulated']
    topic = resolve_topic(mqtt_settings, settings, device_settings, name)

    def callback(key, code, sensor_name):
        dms_callback(key, code, sensor_name)
        enqueue_reading(topic, sensor_name, code, key, simulated)

    if simulated:
        print(f"Starting {name} simulator")
        keypad_thread = threading.Thread(
            target=run_dms_simulator, args=(2, callback, stop_event, name)
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
            target=run_dms_loop, args=(dms, 0.1, callback, stop_event, name)
        )
        keypad_thread.start()
        threads.append(keypad_thread)
        print(f"{name} loop started")

    return callback
