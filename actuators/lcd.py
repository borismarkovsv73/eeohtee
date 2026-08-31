import time

try:
    import RPi.GPIO as GPIO
except:
    pass


class LCD(object):
    def __init__(self, rs_pin, e_pin, data_pins):
        self.rs = rs_pin
        self.e = e_pin
        self.data_pins = data_pins  # [d4, d5, d6, d7]
        GPIO.setmode(GPIO.BCM)
        for pin in [self.rs, self.e] + self.data_pins:
            GPIO.setup(pin, GPIO.OUT)
        self._init_display()

    def _pulse_enable(self):
        GPIO.output(self.e, True)
        time.sleep(0.0000005)
        GPIO.output(self.e, False)
        time.sleep(0.00005)

    def _write4(self, nibble):
        for i in range(4):
            GPIO.output(self.data_pins[i], (nibble >> i) & 1 == 1)
        self._pulse_enable()

    def _write_byte(self, value, is_data):
        GPIO.output(self.rs, is_data)
        self._write4(value >> 4)
        self._write4(value & 0x0F)

    def _init_display(self):
        GPIO.output(self.rs, False)
        time.sleep(0.05)
        for _ in range(3):
            self._write4(0x03)
            time.sleep(0.005)
        self._write4(0x02)
        self._write_byte(0x28, False)  # 4-bit, 2-line, 5x8 font
        self._write_byte(0x0C, False)  # display on, cursor off
        self._write_byte(0x06, False)  # auto-increment cursor
        self.clear()

    def clear(self):
        self._write_byte(0x01, False)
        time.sleep(0.002)

    def write_line(self, text, line=0):
        address = 0x80 if line == 0 else 0xC0
        self._write_byte(address, False)
        for char in text[:16].ljust(16):
            self._write_byte(ord(char), True)


def run_lcd_loop(lcd, delay, callback, stop_event, name, queue):
    lines = ["", ""]
    while not stop_event.is_set():
        try:
            event = queue.get(timeout=delay)
            if isinstance(event, dict) and event.get("code") == "MANUAL_SET":
                line = event.get("line", 0)
                text = event.get("text", "")
                lines[line] = text
                lcd.write_line(text, line)
                callback(tuple(lines), event.get("code"), name)
        except:
            pass
