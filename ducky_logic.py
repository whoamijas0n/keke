"""
ducky_logic.py - Módulo para ejecutar payloads Rubber Ducky mediante USB Gadget HID.
Funciona escribiendo directamente en /dev/hidg0 usando códigos HID de teclado.
Requiere que el módulo g_hid esté cargado y el dispositivo HID exista.
"""

import os
import time

# Mapeo de teclas a códigos HID (Keyboard/Keypad Page, 0x07)
# Basado en especificación USB HID Usage Tables
HID_KEY_CODES = {
    'a': 0x04, 'b': 0x05, 'c': 0x06, 'd': 0x07, 'e': 0x08, 'f': 0x09, 'g': 0x0a,
    'h': 0x0b, 'i': 0x0c, 'j': 0x0d, 'k': 0x0e, 'l': 0x0f, 'm': 0x10, 'n': 0x11,
    'o': 0x12, 'p': 0x13, 'q': 0x14, 'r': 0x15, 's': 0x16, 't': 0x17, 'u': 0x18,
    'v': 0x19, 'w': 0x1a, 'x': 0x1b, 'y': 0x1c, 'z': 0x1d,
    '1': 0x1e, '2': 0x1f, '3': 0x20, '4': 0x21, '5': 0x22, '6': 0x23, '7': 0x24,
    '8': 0x25, '9': 0x26, '0': 0x27,
    'enter': 0x28, 'esc': 0x29, 'backspace': 0x2a, 'tab': 0x2b, 'space': 0x2c,
    '-': 0x2d, '=': 0x2e, '[': 0x2f, ']': 0x30, '\\': 0x31, ';': 0x33, "'": 0x34,
    '`': 0x35, ',': 0x36, '.': 0x37, '/': 0x38,
    'capslock': 0x39, 'f1': 0x3a, 'f2': 0x3b, 'f3': 0x3c, 'f4': 0x3d, 'f5': 0x3e,
    'f6': 0x3f, 'f7': 0x40, 'f8': 0x41, 'f9': 0x42, 'f10': 0x43, 'f11': 0x44,
    'f12': 0x45, 'printscreen': 0x46, 'scrolllock': 0x47, 'pause': 0x48,
    'insert': 0x49, 'home': 0x4a, 'pageup': 0x4b, 'delete': 0x4c, 'end': 0x4d,
    'pagedown': 0x4e, 'right': 0x4f, 'left': 0x50, 'down': 0x51, 'up': 0x52,
    'numlock': 0x53, 'kp/': 0x54, 'kp*': 0x55, 'kp-': 0x56, 'kp+': 0x57,
    'kpenter': 0x58, 'kp1': 0x59, 'kp2': 0x5a, 'kp3': 0x5b, 'kp4': 0x5c,
    'kp5': 0x5d, 'kp6': 0x5e, 'kp7': 0x5f, 'kp8': 0x60, 'kp9': 0x61, 'kp0': 0x62,
    'kp.': 0x63, 'application': 0x65, 'power': 0x66, 'kp=': 0x67,
    'f13': 0x68, 'f14': 0x69, 'f15': 0x6a, 'f16': 0x6b, 'f17': 0x6c,
    'f18': 0x6d, 'f19': 0x6e, 'f20': 0x6f, 'f21': 0x70, 'f22': 0x71,
    'f23': 0x72, 'f24': 0x73,
    # Modificadores
    'leftctrl': 0xe0, 'leftshift': 0xe1, 'leftalt': 0xe2, 'leftgui': 0xe3,
    'rightctrl': 0xe4, 'rightshift': 0xe5, 'rightalt': 0xe6, 'rightgui': 0xe7,
}

# Alias comunes
ALIAS = {
    'gui': 'leftgui', 'windows': 'leftgui', 'win': 'leftgui',
    'ctrl': 'leftctrl', 'control': 'leftctrl',
    'alt': 'leftalt',
    'shift': 'leftshift',
    'enter': 'enter', 'return': 'enter',
    'esc': 'esc', 'escape': 'esc',
    'tab': 'tab',
    'up': 'up', 'down': 'down', 'left': 'left', 'right': 'right',
    'space': 'space',
    'backspace': 'backspace', 'del': 'delete',
    'caps': 'capslock',
    'print': 'printscreen', 'prtsc': 'printscreen',
    'ins': 'insert',
    'pgup': 'pageup', 'pgdn': 'pagedown',
    'home': 'home', 'end': 'end',
}

HID_DEVICE = "/dev/hidg0"

def enviar_reporte_hid(modificador, tecla):
    """
    Envía un reporte HID de teclado de 8 bytes.
    Byte 0: modificador (bitmask)
    Byte 1: reservado (0)
    Bytes 2-7: códigos de teclas presionadas (hasta 6)
    """
    reporte = bytes([modificador, 0, tecla, 0, 0, 0, 0, 0])
    try:
        with open(HID_DEVICE, 'wb') as fd:
            fd.write(reporte)
            # Enviar reporte vacío para liberar tecla
            fd.write(b'\x00' * 8)
    except Exception as e:
        print(f"[!] Error escribiendo en {HID_DEVICE}: {e}")
        raise

