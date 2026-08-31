try:
    import RPi.GPIO as GPIO
except:
    pass


class BRGB(object):
    def __init__(self, r_pin, g_pin, b_pin, freq=100):
        self.pins = (r_pin, g_pin, b_pin)
        GPIO.setmode(GPIO.BCM)
        for pin in self.pins:
            GPIO.setup(pin, GPIO.OUT)
        self.pwm = tuple(GPIO.PWM(pin, freq) for pin in self.pins)
        for channel in self.pwm:
            channel.start(0)

    def set_color(self, r, g, b):
        for channel, value in zip(self.pwm, (r, g, b)):
            channel.ChangeDutyCycle(value / 255 * 100)


def run_brgb_loop(brgb, delay, callback, stop_event, name, queue):
    color = (0, 0, 0)
    while not stop_event.is_set():
        try:
            event = queue.get(timeout=delay)
            if isinstance(event, dict) and event.get("code") in ("MANUAL_SET", "MANUAL_OFF"):
                new_color = tuple(event.get("color", (0, 0, 0)))
                if new_color != color:
                    color = new_color
                    brgb.set_color(*color)
                    callback(color, event.get("code"), name)
        except:
            pass
