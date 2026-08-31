import json
import threading
import time

import paho.mqtt.client as mqtt

from mqtt_client.buffer import buffer


def _connect(mqtt_settings):
    client_id = mqtt_settings.get("client_id", "pi-publisher")
    client = mqtt.Client(client_id=client_id)
    client.connect(mqtt_settings.get("broker", "localhost"), mqtt_settings.get("port", 1883))
    client.loop_start()
    return client


def _publish_batches(client, drained):
    if not drained:
        return 0, 0
    grouped = {}
    for topic, reading in drained:
        grouped.setdefault(topic, []).append(reading)
    for topic, readings in grouped.items():
        payload = json.dumps({"count": len(readings), "readings": readings})
        client.publish(topic, payload, qos=1)
    return len(drained), len(grouped)


def run_publisher_daemon(mqtt_settings, stop_event):
    """Generic batching daemon: works for every sensor/actuator type,
    since it only ever moves opaque (topic, reading) pairs out of the buffer.
    """
    if stop_event.is_set():
        return
    client = _connect(mqtt_settings)
    interval = mqtt_settings.get("batch_interval", 5)
    print(f"[MQTT] publisher daemon started (broker={mqtt_settings.get('broker')}, batch_interval={interval}s)")
    try:
        while not stop_event.is_set():
            stop_event.wait(interval)
            drained = buffer.drain()
            count, topics = _publish_batches(client, drained)
            if count:
                print(f"[MQTT] published {count} reading(s) across {topics} topic(s)")
    finally:
        # give the background network thread a moment to flush any
        # in-flight publish from the final drain before disconnecting
        time.sleep(0.3)
        client.loop_stop()
        client.disconnect()
        print("[MQTT] publisher daemon stopped")


def start_publisher_daemon(mqtt_settings, stop_event, threads):
    thread = threading.Thread(
        target=run_publisher_daemon, args=(mqtt_settings, stop_event), daemon=True
    )
    thread.start()
    threads.append(thread)
    return thread
