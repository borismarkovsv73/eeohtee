from simulators.gsg import run_gsg_simulator
from sensors.gsg import run_gsg_loop
from mqtt_client.buffer import enqueue_reading
from mqtt_client.topics import resolve_topic
from verbosity import is_verbose
import threading
import time


def gsg_callback(moved, code, name):
    if not is_verbose():
        return
    t = time.localtime()
    state = "Movement detected" if moved else "Still"
    print("="*20 + f"\nName: {name}\nTimestamp: {time.strftime('%H:%M:%S', t)}\nCode: {code}\nState: {state}\n")


def run_gsg(settings, threads, stop_event, name, mqtt_settings, device_settings):
    simulated = settings['simulated']
    topic = resolve_topic(mqtt_settings, settings, device_settings, name)

    def callback(moved, code, sensor_name):
        gsg_callback(moved, code, sensor_name)
        enqueue_reading(topic, sensor_name, code, moved, simulated)

    if simulated:
        print(f"Starting {name} simulator")
        sensor_thread = threading.Thread(
            target=run_gsg_simulator, args=(2, callback, stop_event, name)
        )
        sensor_thread.start()
        threads.append(sensor_thread)
        print(f"{name} simulator started")
    else:
        from sensors.gsg import GSG
        print(f"Starting {name} loop")
        gsg = GSG(settings['pin'])
        sensor_thread = threading.Thread(
            target=run_gsg_loop, args=(gsg, 0.2, callback, stop_event, name)
        )
        sensor_thread.start()
        threads.append(sensor_thread)
        print(f"{name} loop started")
