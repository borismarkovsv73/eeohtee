
import threading

from queue import Queue

from components.dht import run_dht
from settings import load_settings
from components.ir import run_ir
from components.brgb import run_brgb
from components.lcd import run_lcd
from components.pir import run_pir
from console import run_console
from mqtt_client.publisher import start_publisher_daemon
import time

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
except:
    pass


if __name__ == "__main__":
    print('Starting app')
    settings = load_settings('settings_pi3.json')
    threads = []
    stop_event = threading.Event()
    try:
        device_settings = settings['device']
        mqtt_settings = settings['mqtt']
        dht1_settings = settings['DHT1']
        dht2_settings = settings['DHT2']
        ir_settings = settings['IR']
        brgb_settings = settings['BRGB']
        lcd_settings = settings['LCD']
        dpir3_settings = settings['DPIR3']

        brgb_queue = Queue()
        lcd_queue = Queue()

        print(f"Device: {device_settings.get('name')} ({device_settings.get('pi_id')})")
        start_publisher_daemon(mqtt_settings, stop_event, threads)

        if dht1_settings.get('enabled', True):
            run_dht(dht1_settings, threads, stop_event, "DHT1", mqtt_settings, device_settings)

        if dht2_settings.get('enabled', True):
            run_dht(dht2_settings, threads, stop_event, "DHT2", mqtt_settings, device_settings)

        if ir_settings.get('enabled', True):
            run_ir(ir_settings, threads, stop_event, "IR", mqtt_settings, device_settings)

        if brgb_settings.get('enabled', True):
            run_brgb(brgb_settings, threads, stop_event, "BRGB", brgb_queue, mqtt_settings, device_settings)

        if lcd_settings.get('enabled', True):
            run_lcd(lcd_settings, threads, stop_event, "LCD", lcd_queue, mqtt_settings, device_settings)

        if dpir3_settings.get('enabled', True):
            run_pir(dpir3_settings, threads, stop_event, "DPIR3", mqtt_settings, device_settings)

        actuators = [
            {
                "code": "BRGB",
                "enabled": brgb_settings.get('enabled', True),
                "queue": brgb_queue,
                "help": [
                    "BRGB SET r g b - Set color, each 0-255, e.g. BRGB SET 255 0 0",
                    "BRGB OFF       - Turn off",
                ],
                "commands": {
                    "SET": lambda args: {"code": "MANUAL_SET", "color": tuple(int(x) for x in args[:3])} if len(args) >= 3 else None,
                    "OFF": lambda args: {"code": "MANUAL_OFF", "color": (0, 0, 0)},
                },
            },
            {
                "code": "LCD",
                "enabled": lcd_settings.get('enabled', True),
                "queue": lcd_queue,
                "help": [
                    "LCD SET <line> <text> - Show text on line 0 or 1, e.g. LCD SET 0 Hello",
                ],
                "commands": {
                    "SET": lambda args: {"code": "MANUAL_SET", "line": int(args[0]), "text": " ".join(args[1:])} if len(args) >= 2 else None,
                },
            },
        ]
        run_console(stop_event, actuators)

    except KeyboardInterrupt:
        print('Stopping app')

    finally:
        stop_event.set()
        for t in threads:
            t.join(timeout=5)
        try:
            GPIO.cleanup()
        except NameError:
            pass
