import threading
import time
from collections import deque


class AlarmEngine(object):
    PIR_CODES = {"DPIR1", "DPIR2", "DPIR3"}
    DOOR_TO_DISTANCE = {"DS1": "DUS1", "DS2": "DUS2"}
    PIR_TO_DISTANCE = {"DPIR1": "DUS1", "DPIR2": "DUS2"}

    def __init__(self, influx_writer, command_publisher, config, stop_event):
        self._influx_writer = influx_writer
        self._command_publisher = command_publisher
        self._stop_event = stop_event

        self.pin = str(config.get("pin", "1234"))
        self.arm_delay = config.get("arm_delay_seconds", 10)
        self.door_open_threshold = config.get("door_open_threshold_seconds", 5)
        self.door_grace_period = config.get("door_grace_period_seconds", 10)
        self.distance_window = config.get("distance_window_seconds", 5)
        self.direction_threshold_cm = config.get("direction_threshold_cm", 15)

        self._lock = threading.Lock()
        self.alarm_active = False
        self.alarm_reason = None
        self.armed = False
        self.occupancy = 0

        self._active_conditions = {}     # condition_key -> reason
        self._pin_buffer = ""
        self._pending_arm_deadline = None

        self._ds_since = {}              # sensor_code -> time.time() when became pressed
        self._armed_door_deadline = {}   # sensor_code -> deadline time.time()
        self._distance_history = {"DUS1": deque(), "DUS2": deque()}
        self._last_occupancy_event = {}  # pir_code -> time.time() of last counted crossing

        self._ticker = threading.Thread(target=self._tick_loop, daemon=True)
        self._ticker.start()

    # ---- public snapshot / web-app disarm -----------------------------

    def snapshot(self):
        with self._lock:
            return {
                "alarm_active": self.alarm_active,
                "alarm_reason": self.alarm_reason,
                "armed": self.armed,
                "occupancy": self.occupancy,
                "pending_arm": self._pending_arm_deadline is not None,
            }

    def disarm_via_web(self):
        self._disarm("WEB_APP")

    # ---- incoming readings ---------------------------------------------

    def handle_reading(self, pi_id, sensor_code, reading):
        value = reading.get("value")
        ts = reading.get("timestamp", time.time())

        if sensor_code in self.DOOR_TO_DISTANCE:
            self._handle_door_sensor(sensor_code, bool(value), ts)
        elif sensor_code in self.PIR_CODES:
            self._handle_pir(sensor_code, bool(value), ts)
        elif sensor_code in ("DUS1", "DUS2"):
            self._handle_distance(sensor_code, value, ts)
        elif sensor_code == "DMS":
            self._handle_keypress(str(value))
        elif sensor_code == "GSG":
            if bool(value):
                self._activate_alarm("GSG_MOVEMENT", "GSG", "GSG_MOVEMENT")

    def _handle_door_sensor(self, code, pressed, ts):
        with self._lock:
            was_armed = self.armed
            if pressed:
                self._ds_since[code] = ts
                if was_armed:
                    self._armed_door_deadline[code] = ts + self.door_grace_period
            else:
                self._ds_since.pop(code, None)
                self._armed_door_deadline.pop(code, None)
        if not pressed:
            # only DOOR_HELD_OPEN resolves this way - UNAUTHORIZED_ENTRY has
            # no such exit condition, it requires PIN/web disarm regardless
            # of whether the door is later closed
            self._clear_condition(f"DOOR_HELD_OPEN:{code}")

    def _handle_pir(self, code, motion, ts):
        if not motion:
            return

        direction = None
        distance_code = self.PIR_TO_DISTANCE.get(code)
        if distance_code:
            with self._lock:
                last_event = self._last_occupancy_event.get(code)
                debounced = last_event is not None and (ts - last_event) < self.distance_window
            if not debounced:
                direction = self._infer_direction(distance_code, ts)
                if direction in ("enter", "exit"):
                    # only a crossing that actually gets counted consumes
                    # the debounce window - an inconclusive/no-data PIR
                    # blip must not block a real crossing shortly after
                    with self._lock:
                        self._last_occupancy_event[code] = ts

        with self._lock:
            occupancy_now = self.occupancy
        if occupancy_now <= 0 and direction != "enter":
            # a confidently-inferred entry explains the motion on its own -
            # only treat it as suspicious if it's not that
            self._activate_alarm("EMPTY_HOUSE_MOTION", code, "EMPTY_HOUSE_MOTION")

        if direction == "enter":
            self._adjust_occupancy(1)
        elif direction == "exit":
            self._adjust_occupancy(-1)

    def _handle_distance(self, code, distance, ts):
        try:
            distance = float(distance)
        except (TypeError, ValueError):
            return
        with self._lock:
            dq = self._distance_history.get(code)
            if dq is None:
                return
            dq.append((ts, distance))
            cutoff = ts - self.distance_window
            while dq and dq[0][0] < cutoff:
                dq.popleft()

    def _infer_direction(self, code, ts):
        cutoff = ts - self.distance_window
        with self._lock:
            dq = [(t, d) for t, d in self._distance_history.get(code, ()) if cutoff <= t <= ts]
        if len(dq) < 2:
            return None
        _, first_d = dq[0]
        _, last_d = dq[-1]
        delta = last_d - first_d
        if delta <= -self.direction_threshold_cm:
            return "enter"   # distance shrinking = getting closer to the door sensor
        if delta >= self.direction_threshold_cm:
            return "exit"    # distance growing = moving away from the door sensor
        return None

    def _handle_keypress(self, key):
        if not key.isdigit():
            return
        with self._lock:
            self._pin_buffer = (self._pin_buffer + key)[-4:]
            matched = self._pin_buffer == self.pin
            if matched:
                self._pin_buffer = ""
                if self.alarm_active or self.armed:
                    action = "disarm"
                elif self._pending_arm_deadline is not None:
                    action = "cancel_arm"
                else:
                    action = "start_arm"
            else:
                action = None
        if action == "disarm":
            self._disarm("PIN_DMS")
        elif action == "cancel_arm":
            self._cancel_pending_arm()
        elif action == "start_arm":
            self._start_arm_countdown()

    # ---- state transitions ----------------------------------------------

    def _start_arm_countdown(self):
        with self._lock:
            self._pending_arm_deadline = time.time() + self.arm_delay
        print(f"[alarm] PIN accepted - arming in {self.arm_delay}s")

    def _cancel_pending_arm(self):
        with self._lock:
            self._pending_arm_deadline = None
        print("[alarm] pending arm cancelled")

    def _adjust_occupancy(self, delta):
        with self._lock:
            self.occupancy = max(0, self.occupancy + delta)
            new_value = self.occupancy
        self._log("OCCUPANCY", "OCCUPANCY_CHANGED", new_value)
        print(f"[alarm] occupancy -> {new_value}")

    def _activate_alarm(self, reason, source, condition_key):
        with self._lock:
            already_active = bool(self._active_conditions)
            self._active_conditions[condition_key] = reason
            self.alarm_active = True
            self.alarm_reason = reason
        self._log("ALARM", reason, True)
        print(f"[alarm] ALARM ON (reason={reason}, source={source})")
        if not already_active:
            self._command_publisher.send("PI1", "DB", {"code": "ALARM_ON"})

    def _clear_condition(self, condition_key):
        with self._lock:
            had = self._active_conditions.pop(condition_key, None)
            if had is None:
                return
            still_active = bool(self._active_conditions)
            if not still_active:
                self.alarm_active = False
                self.alarm_reason = None
            else:
                self.alarm_reason = next(reversed(list(self._active_conditions.values())))
        print(f"[alarm] condition resolved: {condition_key}")
        if not still_active:
            self._log("ALARM", "ALARM_OFF", False)
            self._command_publisher.send("PI1", "DB", {"code": "ALARM_OFF"})

    def _disarm(self, source):
        with self._lock:
            was_active = bool(self._active_conditions)
            self._active_conditions.clear()
            self.alarm_active = False
            self.alarm_reason = None
            self.armed = False
            self._pending_arm_deadline = None
            self._armed_door_deadline.clear()
            now = time.time()
            for code in self._ds_since:
                self._ds_since[code] = now
        self._log("SECURITY", "DISARMED", True)
        print(f"[alarm] disarmed (source={source}, was_active={was_active})")
        if was_active:
            self._log("ALARM", "ALARM_OFF", False)
            self._command_publisher.send("PI1", "DB", {"code": "ALARM_OFF"})

    def _log(self, sensor_code, code, value):
        reading = {"code": code, "value": value, "simulated": False, "timestamp": time.time()}
        try:
            self._influx_writer.write_readings("SYSTEM", sensor_code, [reading])
        except Exception as exc:
            print(f"[alarm] failed to log {sensor_code}/{code}: {exc}")

    # ---- periodic time-based checks --------------------------------------

    def _tick_loop(self):
        while not self._stop_event.is_set():
            time.sleep(1)
            now = time.time()
            door_held_open = []
            unauthorized_entries = []
            became_armed = False

            with self._lock:
                for code, since in list(self._ds_since.items()):
                    if now - since >= self.door_open_threshold:
                        door_held_open.append(code)
                        del self._ds_since[code]  # only trigger once per hold

                for code, deadline in list(self._armed_door_deadline.items()):
                    if now >= deadline:
                        unauthorized_entries.append(code)
                        del self._armed_door_deadline[code]

                if self._pending_arm_deadline is not None and now >= self._pending_arm_deadline:
                    self.armed = True
                    self._pending_arm_deadline = None
                    became_armed = True

            for code in door_held_open:
                self._activate_alarm("DOOR_HELD_OPEN", code, f"DOOR_HELD_OPEN:{code}")
            for code in unauthorized_entries:
                self._activate_alarm("UNAUTHORIZED_ENTRY", code, f"UNAUTHORIZED_ENTRY:{code}")
            if became_armed:
                self._log("SECURITY", "ARMED", True)
                print("[alarm] system armed")
