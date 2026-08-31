from simulators.lcd import run_lcd_simulator
from actuators.lcd import run_lcd_loop
from mqtt_client.buffer import enqueue_reading
from mqtt_client.topics import resolve_topic
from verbosity import is_verbose
import threading
import time


def lcd_callback(lines, code, name):
    if not is_verbose():
        return
    line0, line1 = lines
    t = time.localtime()
    print("="*20 + f"\nName: {name}\nTimestamp: {time.strftime('%H:%M:%S', t)}\nCode: {code}\nLine0: {line0}\nLine1: {line1}\n")


def run_lcd(settings, threads, stop_event, name, queue, mqtt_settings, device_settings):
    simulated = settings['simulated']
    topic = resolve_topic(mqtt_settings, settings, device_settings, name)

    def callback(lines, code, sensor_name):
        lcd_callback(lines, code, sensor_name)
        line0, line1 = lines
        enqueue_reading(topic, sensor_name, code, line0, simulated, extra={"field": "line0"})
        enqueue_reading(topic, sensor_name, code, line1, simulated, extra={"field": "line1"})

    if simulated:
        print(f"Starting {name} simulator")
        actuator_thread = threading.Thread(
            target=run_lcd_simulator, args=(2, callback, stop_event, name, queue)
        )
        actuator_thread.start()
        threads.append(actuator_thread)
        print(f"{name} simulator started")
    else:
        from actuators.lcd import LCD
        print(f"Starting {name} loop")
        pins = settings['pins']
        lcd = LCD(pins['rs'], pins['e'], [pins['d4'], pins['d5'], pins['d6'], pins['d7']])
        actuator_thread = threading.Thread(
            target=run_lcd_loop, args=(lcd, 2, callback, stop_event, name, queue)
        )
        actuator_thread.start()
        threads.append(actuator_thread)
        print(f"{name} loop started")
