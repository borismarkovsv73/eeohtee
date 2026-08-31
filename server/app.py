from flask import Flask, jsonify

from settings import load_settings
from server.influx_writer import InfluxWriter
from server.mqtt_ingest import start_subscriber
from server.latest_cache import snapshot

app = Flask(__name__)

settings = load_settings('server/settings.json')
influx_writer = InfluxWriter(settings['influxdb'])
mqtt_client = start_subscriber(settings['mqtt'], influx_writer)


@app.get('/health')
def health():
    return jsonify({"status": "ok"})


@app.get('/api/latest')
def latest():
    return jsonify(snapshot())


@app.get('/camera')
def camera_view():
    return app.send_static_file('camera.html')


if __name__ == '__main__':
    http_settings = settings.get('http', {})
    app.run(host=http_settings.get('host', '0.0.0.0'), port=http_settings.get('port', 5000))
