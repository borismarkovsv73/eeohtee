
import threading

from queue import Queue

from components.button import run_button
from settings import load_settings
from components.uds import run_uds
from components.pir import run_pir
from components.dht import run_dht
from components.gsg import run_gsg
from components.sd4 import run_sd4
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
    settings = load_settings('settings_pi2.json')
    threads = []
    stop_event = threading.Event()
    try:
        device_settings = settings['device']
        mqtt_settings = settings['mqtt']
        ds2_settings = settings['DS2']
        dus2_settings = settings['DUS2']
        dpir2_settings = settings['DPIR2']
        sd4_settings = settings['4SD']
        btn_settings = settings['BTN']
        dht3_settings = settings['DHT3']
        gsg_settings = settings['GSG']

        sd4_queue = Queue()

        print(f"Device: {device_settings.get('name')} ({device_settings.get('pi_id')})")
        start_publisher_daemon(mqtt_settings, stop_event, threads)

        if ds2_settings.get('enabled', True):
            run_button(ds2_settings, threads, stop_event, "DS2", mqtt_settings, device_settings)

        if dus2_settings.get('enabled', True):
            run_uds(dus2_settings, threads, stop_event, "DUS2", mqtt_settings, device_settings)

        if dpir2_settings.get('enabled', True):
            run_pir(dpir2_settings, threads, stop_event, "DPIR2", mqtt_settings, device_settings)

        if sd4_settings.get('enabled', True):
            run_sd4(sd4_settings, threads, stop_event, "4SD", sd4_queue, mqtt_settings, device_settings)

        if btn_settings.get('enabled', True):
            run_button(btn_settings, threads, stop_event, "BTN", mqtt_settings, device_settings)

        if dht3_settings.get('enabled', True):
            run_dht(dht3_settings, threads, stop_event, "DHT3", mqtt_settings, device_settings)

        if gsg_settings.get('enabled', True):
            run_gsg(gsg_settings, threads, stop_event, "GSG", mqtt_settings, device_settings)

        actuators = [
            {
                "code": "4SD",
                "enabled": sd4_settings.get('enabled', True),
                "queue": sd4_queue,
                "help": [
                    "4SD SET <mmss>   - Set timer display, e.g. 4SD SET 0130",
                    "4SD BLINK ON/OFF - Start/stop blinking",
                ],
                "commands": {
                    "SET": lambda args: {"code": "MANUAL_SET", "value": args[0]} if args else None,
                    "BLINK": lambda args: {"code": "MANUAL_BLINK", "state": args[0].upper() == "ON"} if args else None,
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
