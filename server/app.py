import threading

from flask import Flask, jsonify, request

from settings import load_settings
from server.influx_writer import InfluxWriter
from server.mqtt_ingest import start_subscriber
from server.latest_cache import snapshot
from server.command_publisher import CommandPublisher
from server.alarm import AlarmEngine

app = Flask(__name__)

settings = load_settings('server/settings.json')
influx_writer = InfluxWriter(settings['influxdb'])
command_publisher = CommandPublisher(settings['mqtt'])
_alarm_stop_event = threading.Event()
alarm_engine = AlarmEngine(influx_writer, command_publisher, settings.get('alarm', {}), _alarm_stop_event)
mqtt_client = start_subscriber(settings['mqtt'], influx_writer, alarm_engine)


@app.get('/health')
def health():
    return jsonify({"status": "ok"})


@app.get('/api/latest')
def latest():
    return jsonify(snapshot())


@app.get('/api/alarm')
def alarm_status():
    return jsonify(alarm_engine.snapshot())


@app.post('/api/alarm/disarm')
def alarm_disarm():
    data = request.get_json(silent=True) or {}
    pin = str(data.get('pin', ''))
    if pin != alarm_engine.pin:
        return jsonify({"ok": False, "error": "invalid pin"}), 403
    alarm_engine.disarm_via_web()
    return jsonify({"ok": True, "state": alarm_engine.snapshot()})


@app.post('/api/timer/set')
def timer_set():
    data = request.get_json(silent=True) or {}
    try:
        seconds = int(data.get('seconds', 0))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "seconds must be an integer"}), 400
    command_publisher.send('PI2', 'TIMER', {"code": "SET_TIME", "seconds": seconds})
    return jsonify({"ok": True})


@app.post('/api/timer/config')
def timer_config():
    data = request.get_json(silent=True) or {}
    try:
        seconds = int(data.get('add_seconds', 30))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "add_seconds must be an integer"}), 400
    command_publisher.send('PI2', 'TIMER', {"code": "SET_INCREMENT", "seconds": seconds})
    return jsonify({"ok": True})


@app.post('/api/brgb')
def brgb_set():
    data = request.get_json(silent=True) or {}
    if data.get('on') is False:
        command_publisher.send('PI3', 'BRGB', {"code": "MANUAL_OFF", "color": (0, 0, 0)})
        return jsonify({"ok": True})
    try:
        color = (int(data['r']), int(data['g']), int(data['b']))
    except (KeyError, TypeError, ValueError):
        return jsonify({"ok": False, "error": "expected r, g, b integers (or on: false)"}), 400
    command_publisher.send('PI3', 'BRGB', {"code": "MANUAL_SET", "color": color})
    return jsonify({"ok": True})


@app.post('/api/pi/<pi_id>/command')
def pi_command(pi_id):
    pi_id = pi_id.upper()
    if pi_id not in ('PI1', 'PI2', 'PI3'):
        return jsonify({"ok": False, "error": "unknown PI"}), 404
    data = request.get_json(silent=True) or {}
    command = str(data.get('command', '')).strip()
    if not command:
        return jsonify({"ok": False, "error": "missing command"}), 400
    command_publisher.send(pi_id, 'console', {"command": command})
    return jsonify({"ok": True, "queued": command})


@app.get('/api/config')
def web_config():
    web_settings = settings.get('web', {})
    return jsonify({
        "webc_url": web_settings.get('webc_url', 'http://localhost:8080/?action=stream'),
        "grafana_url": web_settings.get('grafana_url'),
    })


@app.get('/camera')
def camera_view():
    return app.send_static_file('camera.html')


@app.get('/')
def dashboard_view():
    return app.send_static_file('dashboard.html')


if __name__ == '__main__':
    http_settings = settings.get('http', {})
    app.run(host=http_settings.get('host', '0.0.0.0'), port=http_settings.get('port', 5000))
