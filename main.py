
import threading

from queue import Queue

from components.dl import run_dl
from components.ds import run_ds
from settings import load_settings
from components.uds import run_uds
from components.db import run_db
from components.dms import run_dms
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
    settings = load_settings()
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

        dl_queue = Queue()
        db_queue = Queue()

        print(f"Device: {device_settings.get('name')} ({device_settings.get('pi_id')})")
        start_publisher_daemon(mqtt_settings, stop_event, threads)

        if ds1_settings.get('enabled', True):
            run_ds(ds1_settings, threads, stop_event, "DS1", dl_queue, db_queue, mqtt_settings, device_settings)

        if dl_settings.get('enabled', True):
            run_dl(dl_settings, threads, stop_event, "DL", dl_queue, mqtt_settings, device_settings)

        if dus1_settings.get('enabled', True):
            run_uds(dus1_settings, threads, stop_event, "DUS1", mqtt_settings, device_settings)

        if db_settings.get('enabled', True):
            run_db(db_settings, threads, stop_event, "DB", db_queue, mqtt_settings, device_settings)

        if dms_settings.get('enabled', True):
            run_dms(dms_settings, threads, stop_event, "DMS", mqtt_settings, device_settings)

        if dpir1_settings.get('enabled', True):
            run_pir(dpir1_settings, threads, stop_event, "DPIR1", mqtt_settings, device_settings)

        run_console(dl_queue, db_queue, stop_event)

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
