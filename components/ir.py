from simulators.ir import run_ir_simulator
from sensors.ir import run_ir_loop
from mqtt_client.buffer import enqueue_reading
from mqtt_client.topics import resolve_topic
from verbosity import is_verbose
import threading
import time


def ir_callback(code, msg_code, name):
    if not is_verbose():
        return
    t = time.localtime()
    print("="*20 + f"\nName: {name}\nTimestamp: {time.strftime('%H:%M:%S', t)}\nCode: {msg_code}\nRemote code: {code}\n")


def run_ir(settings, threads, stop_event, name, mqtt_settings, device_settings):
    simulated = settings['simulated']
    topic = resolve_topic(mqtt_settings, settings, device_settings, name)

    def callback(code, msg_code, sensor_name):
        ir_callback(code, msg_code, sensor_name)
        enqueue_reading(topic, sensor_name, msg_code, code, simulated)

    if simulated:
        print(f"Starting {name} simulator")
        sensor_thread = threading.Thread(
            target=run_ir_simulator, args=(2, callback, stop_event, name)
        )
        sensor_thread.start()
        threads.append(sensor_thread)
        print(f"{name} simulator started")
    else:
        from sensors.ir import IRReceiver
        print(f"Starting {name} loop")
        ir = IRReceiver(settings['pin'])
        sensor_thread = threading.Thread(
            target=run_ir_loop, args=(ir, callback, stop_event, name)
        )
        sensor_thread.start()
        threads.append(sensor_thread)
        print(f"{name} loop started")