def presionar_tecla(tecla_str):
    """Presiona una tecla normal (sin modificadores)."""
    tecla_str = tecla_str.lower()
    if tecla_str in ALIAS:
        tecla_str = ALIAS[tecla_str]
    if tecla_str not in HID_KEY_CODES:
        print(f"[!] Tecla no mapeada: {tecla_str}")
        return
    codigo = HID_KEY_CODES[tecla_str]
    # Si es un modificador (código >= 0xE0), se maneja distinto
    if codigo >= 0xE0:
        mod_bit = 1 << (codigo - 0xE0)
        enviar_reporte_hid(mod_bit, 0)
    else:
        enviar_reporte_hid(0, codigo)

def presionar_combinacion(modificador, tecla):
    """Presiona combinación de tecla con modificador (ej. GUI + r)."""
    mod_str = modificador.lower()
    if mod_str in ALIAS:
        mod_str = ALIAS[mod_str]
    tecla_str = tecla.lower()
    if tecla_str in ALIAS:
        tecla_str = ALIAS[tecla_str]
    if mod_str not in HID_KEY_CODES or HID_KEY_CODES[mod_str] < 0xE0:
        print(f"[!] Modificador inválido: {modificador}")
        return
    if tecla_str not in HID_KEY_CODES:
        print(f"[!] Tecla no mapeada: {tecla}")
        return
    mod_code = HID_KEY_CODES[mod_str]
    mod_bit = 1 << (mod_code - 0xE0)
    key_code = HID_KEY_CODES[tecla_str]
    enviar_reporte_hid(mod_bit, key_code)

def escribir_texto(texto):
    """Escribe una cadena de texto carácter por carácter."""
    for char in texto:
        # Manejar caracteres especiales como mayúsculas
        if char.isupper():
            # Presionar shift + char.lower()
            mod_bit = 1 << (HID_KEY_CODES['leftshift'] - 0xE0)
            key_lower = char.lower()
            if key_lower in HID_KEY_CODES:
                enviar_reporte_hid(mod_bit, HID_KEY_CODES[key_lower])
        else:
            if char in HID_KEY_CODES:
                enviar_reporte_hid(0, HID_KEY_CODES[char])
            else:
                # Carácter no mapeado, se omite (puede mejorarse con mapeo extendido)
                print(f"[!] Carácter no soportado: {char}")

def ejecutar_script_ducky(ruta_archivo):
    """Lee y ejecuta un script Rubber Ducky escribiendo en /dev/hidg0."""
    if not os.path.exists(HID_DEVICE):
        raise FileNotFoundError(f"Dispositivo HID {HID_DEVICE} no encontrado. Asegúrate de que el gadget USB HID esté configurado.")
    
    try:
        with open(ruta_archivo, 'r', encoding='utf-8') as f:
            lineas = f.readlines()
    except Exception as e:
        print(f"[!] Error al leer el archivo: {e}")
        return

    print(f"\n[+] Iniciando payload: {os.path.basename(ruta_archivo)}")
    print("[!] Tienes 2 segundos para situar el cursor...")
    time.sleep(2)

    for linea in lineas:
        linea = linea.strip()
        if not linea or linea.upper().startswith("REM"):
            continue

        partes = linea.split(maxsplit=1)
        comando = partes[0].upper()
        argumento = partes[1] if len(partes) > 1 else ""

        if comando == "STRING":
            print(f"  [>] Escribiendo: {argumento}")
            escribir_texto(argumento)
        elif comando == "DELAY":
            try:
                ms = int(argumento)
                print(f"  [~] Esperando {ms}ms...")
                time.sleep(ms / 1000.0)
            except ValueError:
                print(f"[!] DELAY inválido: {argumento}")
        elif comando in ["ENTER", "GUI", "WINDOWS", "TAB", "ESC", "ALT", "CONTROL", "SHIFT", 
                         "UP", "DOWN", "LEFT", "RIGHT", "SPACE", "BACKSPACE", "DELETE"]:
            print(f"  [*] Pulsando tecla: {comando}")
            presionar_tecla(comando)
        elif " " in linea and comando not in ["STRING", "DELAY"]:
            # Combinación como "GUI r"
            mod, tecla = linea.split(maxsplit=1)
            print(f"  [*] Combinación: {mod}+{tecla}")
            presionar_combinacion(mod, tecla)
        else:
            # Intenta como tecla simple
            print(f"  [*] Pulsando tecla: {linea}")
            presionar_tecla(linea)

    print("[#] Payload finalizado con éxito.\n")

def menu(Menu, AccionPython):
    """Función de menú para integrar con la interfaz (mantenida por compatibilidad)."""
    menu_d = Menu("MIS PAYLOADS")
    folder = "payloads"
    if not os.path.exists(folder):
        os.makedirs(folder)
    archivos = [f for f in os.listdir(folder) if f.endswith(".txt")]
    for archivo in archivos:
        ruta = os.path.join(folder, archivo)
        menu_d.agregar_opcion(f"{archivo}", AccionPython(f"Ejecutando...", ejecutar_script_ducky, ruta))
    return menu_d