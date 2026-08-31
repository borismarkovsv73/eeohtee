from simulators.db import run_db_simulator
from actuators.db import run_db_loop
from mqtt_client.buffer import enqueue_reading
from mqtt_client.topics import resolve_topic
from verbosity import is_verbose
import threading
import time


def db_callback(state, code, name):
    if not is_verbose():
        return
    t = time.localtime()
    buzzing = "Buzzing" if state else "Not buzzing"
    print("="*20 + f"\nName: {name}\nTimestamp: {time.strftime('%H:%M:%S', t)}\nCode: {code}\nState: {buzzing}\n")


def run_db(settings, threads, stop_event, name, queue, mqtt_settings, device_settings):
    simulated = settings['simulated']
    topic = resolve_topic(mqtt_settings, settings, device_settings, name)

    def callback(state, code, sensor_name):
        db_callback(state, code, sensor_name)
        enqueue_reading(topic, sensor_name, code, state, simulated)

    if simulated:
        print(f"Starting {name} simulator")
        buzzer_thread = threading.Thread(
            target=run_db_simulator, args=(5, callback, stop_event, name, queue)
        )
        buzzer_thread.start()
        threads.append(buzzer_thread)
        print(f"{name} simulator started")
    else:
        from actuators.db import DB
        print(f"Starting {name} loop")
        db = DB(settings['pin'])
        buzzer_thread = threading.Thread(
            target=run_db_loop, args=(db, 5, callback, stop_event, name, queue)
        )
        buzzer_thread.start()
        threads.append(buzzer_thread)
        print(f"{name} loop started")
