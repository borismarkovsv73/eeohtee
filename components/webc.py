import threading
import time

from mqtt_client.buffer import enqueue_reading
from mqtt_client.topics import resolve_topic
from verbosity import is_verbose


def webc_callback(url, code, name):
    if not is_verbose():
        return
    t = time.localtime()
    print("="*20 + f"\nName: {name}\nTimestamp: {time.strftime('%H:%M:%S', t)}\nCode: {code}\nStream: {url}\n")


def run_webc(settings, threads, stop_event, name, mqtt_settings, device_settings):
    simulated = settings['simulated']
    topic = resolve_topic(mqtt_settings, settings, device_settings, name)
    port = settings.get('port', 8080)
    url = f"http://localhost:{port}/?action=stream"

    if simulated:
        print(f"Starting {name} simulator (MJPEG test stream on port {port})")
        from simulators.webc import run_webc_simulator
        stream_thread = threading.Thread(
            target=run_webc_simulator, args=(port, stop_event)
        )
        stream_thread.start()
        threads.append(stream_thread)
        print(f"{name} simulator started")
    else:
        print(f"Starting {name} (mjpg-streamer on port {port})")
        from sensors.webc import run_webc_process
        stream_thread = threading.Thread(
            target=run_webc_process, args=(settings, stop_event)
        )
        stream_thread.start()
        threads.append(stream_thread)
        print(f"{name} started")

    webc_callback(url, "WEBC_ONLINE", name)
    enqueue_reading(topic, name, "WEBC_ONLINE", url, simulated)
