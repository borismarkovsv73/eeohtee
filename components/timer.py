import threading


def run_timer(sd4_queue, timer_queue, stop_event):
    """Kitchen stopwatch (item 8) - purely local to PI2, since BTN and 4SD
    both live there. Drives the 4SD display through its normal queue (the
    same one console/remote commands use), so no changes were needed to
    the 4SD actuator itself.

    timer_queue accepts:
      {"code": "SET_TIME", "seconds": N}       - set the countdown (Web app)
      {"code": "SET_INCREMENT", "seconds": N}  - configure BTN's add-amount
      {"code": "BTN_PRESS"}                    - add N seconds, or silence
                                                  the blink if expired
    """
    remaining = 0
    increment = 30
    expired = False

    def push_display():
        clamped = max(0, int(remaining))
        mm, ss = divmod(clamped, 60)
        sd4_queue.put({"code": "MANUAL_SET", "value": f"{mm:02d}{ss:02d}"})

    push_display()

    while not stop_event.is_set():
        try:
            msg = timer_queue.get(timeout=1)
            if not isinstance(msg, dict):
                continue
            code = msg.get("code")
            if code == "SET_TIME":
                remaining = max(0, int(msg.get("seconds", 0)))
                expired = False
                sd4_queue.put({"code": "MANUAL_BLINK", "state": False})
                push_display()
            elif code == "SET_INCREMENT":
                increment = max(1, int(msg.get("seconds", increment)))
            elif code == "BTN_PRESS":
                if expired:
                    expired = False
                    sd4_queue.put({"code": "MANUAL_BLINK", "state": False})
                else:
                    remaining += increment
                push_display()
        except:
            # queue empty for ~1s - tick the countdown
            if remaining > 0 and not expired:
                remaining -= 1
                push_display()
                if remaining == 0:
                    expired = True
                    sd4_queue.put({"code": "MANUAL_BLINK", "state": True})


def start_timer(sd4_queue, timer_queue, stop_event, threads):
    thread = threading.Thread(target=run_timer, args=(sd4_queue, timer_queue, stop_event))
    thread.start()
    threads.append(thread)
    return thread
