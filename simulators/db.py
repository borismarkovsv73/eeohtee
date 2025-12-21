def run_db_simulator(delay, callback, stop_event, name, queue):
    buzzing = False
    while not stop_event.is_set():
        try:
            event = queue.get(timeout=delay)
            
            if isinstance(event, dict):
                if event.get("code") == "MANUAL_BUZZ":
                    buzzing = True
                    callback(buzzing, "MANUAL_BUZZ", name)
                    buzzing = False
            elif event == "DOOR_LOCKED" and buzzing:
                buzzing = False
                code = "DB_OK"
                callback(buzzing, code, name)
            elif event == "DOOR_UNLOCKED" and not buzzing:
                buzzing = True
                code = "DB_OK"
                callback(buzzing, code, name)
        except:
            pass
