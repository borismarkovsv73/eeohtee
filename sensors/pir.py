import time

try:
    import RPi.GPIO as GPIO
except:
    pass

class DPIR1(object):
    def __init__(self, pin):
        self.pin = pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin, GPIO.IN)
        time.sleep(2)

    def motion_detected(self):
        return GPIO.input(self.pin) == GPIO.HIGH


def run_pir_loop(pir, delay, callback, stop_event, name):
    last_state = False
    while not stop_event.is_set():
        motion = pir.motion_detected()
        if motion != last_state:
            last_state = motion
            code = "PIR_MOTION" if motion else "PIR_CLEAR"
            callback(motion, code, name)
        time.sleep(delay)
