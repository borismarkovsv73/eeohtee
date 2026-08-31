from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import WriteOptions


class InfluxWriter(object):
    """Wraps the InfluxDB client's own batching write API (it maintains its
    own internal buffer/flush thread), so no additional locking is needed
    here - writes are just handed off.
    """

    def __init__(self, influx_settings):
        self._bucket = influx_settings['bucket']
        self._org = influx_settings['org']
        self._client = InfluxDBClient(
            url=influx_settings['url'],
            token=influx_settings['token'],
            org=self._org,
        )
        self._write_api = self._client.write_api(
            write_options=WriteOptions(batch_size=50, flush_interval=2000)
        )

    def write_readings(self, pi_id, sensor_code, readings):
        points = []
        for reading in readings:
            point = (
                Point(sensor_code)
                .tag("pi_id", pi_id)
                .tag("simulated", str(bool(reading.get("simulated"))).lower())
                .field("code", str(reading.get("code", "")))
            )
            field = reading.get("field", "value")
            value = reading.get("value")
            if isinstance(value, bool):
                point = point.field(field, value)
            elif isinstance(value, (int, float)):
                point = point.field(field, float(value))
            else:
                point = point.field(field, str(value))

            timestamp = reading.get("timestamp")
            if timestamp is not None:
                point = point.time(int(timestamp * 1e9))

            points.append(point)

        if points:
            self._write_api.write(bucket=self._bucket, org=self._org, record=points)

    def close(self):
        self._write_api.close()
        self._client.close()
