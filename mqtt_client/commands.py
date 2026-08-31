import json
import threading

import paho.mqtt.client as mqtt


def start_command_subscriber(mqtt_settings, device_settings, queues_by_code, stop_event):
    """Lets the server (or anything else) remotely drive a PI's actuators
    without touching actuator code at all: subscribes to
    '<prefix>/<pi_id>/<code>/cmd' for every code in queues_by_code, and
    forwards the JSON payload straight onto that actuator's existing
    queue - the exact same queue the console's manual commands use.
    """
    prefix = mqtt_settings.get("topic_prefix", "smarthome")
    pi_id = device_settings.get("pi_id", "PI1")

    def on_connect(client, userdata, flags, rc):
        for code in queues_by_code:
            topic = f"{prefix}/{pi_id}/{code}/cmd"
            client.subscribe(topic)

    def on_message(client, userdata, msg):
        parts = msg.topic.split('/')
        if len(parts) < 4:
            return
        code = parts[2]
        queue = queues_by_code.get(code)
        if queue is None:
            return
        try:
            message = json.loads(msg.payload.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return
        queue.put(message)

    client = mqtt.Client(client_id=f"{pi_id}-cmd-subscriber")
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
