import time

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
    motion_off_at = None
    while not stop_event.is_set():
        timeout = delay if motion_off_at is None else max(0, min(delay, motion_off_at - time.time()))
        try:
            event = queue.get(timeout=timeout)

            if isinstance(event, dict):
                code = event.get("code")
                if code in ["MANUAL_ON", "MANUAL_OFF"]:
                    new_state = event.get("state", False)
                    motion_off_at = None
                    if new_state and not is_on:
                        dl.on()
                        is_on = True
                        callback(is_on, code, name)
                    elif not new_state and is_on:
                        dl.off()
                        is_on = False
                        callback(is_on, code, name)
                elif code == "MOTION_ON":
                    motion_off_at = time.time() + event.get("duration", 10)
                    if not is_on:
                        dl.on()
                        is_on = True
                        callback(is_on, code, name)
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

        if motion_off_at is not None and time.time() >= motion_off_at and is_on:
            dl.off()
            is_on = False
            motion_off_at = None
            callback(is_on, "MOTION_TIMEOUT", name)
