import time

try:
    import RPi.GPIO as GPIO
except:
    pass

class DS1(object):
    def __init__(self, pin, bouncetime=0.1):
        self.pin = pin
        self.bouncetime = bouncetime
        self.last_change_time = 0
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def is_pressed(self):
        return GPIO.input(self.pin) == GPIO.LOW
    
    def should_process(self):
        current_time = time.time()
        if current_time - self.last_change_time >= self.bouncetime:
            self.last_change_time = current_time
            return True
        return False


def run_ds_loop(ds, delay, callback, stop_event, name, dl_queue, db_queue):
    last_state = False
    while not stop_event.is_set():
        pressed = ds.is_pressed()
        if pressed != last_state and ds.should_process():
            last_state = pressed
            if pressed:
                code = "DS_PRESSED"
                dl_queue.put("DOOR_UNLOCKED")
                db_queue.put("DOOR_UNLOCKED")
            else:
                code = "DS_RELEASED"
                dl_queue.put("DOOR_LOCKED")
                db_queue.put("DOOR_LOCKED")
            callback(pressed, code, name)
        time.sleep(0.01)
