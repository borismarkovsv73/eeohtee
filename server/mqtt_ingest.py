import json

import paho.mqtt.client as mqtt

from server.latest_cache import update as update_latest


def _parse_topic(topic, topic_prefix):
    # expected shape: "<prefix>/<pi_id>/<sensor_code>"
    parts = topic.split('/')
    if len(parts) < 3 or parts[0] != topic_prefix:
        return None, None
    return parts[1], parts[2]


def build_subscriber(mqtt_settings, influx_writer):
    topic_prefix = mqtt_settings.get('topic_prefix', 'smarthome')

    def on_connect(client, userdata, flags, rc):
        subscribe_topic = mqtt_settings.get('subscribe_topic', f'{topic_prefix}/#')
        client.subscribe(subscribe_topic)
        print(f"[server] subscribed to {subscribe_topic}")

    def on_message(client, userdata, msg):
        pi_id, sensor_code = _parse_topic(msg.topic, topic_prefix)
        if not pi_id or not sensor_code:
            print(f"[server] ignoring message on unexpected topic: {msg.topic}")
            return
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            print(f"[server] dropped malformed payload on {msg.topic}")
            return

        readings = payload.get('readings', [])
        if not readings:
            return

        influx_writer.write_readings(pi_id, sensor_code, readings)
        update_latest(pi_id, sensor_code, readings[-1])
        print(f"[server] stored {len(readings)} reading(s) for {pi_id}/{sensor_code}")

    client = mqtt.Client(client_id=mqtt_settings.get('client_id', 'smarthome-server'))
    client.on_connect = on_connect
    client.on_message = on_message
    return client


def start_subscriber(mqtt_settings, influx_writer):
    client = build_subscriber(mqtt_settings, influx_writer)
    client.connect(mqtt_settings.get('broker', 'localhost'), mqtt_settings.get('port', 1883))
    client.loop_start()
    return client
