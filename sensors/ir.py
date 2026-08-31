import time

try:
    import RPi.GPIO as GPIO
except:
    pass


class IRReceiver(object):
    BIT_THRESHOLD = 0.001  # ~1ms: shorter space = '0', longer = '1'

    def __init__(self, pin):
        self.pin = pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def _wait_for_level(self, level, timeout):
        deadline = time.time() + timeout
        while GPIO.input(self.pin) != level:
            if time.time() > deadline:
                return False
        return True

    def read_code(self):
        if not self._wait_for_level(GPIO.LOW, 1.0):
            return None
        if not self._wait_for_level(GPIO.HIGH, 0.015):
            return None
        if not self._wait_for_level(GPIO.LOW, 0.006):
            return None

        bits = []
        for _ in range(32):
            if not self._wait_for_level(GPIO.HIGH, 0.002):
                break
            start = time.time()
            if not self._wait_for_level(GPIO.LOW, 0.002):
                break
            bits.append(1 if (time.time() - start) > self.BIT_THRESHOLD else 0)

        if len(bits) < 32:
            return None

        bytes_ = [0, 0, 0, 0]
        for i, bit in enumerate(bits):
            bytes_[i // 8] |= bit << (i % 8)

        _address, _address_inv, command, _command_inv = bytes_
        return f"0x{command:02X}"


def run_ir_loop(ir, callback, stop_event, name):
    while not stop_event.is_set():
        code = ir.read_code()
        if code:
            callback(code, "IR_CODE", name)
