def run_dl_simulator(delay, callback, stop_event, name, queue):
    is_on = False
    while not stop_event.is_set():
        try:
            event = queue.get(timeout=delay)
            
            if isinstance(event, dict):
                if event.get("code") in ["MANUAL_ON", "MANUAL_OFF"]:
                    new_state = event.get("state", False)
                    if new_state != is_on:
                        is_on = new_state
                        callback(is_on, event.get("code"), name)
            elif event == "DOOR_LOCKED" and is_on:
                is_on = False
                code = "DL_OK"
                callback(is_on, code, name)
            elif event == "DOOR_UNLOCKED" and not is_on:
                is_on = True
                code = "DL_OK"
                callback(is_on, code, name)
        except:
            pass
