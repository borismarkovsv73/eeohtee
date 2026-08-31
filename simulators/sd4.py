def run_sd4_simulator(delay, callback, stop_event, name, queue):
    buffer_ = "    "
    blinking = False
    while not stop_event.is_set():
        try:
            event = queue.get(timeout=delay)
            if not isinstance(event, dict):
                continue
            if event.get("code") == "MANUAL_SET":
                buffer_ = event.get("value", "    ")[:4].rjust(4)
                callback((buffer_, blinking), event.get("code"), name)
            elif event.get("code") == "MANUAL_BLINK":
                blinking = event.get("state", False)
                callback((buffer_, blinking), event.get("code"), name)
        except:
            pass
