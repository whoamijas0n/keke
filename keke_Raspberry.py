import customtkinter as ctk
import subprocess
import threading
import os

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

class RedTeamApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("KEKE ZERO - RED TEAM TOOLBOX")
        
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
            self.lift()            # <--- Fuerza a la ventana a subir al primer plano
            self.focus_force() 
            self.update_idletasks()
            
            # Teletransportar raton al centro para "despertar" a X11
            self.event_generate('<Motion>', warp=True, x=ancho//2, y=alto//2)
            
        self.after(1000, aplicar_kiosco) # 1 segundo completo de paciencia para la VM
        
        self.bind("<Escape>", lambda event: self.destroy())
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.target_ip = ctk.StringVar(value="127.0.0.1")
        self.session_dir = "Resultados_GUI"
        os.makedirs(self.session_dir, exist_ok=True)

        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=15, fg_color=COLOR_FONDO_SIDEBAR)
        self.sidebar_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(7, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="KEKE ZERO\nSYSTEM", 
                                     font=ctk.CTkFont(size=22, weight="bold"), text_color="#ff4d4d")
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 15))

        self.btn_nmap = self.crear_boton_menu("1. Nmap / Recon", self.show_recon_menu, 1)
        self.btn_mac = self.crear_boton_menu("2. Macchanger", self.show_mac_menu, 2)
        self.btn_wifi = self.crear_boton_menu("3. Auditoria WiFi", self.show_wifi_menu, 3)
        self.btn_exploit = self.crear_boton_menu("4. Explotacion", self.show_exploit_menu, 4)
        self.btn_utils = self.crear_boton_menu("5. Utilidades OS", self.show_utils_menu, 5)

        self.main_frame = ctk.CTkScrollableFrame(self, corner_radius=15, fg_color=COLOR_FONDO_PRINCIPAL)
        self.main_frame.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="nsew")

        self.show_recon_menu()

    def crear_boton_menu(self, texto, comando, fila):
        boton = ctk.CTkButton(self.sidebar_frame, text=texto, command=comando,
                             fg_color="transparent", border_width=2, border_color=COLOR_BOTON_ROJO,
                             hover_color=COLOR_BOTON_HOVER, font=ctk.CTkFont(size=14, weight="bold"))
        boton.grid(row=fila, column=0, padx=15, pady=8, sticky="ew")
        return boton

    def limpiar_main_frame(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

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

    def show_recon_menu(self):
        self.limpiar_main_frame()
        ctk.CTkLabel(self.main_frame, text="AUDITORIA NMAP", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(10, 5))
        input_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        input_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(input_frame, text="Target IP/Dominio:").pack(side="left", padx=5)
        entry_target = ctk.CTkEntry(input_frame, textvariable=self.target_ip, width=200)
        entry_target.pack(side="left", padx=5)
        btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=10)
        btn_frame.grid_columnconfigure((0,1), weight=1)
        comandos_nmap = [
            ("Descubrimiento de hosts", f"nmap -sn {{}}"),
            ("Puertos TCP Completo", f"nmap -sS -p- -T4 --min-rate=1000 {{}}"),
            ("Servicios y versiones", f"nmap -sV --version-intensity 5 {{}}"),
            ("Deteccion de OS", f"nmap -O --osscan-guess {{}}"),
            ("Vulnerabilidades (NSE)", f"nmap --script vuln,exploit {{}}"),
            ("Agresivo Completo (-A)", f"nmap -A -p- -T4 {{}}"),
            ("Auditoria SSL/TLS", f"nmap --script ssl-enum-ciphers -p 443 {{}}"),
            ("Traceroute", f"nmap --traceroute {{}}")
        ]
        for i, (nombre, cmd) in enumerate(comandos_nmap):
            row = i // 2
            col = i % 2
            ctk.CTkButton(btn_frame, text=nombre, fg_color=COLOR_BOTON_ROJO, hover_color=COLOR_BOTON_HOVER,
                         command=lambda c=cmd: self.ejecutar_comando(c.format(self.target_ip.get()))).grid(row=row, column=col, padx=5, pady=5, sticky="ew")
        self.mostrar_consola()

    def show_mac_menu(self):
        self.limpiar_main_frame()
        ctk.CTkLabel(self.main_frame, text="DIRECCION MAC", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(10, 15))
        interfaces = self.obtener_interfaces_red()
        interfaz_seleccionada = ctk.StringVar(value=interfaces[0] if interfaces else "wlan0")
        sel_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        sel_frame.pack(pady=5)
        ctk.CTkLabel(sel_frame, text="Selecciona Interfaz: ").pack(side="left")
        ctk.CTkOptionMenu(sel_frame, variable=interfaz_seleccionada, values=interfaces, fg_color=COLOR_BOTON_ROJO, button_color=COLOR_BOTON_HOVER).pack(side="left")
        ctk.CTkButton(self.main_frame, text="Ver Estado", fg_color=COLOR_BOTON_ROJO, hover_color=COLOR_BOTON_HOVER, width=300,
                     command=lambda: self.ejecutar_comando(f"macchanger -s {interfaz_seleccionada.get()}")).pack(pady=5)
        ctk.CTkButton(self.main_frame, text="MAC Random", fg_color=COLOR_BOTON_ROJO, hover_color=COLOR_BOTON_HOVER, width=300,
                     command=lambda: self.ejecutar_comando(f"ifconfig {interfaz_seleccionada.get()} down && macchanger -r {interfaz_seleccionada.get()} && ifconfig {interfaz_seleccionada.get()} up")).pack(pady=5)
        ctk.CTkButton(self.main_frame, text="Reset Original", fg_color=COLOR_BOTON_ROJO, hover_color=COLOR_BOTON_HOVER, width=300,
                     command=lambda: self.ejecutar_comando(f"ifconfig {interfaz_seleccionada.get()} down && macchanger -p {interfaz_seleccionada.get()} && ifconfig {interfaz_seleccionada.get()} up")).pack(pady=5)
        self.mostrar_consola()

    def show_wifi_menu(self):
        self.limpiar_main_frame()
        ctk.CTkLabel(self.main_frame, text="AUDITORIA INALAMBRICA", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(10, 15))
        interfaces = self.obtener_interfaces_red()
        interfaz_wifi = ctk.StringVar(value=interfaces[0] if interfaces else "wlan0")
        ctk.CTkOptionMenu(self.main_frame, variable=interfaz_wifi, values=interfaces, fg_color=COLOR_BOTON_ROJO, button_color=COLOR_BOTON_HOVER).pack(pady=5)
        ctk.CTkButton(self.main_frame, text="1. Levantar Modo Monitor", fg_color=COLOR_BOTON_ROJO, hover_color=COLOR_BOTON_HOVER, width=300, height=40,
                     command=lambda: self.ejecutar_comando(f"airmon-ng check kill && airmon-ng start {interfaz_wifi.get()}")).pack(pady=5)
        ctk.CTkButton(self.main_frame, text="2. Restaurar Red (Managed)", fg_color=COLOR_BOTON_ROJO, hover_color=COLOR_BOTON_HOVER, width=300, height=40,
                     command=lambda: self.ejecutar_comando(f"airmon-ng stop {interfaz_wifi.get()}mon && systemctl restart NetworkManager")).pack(pady=5)
        ctk.CTkLabel(self.main_frame, text="[!] Para migrar el Evil Twin de consola a interfaz tactil,\nse requiere construir una ventana dedicada con tablas de escaneo.", text_color="gray").pack(pady=10)
        self.mostrar_consola()

    def show_exploit_menu(self):
        self.limpiar_main_frame()
        ctk.CTkLabel(self.main_frame, text="EXPLOTACION", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(10, 15))
        ctk.CTkButton(self.main_frame, text="Iniciar MSFConsole", fg_color=COLOR_BOTON_ROJO, hover_color=COLOR_BOTON_HOVER, width=300,
                     command=lambda: self.ejecutar_comando("msfconsole -q")).pack(pady=5)
        ctk.CTkButton(self.main_frame, text="Buscar PrivEsc Linux", fg_color=COLOR_BOTON_ROJO, hover_color=COLOR_BOTON_HOVER, width=300,
                     command=lambda: self.ejecutar_comando("searchsploit linux privilege escalation")).pack(pady=5)
        self.mostrar_consola()

    def show_utils_menu(self):
        self.limpiar_main_frame()
        ctk.CTkLabel(self.main_frame, text="UTILIDADES DEL SISTEMA", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(10, 15))
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
        ctk.CTkButton(self.main_frame, text="REINICIAR SISTEMA", fg_color=COLOR_BOTON_PELIGRO, width=200,
                     command=lambda: os.system("reboot")).pack(pady=10)
        ctk.CTkButton(self.main_frame, text="APAGAR SISTEMA", fg_color=COLOR_BOTON_PELIGRO, width=200,
                     command=lambda: os.system("shutdown -h now")).pack(pady=5)
        ctk.CTkButton(self.main_frame, text="CERRAR INTERFAZ (SALIR)", fg_color="#4a4a4a", hover_color="#2b2b2b", width=200,
                     command=self.destroy).pack(pady=15)
        self.mostrar_consola()

    def ejecutar_comando(self, comando):
        self.escribir_consola(f"\nroot@kali:~# {comando}")
        hilo = threading.Thread(target=self._hilo_ejecucion, args=(comando,))
        hilo.start()

    def _hilo_ejecucion(self, comando):
        try:
            resultado = subprocess.check_output(comando, shell=True, stderr=subprocess.STDOUT, text=True)
            self.escribir_consola(resultado)
            self.escribir_consola("\n[+] Tarea finalizada.")
        except subprocess.CalledProcessError as e:
            self.escribir_consola(f"\n[!] ERROR: Comando fallo. Codigo: {e.returncode}")
            if e.output:
                self.escribir_consola(e.output)

if __name__ == "__main__":
    app = RedTeamApp()
    app.mainloop()