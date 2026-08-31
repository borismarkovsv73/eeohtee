from verbosity import set_verbose


def run_console(stop_event, actuators, triggers=None):
    """Generic console control loop, shared by every PI's main script.

    `actuators` is a list of dicts:
      {
        "code": "DL",                 # first token of the command, e.g. "DL ON"
        "enabled": True/False,
        "queue": dl_queue,
        "help": ["DL ON    - Turn LED on", "DL OFF   - Turn LED off"],
        "commands": {
            "ON": lambda args: {"code": "MANUAL_ON", "state": True},
            "OFF": lambda args: {"code": "MANUAL_OFF", "state": False},
        },
      }
    A command handler returns the message dict to put on the queue, or
    None (and may print its own error) if the arguments were invalid.

    `triggers` (optional) is a list of dicts in the same shape, minus
    "queue" - used for forcing a sensor reading on demand for demo
    purposes (e.g. "DS1 HOLD", "DPIR1 TRIGGER"). Its command handlers
    perform the action directly (calling the sensor's real callback) and
    return False on invalid input, or anything else on success.
    """
    triggers = triggers or []
    by_code = {}
    for a in actuators:
        by_code[a["code"]] = ("actuator", a)
    for t in triggers:
        by_code[t["code"]] = ("trigger", t)

    print("\n" + "="*50)
    print("Console Control Interface")
    print("="*50)
    print("Commands:")
    for entry in actuators + triggers:
        status = "(ENABLED)" if entry["enabled"] else "(DISABLED)"
        for line in entry["help"]:
            print(f"  {line} {status}")
    print("  QUIET ON/OFF - Silence/restore sensor console prints")
    print("  QUIT     - Exit application")
    print("="*50 + "\n")

    while not stop_event.is_set():
        try:
            raw = input("Enter command: \n").strip()
            if not raw:
                continue

            if raw.upper() == "QUIT":
                print("Exiting application...")
                stop_event.set()
                break

            parts = raw.split()

            if parts[0].upper() == "QUIET":
                sub = parts[1].upper() if len(parts) > 1 else ""
                if sub == "ON":
                    set_verbose(False)
                    print("Sensor console prints muted (QUIET OFF to restore)")
                elif sub == "OFF":
                    set_verbose(True)
                    print("Sensor console prints restored")
                else:
                    print("Usage: QUIET ON | QUIET OFF")
                continue

            code = parts[0].upper()
            entry = by_code.get(code)

            if not entry:
                print(f"Unknown command: {raw}")
                continue

            kind, target = entry
            if not target["enabled"]:
                print(f"{code} is DISABLED in settings")
                continue

            sub = parts[1].upper() if len(parts) > 1 else ""
            handler = target["commands"].get(sub)
            if not handler:
                print(f"Unknown subcommand for {code}: {raw}")
                continue

            if kind == "actuator":
                message = handler(parts[2:])
                if message is not None:
                    target["queue"].put(message)
                else:
                    print(f"Invalid arguments: {raw}")
            else:
                result = handler(parts[2:])
                if result is False:
                    print(f"Invalid arguments: {raw}")

        except EOFError:
            break
        except KeyboardInterrupt:
            print("\nExiting...")
            stop_event.set()
            break
