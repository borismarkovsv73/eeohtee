
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
from mqtt_client.remote_reading import start_remote_reading_subscriber
import time

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
except:
    pass


# item 9: fixed remote-to-color mapping, matching simulators/ir.py's REMOTE_CODES
IR_REMOTE_MAP = {
    "0x45": {"code": "MANUAL_OFF", "color": (0, 0, 0)},
    "0x46": {"code": "MANUAL_SET", "color": (255, 0, 0)},
    "0x47": {"code": "MANUAL_SET", "color": (0, 255, 0)},
    "0x44": {"code": "MANUAL_SET", "color": (0, 0, 255)},
    "0x40": {"code": "MANUAL_SET", "color": (255, 255, 255)},
}

DHT_ROTATION_ORDER = ["DHT1", "DHT2", "DHT3"]
DHT_ROTATION_INTERVAL = 4


def run_lcd_rotation(lcd_queue, dht_readings, stop_event):
    index = 0
    while not stop_event.is_set():
        name = DHT_ROTATION_ORDER[index % len(DHT_ROTATION_ORDER)]
        index += 1
        reading = dht_readings[name]
        temperature, humidity = reading["temperature"], reading["humidity"]
        if temperature is not None and humidity is not None:
            line0 = f"{name} {temperature:.1f}C"
            line1 = f"Humidity: {humidity:.0f}%"
        else:
            line0 = name
            line1 = "no data yet"
        lcd_queue.put({"code": "MANUAL_SET", "line": 0, "text": line0})
        lcd_queue.put({"code": "MANUAL_SET", "line": 1, "text": line1})
        stop_event.wait(DHT_ROTATION_INTERVAL)


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

        dpir3_callback = ir_callback = None

        # item 7: DHT1/DHT2 are local (updated via on_reading hooks below);
        # DHT3 lives on PI2, so it's observed directly over MQTT instead of
        # going through the server - PIs can subscribe to each other's
        # already-published sensor topics, no new infrastructure needed
        dht_readings = {name: {"temperature": None, "humidity": None} for name in DHT_ROTATION_ORDER}

        def make_dht_hook(name):
            def hook(temperature, humidity):
                dht_readings[name]["temperature"] = temperature
                dht_readings[name]["humidity"] = humidity
            return hook

        def on_remote_dht3(reading):
            field = reading.get("field", "value")
            if field == "temperature":
                dht_readings["DHT3"]["temperature"] = reading.get("value")
            elif field == "humidity":
                dht_readings["DHT3"]["humidity"] = reading.get("value")

        if dht1_settings.get('enabled', True):
            run_dht(dht1_settings, threads, stop_event, "DHT1", mqtt_settings, device_settings, on_reading=make_dht_hook("DHT1"))

        if dht2_settings.get('enabled', True):
            run_dht(dht2_settings, threads, stop_event, "DHT2", mqtt_settings, device_settings, on_reading=make_dht_hook("DHT2"))

        start_remote_reading_subscriber(mqtt_settings, [("PI2", "DHT3", on_remote_dht3)], stop_event)

        if ir_settings.get('enabled', True):
            # item 9: remote-control button presses drive BRGB directly -
            # local to PI3, since IR and BRGB both live here
            def handle_ir_code(code):
                action = IR_REMOTE_MAP.get(code)
                if action:
                    brgb_queue.put(action)

            ir_callback = run_ir(ir_settings, threads, stop_event, "IR", mqtt_settings, device_settings, on_code=handle_ir_code)

        if brgb_settings.get('enabled', True):
            run_brgb(brgb_settings, threads, stop_event, "BRGB", brgb_queue, mqtt_settings, device_settings)

        if lcd_settings.get('enabled', True):
            run_lcd(lcd_settings, threads, stop_event, "LCD", lcd_queue, mqtt_settings, device_settings)
            rotation_thread = threading.Thread(target=run_lcd_rotation, args=(lcd_queue, dht_readings, stop_event))
            rotation_thread.start()
            threads.append(rotation_thread)

        if dpir3_settings.get('enabled', True):
            dpir3_callback = run_pir(dpir3_settings, threads, stop_event, "DPIR3", mqtt_settings, device_settings)

        def trigger_dpir3(args):
            if dpir3_callback:
                dpir3_callback(True, "PIR_MOTION", "DPIR3")
                dpir3_callback(False, "PIR_CLEAR", "DPIR3")

        def trigger_ir_code(args):
            if not args:
                return False
            if ir_callback:
                ir_callback(args[0], "IR_CODE", "IR")

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
        triggers = [
            {
                "code": "DPIR3",
                "enabled": dpir3_settings.get('enabled', True),
                "help": ["DPIR3 TRIGGER - Force a motion blip on DPIR3"],
                "commands": {"TRIGGER": trigger_dpir3},
            },
            {
                "code": "IR",
                "enabled": ir_settings.get('enabled', True),
                "help": [
                    "IR CODE <code> - Force a remote code, e.g. IR CODE 0x46 (red)",
                    "                 known codes: 0x45 off, 0x46 red, 0x47 green, 0x44 blue, 0x40 white",
                ],
                "commands": {"CODE": trigger_ir_code},
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
