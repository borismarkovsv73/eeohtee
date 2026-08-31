import random
import time


def run_dht_simulator(delay, callback, stop_event, name):
    while not stop_event.is_set():
        temperature = round(random.uniform(18.0, 28.0), 1)
        humidity = round(random.uniform(30.0, 60.0), 1)
        callback((temperature, humidity), "DHT_READING", name)
        time.sleep(delay)
