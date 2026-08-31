from simulators.uds import run_uds_simulator
from sensors.uds import run_uds_loop
from mqtt_client.buffer import enqueue_reading
from mqtt_client.topics import resolve_topic
import threading
import time


def uds_callback(distance, code, name):
    t = time.localtime()
    print("="*20 + f"\nName: {name}\nTimestamp: {time.strftime('%H:%M:%S', t)}\nCode: {code}\nDistance: {distance:.2f} cm\n")


def run_uds(settings, threads, stop_event, name, mqtt_settings, device_settings):
    simulated = settings['simulated']
    topic = resolve_topic(mqtt_settings, settings, device_settings, name)

    def callback(distance, code, sensor_name):
        uds_callback(distance, code, sensor_name)
        enqueue_reading(topic, sensor_name, code, distance, simulated)

    if simulated:
        print(f"Starting {name} simulator")
        sensor_thread = threading.Thread(
            target=run_uds_simulator, args=(2, callback, stop_event, name)
        )
        sensor_thread.start()
        threads.append(sensor_thread)
        print(f"{name} simulator started")
    else:
        from sensors.uds import DUS1
        print(f"Starting {name} loop")
        uds = DUS1(settings['trig_pin'], settings['echo_pin'])
        sensor_thread = threading.Thread(
            target=run_uds_loop, args=(uds, 0.5, callback, stop_event, name)
        )
        sensor_thread.start()
        threads.append(sensor_thread)
        print(f"{name} loop started")
