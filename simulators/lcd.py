def run_lcd_simulator(delay, callback, stop_event, name, queue):
    lines = ["", ""]
    while not stop_event.is_set():
        try:
            event = queue.get(timeout=delay)
            if isinstance(event, dict) and event.get("code") == "MANUAL_SET":
                line = event.get("line", 0)
                text = event.get("text", "")
                lines[line] = text
                callback(tuple(lines), event.get("code"), name)
        except:
            pass
