import time

try:
    import RPi.GPIO as GPIO
except:
    pass

class DMS(object):
    KEYS = [
        ['1', '2', '3', 'A'],
        ['4', '5', '6', 'B'],
        ['7', '8', '9', 'C'],
        ['*', '0', '#', 'D']
    ]
    
    def __init__(self, row_pins, col_pins):
        self.row_pins = row_pins
        self.col_pins = col_pins
        
        GPIO.setmode(GPIO.BCM)
        
        for pin in self.row_pins:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.HIGH)
        
        for pin in self.col_pins:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    def get_key(self):
        for row_idx, row_pin in enumerate(self.row_pins):
            GPIO.output(row_pin, GPIO.LOW)
            
            for col_idx, col_pin in enumerate(self.col_pins):
                if GPIO.input(col_pin) == GPIO.LOW:
                    key = self.KEYS[row_idx][col_idx]
                    time.sleep(0.2)
                    GPIO.output(row_pin, GPIO.HIGH)
                    return key
            
            GPIO.output(row_pin, GPIO.HIGH)
        
        return None


def run_dms_loop(dms, delay, callback, stop_event, name):
    while not stop_event.is_set():
        key = dms.get_key()
        if key:
            code = "DMS_KEY"
            callback(key, code, name)
        time.sleep(delay)
