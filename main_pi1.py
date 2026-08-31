
import threading

from queue import Queue

from components.dl import run_dl
from components.ds import run_ds
from settings import load_settings
from components.uds import run_uds
from components.db import run_db
from components.dms import run_dms
from components.pir import run_pir
from components.webc import run_webc
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
    settings = load_settings('settings_pi1.json')
    threads = []
    stop_event = threading.Event()
    try:
        device_settings = settings['device']
        mqtt_settings = settings['mqtt']
        ds1_settings = settings['DS1']
        dl_settings = settings['DL']
        dus1_settings = settings['DUS1']
        db_settings = settings['DB']
        dpir1_settings = settings['DPIR1']
        dms_settings = settings['DMS']
        webc_settings = settings['WEBC']

        dl_queue = Queue()
        db_queue = Queue()

        print(f"Device: {device_settings.get('name')} ({device_settings.get('pi_id')})")
        start_publisher_daemon(mqtt_settings, stop_event, threads)
        start_command_subscriber(mqtt_settings, device_settings, {"DB": db_queue}, stop_event)

        ds1_callback = dpir1_callback = dus1_callback = dms_callback = None

        if ds1_settings.get('enabled', True):
            ds1_callback = run_ds(ds1_settings, threads, stop_event, "DS1", dl_queue, db_queue, mqtt_settings, device_settings)

        if dl_settings.get('enabled', True):
            run_dl(dl_settings, threads, stop_event, "DL", dl_queue, mqtt_settings, device_settings)

        if dus1_settings.get('enabled', True):
            dus1_callback = run_uds(dus1_settings, threads, stop_event, "DUS1", mqtt_settings, device_settings)

        if db_settings.get('enabled', True):
            run_db(db_settings, threads, stop_event, "DB", db_queue, mqtt_settings, device_settings)

        if dms_settings.get('enabled', True):
            dms_callback = run_dms(dms_settings, threads, stop_event, "DMS", mqtt_settings, device_settings)

        if dpir1_settings.get('enabled', True):
            # item 1: motion on DPIR1 turns DL1 on for 10s - purely local to
            # PI1, no server round-trip needed since both devices live here
            def dpir1_turns_on_dl():
                dl_queue.put({"code": "MOTION_ON", "duration": 10})

            dpir1_callback = run_pir(dpir1_settings, threads, stop_event, "DPIR1", mqtt_settings, device_settings, on_motion=dpir1_turns_on_dl)

        if webc_settings.get('enabled', True):
            run_webc(webc_settings, threads, stop_event, "WEBC", mqtt_settings, device_settings)

        def trigger_ds1_hold(args):
            if ds1_callback:
                ds1_callback(True, "DS_PRESSED", "DS1")

        def trigger_ds1_release(args):
            if ds1_callback:
                ds1_callback(False, "DS_RELEASED", "DS1")

        def trigger_dpir1(args):
            if dpir1_callback:
                dpir1_callback(True, "PIR_MOTION", "DPIR1")
                dpir1_callback(False, "PIR_CLEAR", "DPIR1")

        def trigger_dus1_set(args):
            if not args:
                return False
            try:
                distance = float(args[0])
            except ValueError:
                return False
            if dus1_callback:
                dus1_callback(distance, "UDS_MANUAL", "DUS1")

        def trigger_dms_key(args):
            if not args or not args[0].isdigit():
                return False
            if dms_callback:
                for digit in args[0]:
                    dms_callback(digit, "DMS_KEY", "DMS")

        actuators = [
            {
                "code": "DL",
                "enabled": dl_settings.get('enabled', True),
                "queue": dl_queue,
                "help": ["DL ON    - Turn LED on", "DL OFF   - Turn LED off"],
                "commands": {
                    "ON": lambda args: {"code": "MANUAL_ON", "state": True},
                    "OFF": lambda args: {"code": "MANUAL_OFF", "state": False},
                },
            },
            {
                "code": "DB",
                "enabled": db_settings.get('enabled', True),
                "queue": db_queue,
                "help": ["DB BUZZ  - Activate buzzer"],
                "commands": {
                    "BUZZ": lambda args: {"code": "MANUAL_BUZZ", "state": True},
                },
            },
        ]
        triggers = [
            {
                "code": "DS1",
                "enabled": ds1_settings.get('enabled', True),
                "help": [
                    "DS1 HOLD    - Force DS1 pressed (test the 5s door-held-open alarm)",
                    "DS1 RELEASE - Force DS1 released",
                ],
                "commands": {"HOLD": trigger_ds1_hold, "RELEASE": trigger_ds1_release},
            },
            {
                "code": "DPIR1",
                "enabled": dpir1_settings.get('enabled', True),
                "help": ["DPIR1 TRIGGER - Force a motion blip on DPIR1"],
                "commands": {"TRIGGER": trigger_dpir1},
            },
            {
                "code": "DUS1",
                "enabled": dus1_settings.get('enabled', True),
                "help": ["DUS1 SET <cm> - Force a distance reading, e.g. DUS1 SET 20"],
                "commands": {"SET": trigger_dus1_set},
            },
            {
                "code": "DMS",
                "enabled": dms_settings.get('enabled', True),
                "help": ["DMS KEY <digits> - Type a key sequence on the keypad, e.g. DMS KEY 1234"],
                "commands": {"KEY": trigger_dms_key},
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
