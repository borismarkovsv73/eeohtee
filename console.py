from verbosity import set_verbose


def build_registry(actuators, triggers):
    by_code = {}
    for a in actuators:
        by_code[a["code"]] = ("actuator", a)
    for t in triggers:
        by_code[t["code"]] = ("trigger", t)
    return by_code


def dispatch_command(raw, by_code):
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
