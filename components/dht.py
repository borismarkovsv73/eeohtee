from simulators.dht import run_dht_simulator
from sensors.dht import run_dht_loop
from mqtt_client.buffer import enqueue_reading
from mqtt_client.topics import resolve_topic
from verbosity import is_verbose
import threading
import time


def dht_callback(reading, code, name):
    if not is_verbose():
        return
    temperature, humidity = reading
    t = time.localtime()
    print("="*20 + f"\nName: {name}\nTimestamp: {time.strftime('%H:%M:%S', t)}\nCode: {code}\nTemperature: {temperature}C\nHumidity: {humidity}%\n")


def run_dht(settings, threads, stop_event, name, mqtt_settings, device_settings):
    simulated = settings['simulated']
    topic = resolve_topic(mqtt_settings, settings, device_settings, name)

    def callback(reading, code, sensor_name):
        dht_callback(reading, code, sensor_name)
        temperature, humidity = reading
        enqueue_reading(topic, sensor_name, code, temperature, simulated, extra={"field": "temperature"})
        enqueue_reading(topic, sensor_name, code, humidity, simulated, extra={"field": "humidity"})

    if simulated:
        print(f"Starting {name} simulator")
        sensor_thread = threading.Thread(
            target=run_dht_simulator, args=(5, callback, stop_event, name)
        )
        sensor_thread.start()
        threads.append(sensor_thread)
        print(f"{name} simulator started")
    else:
        from sensors.dht import DHT
        print(f"Starting {name} loop")
        dht = DHT(settings['pin'])
        sensor_thread = threading.Thread(
            target=run_dht_loop, args=(dht, 3, callback, stop_event, name)
        )
        sensor_thread.start()
        threads.append(sensor_thread)
        print(f"{name} loop started")
