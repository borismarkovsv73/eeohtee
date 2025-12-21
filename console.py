import threading
from queue import Queue
from settings import load_settings


def run_console(dl_queue, db_queue, stop_event):
    settings = load_settings()
    dl_enabled = settings.get('DL', {}).get('enabled', True)
    db_enabled = settings.get('DB', {}).get('enabled', True)
    
    print("\n" + "="*50)
    print("Console Control Interface")
    print("="*50)
    print("Commands:")
    print(f"  DL ON    - Turn LED on {'(ENABLED)' if dl_enabled else '(DISABLED)'}")
    print(f"  DL OFF   - Turn LED off {'(ENABLED)' if dl_enabled else '(DISABLED)'}")
    print(f"  DB BUZZ  - Activate buzzer {'(ENABLED)' if db_enabled else '(DISABLED)'}")
    print("  QUIT     - Exit application")
    print("="*50 + "\n")
    
    while not stop_event.is_set():
        try:
            command = input("Enter command: \n").strip().upper()
            
            if command == "DL ON":
                if not dl_enabled:
                    print("LED is DISABLED in settings.json")
                else:
                    dl_queue.put({"code": "MANUAL_ON", "state": True})
                    print("LED turned ON")
            elif command == "DL OFF":
                if not dl_enabled:
                    print("LED is DISABLED in settings.json")
                else:
                    dl_queue.put({"code": "MANUAL_OFF", "state": False})
                    print("LED turned OFF")
            elif command == "DB BUZZ":
                if not db_enabled:
                    print("Buzzer is DISABLED in settings.json")
                else:
                    db_queue.put({"code": "MANUAL_BUZZ", "state": True})
                    print("Buzzer activated")
            elif command == "QUIT":
                print("Exiting application...")
                stop_event.set()
                break
            else:
                print(f"Unknown command: {command}")
                print("Available: DL ON, DL OFF, DB BUZZ, QUIT")
        except EOFError:
            break
        except KeyboardInterrupt:
            print("\nExiting...")
            stop_event.set()
            break
