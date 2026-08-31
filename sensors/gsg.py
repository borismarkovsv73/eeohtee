import time

try:
    import RPi.GPIO as GPIO
except:
    pass


class GSG(object):
    def __init__(self, pin):
        self.pin = pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin, GPIO.IN)

    def movement_detected(self):
        return GPIO.input(self.pin) == GPIO.HIGH


def run_gsg_loop(gsg, delay, callback, stop_event, name):
    last_state = False
    while not stop_event.is_set():
        moved = gsg.movement_detected()
        if moved != last_state:
            last_state = moved
            code = "GSG_MOTION" if moved else "GSG_CLEAR"
            callback(moved, code, name)
        time.sleep(delay)
