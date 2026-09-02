import json
import threading

import paho.mqtt.client as mqtt


def start_remote_reading_subscriber(mqtt_settings, subscriptions, stop_event):
    prefix = mqtt_settings.get("topic_prefix", "smarthome")
    callbacks_by_topic = {}
    for pi_id, sensor_code, callback in subscriptions:
        topic = f"{prefix}/{pi_id}/{sensor_code}"
        callbacks_by_topic[topic] = callback

    def on_connect(client, userdata, flags, rc):
        for topic in callbacks_by_topic:
            client.subscribe(topic)

    def on_message(client, userdata, msg):
        callback = callbacks_by_topic.get(msg.topic)
        if callback is None:
            return
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return
        for reading in payload.get('readings', []):
            callback(reading)

    client_id = mqtt_settings.get("client_id", "pi-remote") + "-remote"
    client = mqtt.Client(client_id=client_id)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(mqtt_settings.get("broker", "localhost"), mqtt_settings.get("port", 1883))
    client.loop_start()

    def watch_stop():
        stop_event.wait()
        client.loop_stop()
        client.disconnect()

    watcher = threading.Thread(target=watch_stop, daemon=True)
    watcher.start()
    return client
