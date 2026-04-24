import serial
import threading
import time

class BLEGadget:
    """
    Encapsula la conexión serie con el gadget BLE (ESP32).
    Soporta escaneo, publicidad, flood, jam y estado.
    """
    def __init__(self, port="/dev/ttyACM0", baudrate=115200, timeout=2):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_lock = threading.Lock()
        self._ser = None
        try:
            self._ser = serial.Serial(port, baudrate, timeout=timeout)
            time.sleep(1)
            self._ser.reset_input_buffer()
            self._available = True
        except serial.SerialException:
            self._available = False

    def is_available(self) -> bool:
        return self._available and self._ser is not None and self._ser.is_open

    def _send_command(self, cmd: str):
        """Envía comando seguido de \\n y espera reconocimiento simple."""
        if not self.is_available():
            raise serial.SerialException("Gadget no disponible")
        with self.serial_lock:
            self._ser.write((cmd + "\n").encode())
            self._ser.flush()

    def _read_line(self):
        """Lee una línea del serial con timeout."""
        if not self.is_available():
            return ""
        self._ser.timeout = self.timeout
        return self._ser.readline().decode(errors='ignore').strip()

    def _read_until(self, end_marker, timeout_secs=30):
        """Lee líneas hasta encontrar el marcador final. Retorna lista de líneas."""
        lines = []
        start = time.time()
        while time.time() - start < timeout_secs:
            line = self._read_line()
            if line:
                lines.append(line)
                if line.startswith(end_marker):
                    break
        return lines

    def scan(self, module: int, duration: int, callback):
        """
        Escanea dispositivos BLE en el módulo indicado.
        Llama callback(devices) con lista de dicts {mac, rssi, name}.
        """
        def _scan_thread():
            if not self.is_available():
                callback([])
                return
            self._send_command(f"SCAN {module} {duration}")
            # Esperar confirmación
            ack = self._read_line()
            devices = []
            try:
                while True:
                    line = self._read_line()
                    if line is None or line == "":
                        continue
                    if line.startswith("DEVICE:"):
                        parts = line[7:].split(",", 2)
                        if len(parts) >= 3:
                            devices.append({
                                "mac": parts[0].strip(),
                                "rssi": int(parts[1].strip()),
                                "name": parts[2].strip()
                            })
                    elif line.startswith("SCAN_DONE"):
                        break
            except Exception as e:
                print(f"Error en escaneo BLE: {e}")
            callback(devices)
        threading.Thread(target=_scan_thread, daemon=True).start()

    def advertise(self, module: int, message: str):
        """Inicia publicidad continua con el mensaje como nombre BLE."""
        self._send_command(f"ADVERTISE {module} {message}")

    def beacon_flood(self, module: int, count: int, interval_ms: int):
        """Inicia inundación de beacons con nombres aleatorios."""
        self._send_command(f"BEACON_FLOOD {module} {count} {interval_ms}")

    def jam(self, module: int, channel: int, duration_sec: int):
        """Activa jamming en canal BLE durante la duración indicada."""
        self._send_command(f"JAM {module} {channel} {duration_sec}")

    def stop(self, module: int):
        """Detiene la operación en el módulo especificado."""
        self._send_command(f"STOP {module}")

    def status(self) -> str:
        """Solicita estado del gadget y retorna la respuesta."""
        self._send_command("STATUS")
        return self._read_line()