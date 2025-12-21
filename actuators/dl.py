try:
    import RPi.GPIO as GPIO
except:
    pass

class DL(object):
    def __init__(self, pin):
        self.pin = pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin, GPIO.OUT)

    def on(self):
        GPIO.output(self.pin, True)

    def off(self):
        GPIO.output(self.pin, False)


def run_dl_loop(dl, delay, callback, stop_event, name, queue):
    is_on = False
    while not stop_event.is_set():
        try:
            event = queue.get(timeout=delay)
            
            if isinstance(event, dict):
                if event.get("code") in ["MANUAL_ON", "MANUAL_OFF"]:
                    new_state = event.get("state", False)
                    if new_state and not is_on:
                        dl.on()
                        is_on = True
                        callback(is_on, event.get("code"), name)
                    elif not new_state and is_on:
                        dl.off()
                        is_on = False
                        callback(is_on, event.get("code"), name)
            elif event == "DOOR_LOCKED" and is_on:
                dl.off()
                is_on = False
                code = "DL_OK"
                callback(is_on, code, name)
            elif event == "DOOR_UNLOCKED" and not is_on:
                dl.on()
                is_on = True
                code = "DL_OK"
                callback(is_on, code, name)
        except:
            pass
