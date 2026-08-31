def run_db_simulator(delay, callback, stop_event, name, queue):
    # two independent flags on purpose - see actuators/db.py for why
    buzzing = False
    alarm_active = False
    while not stop_event.is_set():
        try:
            event = queue.get(timeout=delay)

            if isinstance(event, dict):
                code = event.get("code")
                if code == "MANUAL_BUZZ":
                    buzzing = True
                    callback(buzzing, "MANUAL_BUZZ", name)
                    buzzing = False
                elif code == "ALARM_ON" and not alarm_active:
                    alarm_active = True
                    callback(True, "ALARM_ON", name)
                elif code == "ALARM_OFF" and alarm_active:
                    alarm_active = False
                    callback(False, "ALARM_OFF", name)
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
