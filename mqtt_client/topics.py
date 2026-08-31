def resolve_topic(mqtt_settings, sensor_settings, device_settings, sensor_code):
    """Topic can be pinned per-sensor in settings.json (sensor_settings['topic']),
    otherwise it is derived generically as '<prefix>/<pi_id>/<sensor_code>'.
    """
    if sensor_settings and sensor_settings.get("topic"):
        return sensor_settings["topic"]
    prefix = mqtt_settings.get("topic_prefix", "smarthome")
    pi_id = device_settings.get("pi_id", "PI1")
    return f"{prefix}/{pi_id}/{sensor_code}"
