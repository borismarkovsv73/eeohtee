
import threading

from queue import Queue

from components.button import run_button
from settings import load_settings
from components.uds import run_uds
from components.pir import run_pir
from components.dht import run_dht
from components.gsg import run_gsg
from components.sd4 import run_sd4
from components.timer import start_timer
from console import run_console
from mqtt_client.publisher import start_publisher_daemon
from mqtt_client.commands import start_command_subscriber
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
        timer_queue = Queue()

        print(f"Device: {device_settings.get('name')} ({device_settings.get('pi_id')})")
        start_publisher_daemon(mqtt_settings, stop_event, threads)
        start_command_subscriber(mqtt_settings, device_settings, {"4SD": sd4_queue, "TIMER": timer_queue}, stop_event)

        ds2_callback = dpir2_callback = dus2_callback = gsg_callback = btn_callback = None

        if ds2_settings.get('enabled', True):
            ds2_callback = run_button(ds2_settings, threads, stop_event, "DS2", mqtt_settings, device_settings)

        if dus2_settings.get('enabled', True):
            dus2_callback = run_uds(dus2_settings, threads, stop_event, "DUS2", mqtt_settings, device_settings)

        if dpir2_settings.get('enabled', True):
            dpir2_callback = run_pir(dpir2_settings, threads, stop_event, "DPIR2", mqtt_settings, device_settings)

        if sd4_settings.get('enabled', True):
            run_sd4(sd4_settings, threads, stop_event, "4SD", sd4_queue, mqtt_settings, device_settings)
            # item 8: kitchen stopwatch drives the same 4SD queue - purely
            # local to PI2, since BTN and 4SD both live here
            start_timer(sd4_queue, timer_queue, stop_event, threads)

        if btn_settings.get('enabled', True):
            btn_callback = run_button(
                btn_settings, threads, stop_event, "BTN", mqtt_settings, device_settings,
                on_press=lambda: timer_queue.put({"code": "BTN_PRESS"}),
            )

        if dht3_settings.get('enabled', True):
            run_dht(dht3_settings, threads, stop_event, "DHT3", mqtt_settings, device_settings)

        if gsg_settings.get('enabled', True):
            gsg_callback = run_gsg(gsg_settings, threads, stop_event, "GSG", mqtt_settings, device_settings)

        def trigger_ds2_hold(args):
            if ds2_callback:
                ds2_callback(True, "BTN_PRESSED", "DS2")

        def trigger_ds2_release(args):
            if ds2_callback:
                ds2_callback(False, "BTN_RELEASED", "DS2")

        def trigger_dpir2(args):
            if dpir2_callback:
                dpir2_callback(True, "PIR_MOTION", "DPIR2")
                dpir2_callback(False, "PIR_CLEAR", "DPIR2")

        def trigger_dus2_set(args):
            if not args:
                return False
            try:
                distance = float(args[0])
            except ValueError:
                return False
            if dus2_callback:
                dus2_callback(distance, "UDS_MANUAL", "DUS2")

        def trigger_gsg(args):
            if gsg_callback:
                gsg_callback(True, "GSG_MOTION", "GSG")
                gsg_callback(False, "GSG_CLEAR", "GSG")

        def trigger_btn_press(args):
            if btn_callback:
                btn_callback(True, "BTN_PRESSED", "BTN")
                btn_callback(False, "BTN_RELEASED", "BTN")

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
            {
                "code": "TIMER",
                "enabled": sd4_settings.get('enabled', True),
                "queue": timer_queue,
                "help": [
                    "TIMER SET <seconds>       - Set the kitchen stopwatch, e.g. TIMER SET 90",
                    "TIMER INCREMENT <seconds> - Configure how much BTN adds per press",
                ],
                "commands": {
                    "SET": lambda args: {"code": "SET_TIME", "seconds": int(args[0])} if args and args[0].isdigit() else None,
                    "INCREMENT": lambda args: {"code": "SET_INCREMENT", "seconds": int(args[0])} if args and args[0].isdigit() else None,
                },
            },
        ]
        triggers = [
            {
                "code": "DS2",
                "enabled": ds2_settings.get('enabled', True),
                "help": [
                    "DS2 HOLD    - Force DS2 pressed (test the 5s door-held-open alarm)",
                    "DS2 RELEASE - Force DS2 released",
                ],
                "commands": {"HOLD": trigger_ds2_hold, "RELEASE": trigger_ds2_release},
            },
            {
                "code": "DPIR2",
                "enabled": dpir2_settings.get('enabled', True),
                "help": ["DPIR2 TRIGGER - Force a motion blip on DPIR2"],
                "commands": {"TRIGGER": trigger_dpir2},
            },
            {
                "code": "DUS2",
                "enabled": dus2_settings.get('enabled', True),
                "help": ["DUS2 SET <cm> - Force a distance reading, e.g. DUS2 SET 20"],
                "commands": {"SET": trigger_dus2_set},
            },
            {
                "code": "GSG",
                "enabled": gsg_settings.get('enabled', True),
                "help": ["GSG TRIGGER - Force a significant-movement blip on GSG"],
                "commands": {"TRIGGER": trigger_gsg},
            },
            {
                "code": "BTN",
                "enabled": btn_settings.get('enabled', True),
                "help": ["BTN PRESS - Force a press on the kitchen button"],
                "commands": {"PRESS": trigger_btn_press},
            },
        ]
        run_console(stop_event, actuators, triggers)

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
