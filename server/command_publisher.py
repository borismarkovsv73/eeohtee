import json

import paho.mqtt.client as mqtt


class CommandPublisher(object):
    def __init__(self, mqtt_settings):
        self._topic_prefix = mqtt_settings.get("topic_prefix", "smarthome")
        client_id = mqtt_settings.get("client_id", "smarthome-server") + "-cmd"
        self._client = mqtt.Client(client_id=client_id)
        self._client.connect(mqtt_settings.get("broker", "localhost"), mqtt_settings.get("port", 1883))
        self._client.loop_start()

    def send(self, pi_id, code, message):
        topic = f"{self._topic_prefix}/{pi_id}/{code}/cmd"
        self._client.publish(topic, json.dumps(message), qos=1)

    def close(self):
        self._client.loop_stop()
        self._client.disconnect()
