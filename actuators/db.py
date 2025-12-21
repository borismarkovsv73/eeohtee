import time

try:
    import RPi.GPIO as GPIO
except:
    pass

class DB(object):
    def __init__(self, pin):
        self.pin = pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin, GPIO.OUT)

    def buzz(self):
        cycles = 44
        delay = 1/220
        for i in range(cycles):
            GPIO.output(self.pin, True)
            time.sleep(delay)
            GPIO.output(self.pin, False)
            time.sleep(delay)


def run_db_loop(db, delay, callback, stop_event, name, queue):
    buzzing = False
    while not stop_event.is_set():
        try:
            event = queue.get(timeout=delay)
            
            if isinstance(event, dict):
                if event.get("code") == "MANUAL_BUZZ":
                    buzzing = True
                    db.buzz()
                    callback(buzzing, "MANUAL_BUZZ", name)
                    buzzing = False
            elif event == "DOOR_LOCKED" and buzzing:
                buzzing = False
                code = "DB_OK"
                callback(buzzing, code, name)
            elif event == "DOOR_UNLOCKED" and not buzzing:
                buzzing = True
                db.buzz()
                code = "DB_OK"
                callback(buzzing, code, name)
        except:
            pass
