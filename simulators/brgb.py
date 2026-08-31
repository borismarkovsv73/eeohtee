def run_brgb_simulator(delay, callback, stop_event, name, queue):
    color = (0, 0, 0)
    while not stop_event.is_set():
        try:
            event = queue.get(timeout=delay)
            if isinstance(event, dict) and event.get("code") in ("MANUAL_SET", "MANUAL_OFF"):
                new_color = tuple(event.get("color", (0, 0, 0)))
                if new_color != color:
                    color = new_color
                    callback(color, event.get("code"), name)
        except:
            pass
