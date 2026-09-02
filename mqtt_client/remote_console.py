import json
import threading

import paho.mqtt.client as mqtt

from console import dispatch_command


def start_remote_console(mqtt_settings, device_settings, by_code, stop_event):
    prefix = mqtt_settings.get("topic_prefix", "smarthome")
    pi_id = device_settings.get("pi_id", "PI1")
    topic = f"{prefix}/{pi_id}/console/cmd"

    def on_connect(client, userdata, flags, rc):
        client.subscribe(topic)

    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return
        command = payload.get("command", "")
        if not command:
            return
        ok, message = dispatch_command(command, by_code)
        status = "ok" if ok else "error"
        suffix = f": {message}" if message else ""
        print(f"[remote] {command} -> {status}{suffix}")

    client = mqtt.Client(client_id=f"{pi_id}-remote-console")
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
