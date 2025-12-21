from simulators.db import run_db_simulator
from actuators.db import run_db_loop
import threading
import time


def db_callback(state, code, name):
    t = time.localtime()
    buzzing = "Buzzing" if state else "Not buzzing"
    print("="*20 + f"\nName: {name}\nTimestamp: {time.strftime('%H:%M:%S', t)}\nCode: {code}\nState: {buzzing}\n")


def run_db(settings, threads, stop_event, name, queue):
    if settings['simulated']:
        print(f"Starting {name} simulator")
        buzzer_thread = threading.Thread(
            target=run_db_simulator, args=(5, db_callback, stop_event, name, queue)
        )
        buzzer_thread.start()
        threads.append(buzzer_thread)
        print(f"{name} simulator started")
    else:
        from actuators.db import DB
        print(f"Starting {name} loop")
        db = DB(settings['pin'])
        buzzer_thread = threading.Thread(
            target=run_db_loop, args=(db, 5, db_callback, stop_event, name, queue)
        )
        buzzer_thread.start()
        threads.append(buzzer_thread)
        print(f"{name} loop started")
