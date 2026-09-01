from verbosity import set_verbose


def build_registry(actuators, triggers):
    by_code = {}
    for a in actuators:
        by_code[a["code"]] = ("actuator", a)
    for t in triggers:
        by_code[t["code"]] = ("trigger", t)
    return by_code


def dispatch_command(raw, by_code):
    """Parses and executes one command line (e.g. "DS1 HOLD", "DL ON")
    against the by_code registry built by build_registry(). This is the
    single command grammar shared by the interactive console AND the
    remote MQTT console listener (mqtt_client/remote_console.py) - a Web
    UI command is dispatched through the exact same code path as someone
    typing at the PI's own terminal.

    Returns (ok: bool, message: str|None). message is None on a quiet
    success (the device's own callback already printed a confirmation);
    QUIT is deliberately not handled here - that's session lifecycle, not
    a device command, and a remote caller should never be able to kill
    the process this way.
    """
    raw = raw.strip()
    if not raw:
        return False, "empty command"

    parts = raw.split()

    if parts[0].upper() == "QUIET":
        sub = parts[1].upper() if len(parts) > 1 else ""
        if sub == "ON":
            set_verbose(False)
            return True, "Sensor console prints muted (QUIET OFF to restore)"
        elif sub == "OFF":
            set_verbose(True)
            return True, "Sensor console prints restored"
        return False, "Usage: QUIET ON | QUIET OFF"

    code = parts[0].upper()
    entry = by_code.get(code)
    if not entry:
        return False, f"Unknown command: {raw}"

    kind, target = entry
    if not target["enabled"]:
        return False, f"{code} is DISABLED in settings"

    sub = parts[1].upper() if len(parts) > 1 else ""
    handler = target["commands"].get(sub)
    if not handler:
        return False, f"Unknown subcommand for {code}: {raw}"

    if kind == "actuator":
        message = handler(parts[2:])
        if message is not None:
            target["queue"].put(message)
            return True, None
        return False, f"Invalid arguments: {raw}"
    else:
        result = handler(parts[2:])
        if result is False:
            return False, f"Invalid arguments: {raw}"
        return True, None


def run_console(stop_event, actuators, triggers=None, mqtt_settings=None, device_settings=None):
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

    If `mqtt_settings`/`device_settings` are given, this also starts a
    remote console listener (mqtt_client/remote_console.py) so a Web UI
    can run any of the same commands over MQTT via the server.
    """
    triggers = triggers or []
    by_code = build_registry(actuators, triggers)

    if mqtt_settings is not None and device_settings is not None:
        from mqtt_client.remote_console import start_remote_console
        start_remote_console(mqtt_settings, device_settings, by_code, stop_event)

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

            ok, message = dispatch_command(raw, by_code)
            if message:
                print(message)

        except EOFError:
            break
        except KeyboardInterrupt:
            print("\nExiting...")
            stop_event.set()
            break
