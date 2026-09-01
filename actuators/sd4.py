import threading
import time

try:
    import RPi.GPIO as GPIO
except:
    pass

SEGMENT_MAP = {
    '0': 0b0111111, '1': 0b0000110, '2': 0b1011011, '3': 0b1001111,
    '4': 0b1100110, '5': 0b1101101, '6': 0b1111101, '7': 0b0000111,
    '8': 0b1111111, '9': 0b1101111, ' ': 0b0000000, '-': 0b1000000,
}


class FourDigitDisplay(object):
    def __init__(self, segment_pins, digit_pins):
        self.segment_pins = segment_pins  # [a, b, c, d, e, f, g]
        self.digit_pins = digit_pins      # [d1, d2, d3, d4] - active-low select
        GPIO.setmode(GPIO.BCM)
        for pin in self.segment_pins:
            GPIO.setup(pin, GPIO.OUT)
        for pin in self.digit_pins:
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH)  # HIGH = deselected
        self.buffer = "    "
        self.blinking = False
        self._blink_on = True
        self._blink_last_toggle = time.time()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self._thread.start()

    def _show_digit(self, index, char):
        pattern = SEGMENT_MAP.get(char, 0)
        for bit, pin in enumerate(self.segment_pins):
            GPIO.output(pin, (pattern >> bit) & 1 == 1)
        GPIO.output(self.digit_pins[index], False)  # select (active-low)
        time.sleep(0.002)
        GPIO.output(self.digit_pins[index], True)   # deselect

    def _refresh_loop(self):
        while not self._stop.is_set():
            if time.time() - self._blink_last_toggle > 0.5:
                self._blink_on = not self._blink_on
                self._blink_last_toggle = time.time()
            text = self.buffer if (not self.blinking or self._blink_on) else "    "
            for i, char in enumerate(text[:4]):
                self._show_digit(i, char)

    def set_value(self, text):
        self.buffer = text[:4].rjust(4)

    def set_blinking(self, blinking):
        self.blinking = blinking

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=1)


def run_sd4_loop(display, delay, callback, stop_event, name, queue):
    while not stop_event.is_set():
        try:
            event = queue.get(timeout=delay)
            if not isinstance(event, dict):
                continue
            if event.get("code") == "MANUAL_SET":
                display.set_value(event.get("value", "    "))
                callback((display.buffer, display.blinking), event.get("code"), name)
            elif event.get("code") == "MANUAL_BLINK":
                display.set_blinking(event.get("state", False))
                callback((display.buffer, display.blinking), event.get("code"), name)
        except:
            pass
    display.stop()
