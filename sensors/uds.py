import time

try:
    import RPi.GPIO as GPIO
except:
    pass

class DUS1(object):
    def __init__(self, trig_pin, echo_pin):
        self.trig_pin = trig_pin
        self.echo_pin = echo_pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(trig_pin, GPIO.OUT)
        GPIO.setup(echo_pin, GPIO.IN)

    def get_distance(self):
        GPIO.output(self.trig_pin, False)
        time.sleep(0.00001)
        GPIO.output(self.trig_pin, True)
        time.sleep(0.00001)
        GPIO.output(self.trig_pin, False)
        
        pulse_start = time.time()
        pulse_end = time.time()
        timeout = time.time() + 0.1
        
        while GPIO.input(self.echo_pin) == 0:
            pulse_start = time.time()
            if pulse_start > timeout:
                return -1
        
        while GPIO.input(self.echo_pin) == 1:
            pulse_end = time.time()
            if pulse_end > timeout:
                return -1
        
        pulse_duration = pulse_end - pulse_start
        distance = pulse_duration * 17150
        distance = round(distance, 2)
        
        return distance if 2 <= distance <= 400 else -1


def run_uds_loop(uds, delay, callback, stop_event, name):
    while not stop_event.is_set():
        distance = uds.get_distance()
        if distance > 0:
            code = "UDS_OK"
            callback(distance, code, name)
        time.sleep(delay)
