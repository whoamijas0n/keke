import serial
import serial.tools.list_ports
import threading
import time
import glob
import os

class BLEGadget:
    """
    Encapsula la conexión serie con el gadget BLE (ESP32).
    Soporta escaneo, publicidad, flood, jam, sweep_jam y estado.
    """

    _CANDIDATE_PATTERNS = ['/dev/ttyACM*', '/dev/ttyUSB*']

    def __init__(self, port=None, baudrate=115200, timeout=2):
        self.baudrate = baudrate
        self.timeout = timeout
        self._ser = None
        self._available = False
        self._lock = threading.Lock()
        self._stop_events = {}
        self._scan_threads = {}

        if port is None:
            port = self._auto_detect_port()
        if port:
            try:
                self._ser = serial.Serial(port, baudrate, timeout=timeout)
                time.sleep(1)
                self._ser.reset_input_buffer()
                self._available = True
                self._flush_input()
            except serial.SerialException:
                self._available = False

    def _auto_detect_port(self):
        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            if any(hint in p.description for hint in ['CP210', 'CH340', 'USB2.0-Serial']):
                return p.device
        for pattern in self._CANDIDATE_PATTERNS:
            candidates = glob.glob(pattern)
            if candidates:
                return candidates[0]
        return None

    def _flush_input(self):
        if self._ser and self._ser.is_open:
            try:
                self._ser.reset_input_buffer()
            except:
                pass

    def is_available(self) -> bool:
        return self._available and self._ser is not None and self._ser.is_open

    def _send_command(self, cmd: str):
        if not self.is_available():
            raise serial.SerialException("Gadget no disponible")
        with self._lock:
            self._ser.write((cmd + "\n").encode())
            self._ser.flush()

    def _read_line(self):
        if not self.is_available():
            return ""
        try:
            line = self._ser.readline().decode(errors='ignore').strip()
        except:
            line = ""
        return line

    def _wait_for_ack(self, expected_prefix, timeout_secs=5):
        start = time.time()
        while time.time() - start < timeout_secs:
            line = self._read_line()
            if line.startswith(expected_prefix):
                return True
        return False

    def scan(self, module: int, duration: int, callback):
        """
        Escanea dispositivos BLE. callback(devices) recibe lista de dicts.
        """
        if not self.is_available():
            callback([])
            return

        self.stop(module)
        self._flush_input()
        self._send_command(f"SCAN {module} {duration}")
        if not self._wait_for_ack("SCANNING_STARTED", 3):
            callback([])
            return

        event = threading.Event()
        self._stop_events[module] = event

        def _scan_thread():
            devices = []
            timeout = duration + 5
            start = time.time()
            try:
                while not event.is_set() and (time.time() - start) < timeout:
                    line = self._read_line()
                    if not line:
                        continue
                    if line.startswith("DEVICE:"):
                        payload = line[7:]
                        parts = payload.split(",", 2)
                        if len(parts) >= 3:
                            devices.append({
                                "mac": parts[0].strip(),
                                "rssi": int(parts[1].strip()),
                                "name": parts[2].strip()
                            })
                    elif line.startswith("SCAN_DONE") or line.startswith("STOPPED"):
                        break
                    elif line.startswith("ERROR:"):
                        break
            except:
                pass
            finally:
                self._stop_events.pop(module, None)
                self._scan_threads.pop(module, None)
                callback(devices)

        thread = threading.Thread(target=_scan_thread, daemon=True)
        self._scan_threads[module] = thread
        thread.start()

    def advertise(self, module: int, message: str):
        self._send_command(f"ADVERTISE {module} {message}")
        self._wait_for_ack("ADVERTISING_STARTED", 2)

    def beacon_flood(self, module: int, count: int, interval_ms: int):
        self._send_command(f"BEACON_FLOOD {module} {count} {interval_ms}")
        self._wait_for_ack("FLOODING_STARTED", 2)

    def jam(self, module: int, channel: int, duration_sec: int):
        self._send_command(f"JAM {module} {channel} {duration_sec}")
        self._wait_for_ack("JAMMING_STARTED", 2)

    def sweep_jam(self, module: int, duration_sec: int):
        """Activa barrido de frecuencia (0-76) continuo."""
        self._send_command(f"SWEEP_JAM {module} {duration_sec}")
        self._wait_for_ack("SWEEP_JAMMING_STARTED", 2)

    def stop(self, module: int):
        if not self.is_available():
            return
        if module in self._stop_events:
            self._stop_events[module].set()
            self._send_command(f"STOP {module}")
            if module in self._scan_threads:
                self._scan_threads[module].join(timeout=5)
        else:
            self._send_command(f"STOP {module}")
            self._wait_for_ack("STOPPED", 2)

    def status(self) -> str:
        self._send_command("STATUS")
        line = self._read_line()
        return line if line else "ERROR: sin respuesta"