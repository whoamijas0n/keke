import serial
import serial.tools.list_ports
import threading
import time
import glob
import os

class BLEGadget:
    """Encapsula la conexión serie con el gadget BLE (ESP32). Soporta reconexión segura y hot-plugging."""
    _CANDIDATE_PATTERNS = ['/dev/ttyACM*', '/dev/ttyUSB*']

    def __init__(self, baudrate=115200, timeout=2):
        self.baudrate = baudrate
        self.timeout = timeout
        self._ser = None
        self._available = False
        self._lock = threading.Lock()
        self._stop_events = {}
        self._scan_threads = {}
        self._port = None
        self.connect()

    def _handle_disconnect(self):
        """Limpia el estado y cierra el puerto fantasma de forma segura."""
        self._available = False
        if self._ser:
            try:
                self._ser.close()
            except:
                pass
            self._ser = None

    def connect(self):
        """Intenta abrir el puerto y sincronizar con el ESP32."""
        self._handle_disconnect() # Asegurar limpieza previa
        self._port = self._auto_detect_port()
        if not self._port:
            return False

        try:
            # write_timeout evita que la escritura bloquee el hilo si el buffer del SO está lleno
            self._ser = serial.Serial(self._port, self.baudrate, timeout=1, write_timeout=1)
            start = time.time()
            ready = False
            
            while time.time() - start < 3.0:
                try:
                    line = self._ser.readline().decode(errors='ignore').strip()
                    if "Gadget listo" in line:
                        ready = True
                        break
                except:
                    break
                time.sleep(0.05)

            if not ready:
                self._ser.write(b"STATUS\n")
                self._ser.timeout = 1
                resp = self._ser.readline().decode(errors='ignore').strip()
                if "ERROR" not in resp and resp:
                    ready = True

            self._ser.timeout = self.timeout
            self._ser.reset_input_buffer()
            self._available = ready
            return self._available
        except Exception:
            self._handle_disconnect()
            return False

    def reconnect(self):
        """Cierra conexión actual e intenta reconectar."""
        return self.connect()

    def _auto_detect_port(self):
        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            if any(hint in p.description for hint in ['CP210', 'CH340', 'USB2.0-Serial', 'USB Serial']):
                if os.path.exists(p.device): # Doble verificación física
                    return p.device
        for pattern in self._CANDIDATE_PATTERNS:
            candidates = glob.glob(pattern)
            if candidates and os.path.exists(candidates[0]):
                return candidates[0]
        return None

    def is_available(self) -> bool:
        """Verifica el estado del objeto y la existencia física del dispositivo."""
        try:
            if not (self._available and self._ser is not None and self._ser.is_open):
                return False
            # Magia para evitar bloqueos: verificar en el SO si el archivo USB existe
            if self._port and not os.path.exists(self._port):
                self._handle_disconnect()
                return False
            return True
        except:
            return False

    def _send_command(self, cmd: str):
        if not self.is_available():
            raise RuntimeError("Gadget desconectado.")
        with self._lock:
            try:
                self._ser.write((cmd + "\n").encode())
                self._ser.flush()
            except (serial.SerialException, OSError) as e:
                self._handle_disconnect()
                raise RuntimeError(f"Desconexión abrupta del USB: {e}")

    def _read_line(self):
        if not self.is_available(): return ""
        try:
            line = self._ser.readline().decode(errors='ignore').strip()
        except (serial.SerialException, OSError):
            self._handle_disconnect()
            return ""
        return line

    def _wait_for_ack(self, expected_prefix, timeout_secs=5):
        start = time.time()
        while time.time() - start < timeout_secs:
            line = self._read_line()
            if line.startswith(expected_prefix):
                return True
        return False

    def sweep_jam(self, module: int, duration_sec: int):
        try:
            self._send_command(f"SWEEP_JAM {module} {duration_sec}")
            return self._wait_for_ack("JAMMING_STARTED", 3)
        except RuntimeError:
            return False

    def stop(self, module: int):
        try:
            if not self.is_available(): return
            if module in self._stop_events:
                self._stop_events[module].set()
                self._send_command(f"STOP {module}")
            else:
                self._send_command(f"STOP {module}")
                return self._wait_for_ack("STOPPED", 2)
        except RuntimeError:
            pass

    def status(self) -> str:
        try:
            self._send_command("STATUS")
            line = self._read_line()
            return line if line else "ERROR: sin respuesta"
        except RuntimeError:
            return "ERROR: Gadget desconectado"

    def close(self):
        self._available = False
        for ev in list(self._stop_events.values()): ev.set()
        self._handle_disconnect()
