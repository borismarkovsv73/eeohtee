import threading
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
        self._alarm_active = threading.Event()
        self._alarm_thread = None

    def buzz(self):
        cycles = 44
        delay = 1/220
        for i in range(cycles):
            GPIO.output(self.pin, True)
            time.sleep(delay)
            GPIO.output(self.pin, False)
            time.sleep(delay)

    def set_alarm(self, active):
        """Sustained buzzing for as long as ALARM is active - unlike buzz()
        (a fixed short beep), this keeps toggling the pin in a background
        thread until told to stop.
        """
        if active and not self._alarm_active.is_set():
            self._alarm_active.set()
            self._alarm_thread = threading.Thread(target=self._alarm_loop, daemon=True)
            self._alarm_thread.start()
        elif not active and self._alarm_active.is_set():
            self._alarm_active.clear()
            if self._alarm_thread:
                self._alarm_thread.join(timeout=1)
            GPIO.output(self.pin, False)

    def _alarm_loop(self):
        delay = 1/220
        while self._alarm_active.is_set():
            GPIO.output(self.pin, True)
            time.sleep(delay)
            GPIO.output(self.pin, False)
            time.sleep(delay)


def run_db_loop(db, delay, callback, stop_event, name, queue):
    # kept as two independent flags on purpose: the door-demo buzz (below)
    # and the sustained alarm buzz share the same physical buzzer, but a
    # door event arriving mid-alarm must not desync the alarm's own state
    buzzing = False
    alarm_active = False
    while not stop_event.is_set():
        try:
            event = queue.get(timeout=delay)

            if isinstance(event, dict):
                code = event.get("code")
                if code == "MANUAL_BUZZ":
                    buzzing = True
                    db.buzz()
                    callback(buzzing, "MANUAL_BUZZ", name)
                    buzzing = False
                elif code == "ALARM_ON" and not alarm_active:
                    alarm_active = True
                    db.set_alarm(True)
                    callback(True, "ALARM_ON", name)
                elif code == "ALARM_OFF" and alarm_active:
                    alarm_active = False
                    db.set_alarm(False)
                    callback(False, "ALARM_OFF", name)
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
