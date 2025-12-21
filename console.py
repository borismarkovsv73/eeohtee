import threading
from queue import Queue


def run_console(dl_queue, db_queue, stop_event):
    print("\n" + "="*50)
    print("Console Control Interface")
    print("="*50)
    print("Commands:")
    print("  DL ON    - Turn LED on")
    print("  DL OFF   - Turn LED off")
    print("  DB BUZZ  - Activate buzzer")
    print("  QUIT     - Exit application")
    print("="*50 + "\n")
    
    while not stop_event.is_set():
        try:
            command = input("Enter command: \n").strip().upper()
            
            if command == "DL ON":
                dl_queue.put({"code": "MANUAL_ON", "state": True})
                print("LED turned ON")
            elif command == "DL OFF":
                dl_queue.put({"code": "MANUAL_OFF", "state": False})
                print("LED turned OFF")
            elif command == "DB BUZZ":
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
