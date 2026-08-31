import time

try:
    import RPi.GPIO as GPIO
except:
    pass


class DHT(object):
    BIT_THRESHOLD = 0.00005  # ~50us: shorter pulse = '0', longer = '1'

    def __init__(self, pin):
        self.pin = pin

    def _wait_for_level(self, level, timeout):
        deadline = time.time() + timeout
        while GPIO.input(self.pin) != level:
            if time.time() > deadline:
                return False
        return True

    def read(self):
        GPIO.setup(self.pin, GPIO.OUT)
        GPIO.output(self.pin, GPIO.LOW)
        time.sleep(0.018)
        GPIO.output(self.pin, GPIO.HIGH)
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        if not self._wait_for_level(GPIO.LOW, 0.001):
            return None, None
        if not self._wait_for_level(GPIO.HIGH, 0.001):
            return None, None
        if not self._wait_for_level(GPIO.LOW, 0.001):
            return None, None

        bits = []
        for _ in range(40):
            if not self._wait_for_level(GPIO.HIGH, 0.001):
                return None, None
            start = time.time()
            if not self._wait_for_level(GPIO.LOW, 0.001):
                return None, None
            bits.append(1 if (time.time() - start) > self.BIT_THRESHOLD else 0)

        bytes_ = [0] * 5
        for i, bit in enumerate(bits):
            bytes_[i // 8] = (bytes_[i // 8] << 1) | bit

        checksum = (bytes_[0] + bytes_[1] + bytes_[2] + bytes_[3]) & 0xFF
        if checksum != bytes_[4]:
            return None, None

        humidity = float(bytes_[0])
        temperature = float(bytes_[2])
        return temperature, humidity


def run_dht_loop(dht, delay, callback, stop_event, name):
    while not stop_event.is_set():
        temperature, humidity = dht.read()
        if temperature is not None:
            callback((temperature, humidity), "DHT_READING", name)
        time.sleep(delay)
