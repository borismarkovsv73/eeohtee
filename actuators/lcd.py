import time

try:
    import smbus  # OS package on Raspberry Pi OS (python3-smbus), not pip
except ImportError:
    smbus = None

# Standard PCF8574 <-> HD44780 pin mapping used by nearly every I2C LCD
# backpack: P0=RS, P1=RW (unused, tied low), P2=E, P3=backlight, P4-P7=D4-D7.
_RS = 0x01
_EN = 0x04
_BACKLIGHT = 0x08


class LCD(object):
    """16x2 character LCD behind a PCF8574 I2C expander."""

    def __init__(self, i2c_address=0x27, i2c_bus=1):
        self._bus = smbus.SMBus(i2c_bus)
        self._address = i2c_address
        self._init_display()

    def _write_byte(self, data):
        self._bus.write_byte(self._address, data | _BACKLIGHT)

    def _pulse_enable(self, data):
        self._write_byte(data | _EN)
        time.sleep(0.0005)
        self._write_byte(data & ~_EN)
        time.sleep(0.0001)

    def _write4(self, nibble, is_data):
        data = (nibble << 4) | (_RS if is_data else 0)
        self._write_byte(data)
        self._pulse_enable(data)

    def _write_byte_lcd(self, value, is_data):
        self._write4((value >> 4) & 0x0F, is_data)
        self._write4(value & 0x0F, is_data)

    def _init_display(self):
        time.sleep(0.05)
        for _ in range(3):
            self._write4(0x03, False)
            time.sleep(0.005)
        self._write4(0x02, False)
        self._write_byte_lcd(0x28, False)  # 4-bit, 2-line, 5x8 font
        self._write_byte_lcd(0x0C, False)  # display on, cursor off
        self._write_byte_lcd(0x06, False)  # auto-increment cursor
        self.clear()

    def clear(self):
        self._write_byte_lcd(0x01, False)
        time.sleep(0.002)

    def write_line(self, text, line=0):
        address = 0x80 if line == 0 else 0xC0
        self._write_byte_lcd(address, False)
        for char in text[:16].ljust(16):
            self._write_byte_lcd(ord(char), True)


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
