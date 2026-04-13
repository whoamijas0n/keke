import curses
import subprocess
import os
import socket
from datetime import datetime

# ==========================================
# 0. CONFIGURACIÓN INICIAL Y DE SESIÓN
# ==========================================
# Directorio base y directorio específico para la sesión actual
BASE_DIR = "Resultados_Nmap"

# Generamos el nombre de la carpeta de esta sesión (se creará físicamente al lanzar el primer escaneo)
timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
SESSION_DIR = os.path.join(BASE_DIR, f"Auditoria-{timestamp}")

def obtener_ip_y_rango_kali():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip_actual = s.getsockname()[0]
    except Exception:
        return '127.0.0.1', '/8'
    finally:
        s.close()

    try:
        salida = subprocess.check_output(['ip', '-o', '-f', 'inet', 'addr', 'show']).decode('utf-8')
        for linea in salida.splitlines():
            if ip_actual in linea:
                for elemento in linea.split():
                    if elemento.startswith(f"{ip_actual}/"):
                        cidr = f"/{elemento.split('/')[1]}"
                        return ip_actual, cidr
    except Exception:
        pass
    return ip_actual, None

ip_inicial, rango_inicial = obtener_ip_y_rango_kali()

# ==========================================
# 1. GESTIÓN DE ESTADO GLOBAL
# ==========================================
ESTADO = {
    "ip": ip_inicial,
    "rango": rango_inicial,
    "usar_rango": False 
}

def obtener_target():
    if ESTADO["usar_rango"] and ESTADO["rango"]:
        return f"{ESTADO['ip']}{ESTADO['rango']}"
    return ESTADO["ip"]

SCAN_SPEED = "-T4"
MIN_RATE = "--min-rate=1000"

# ==========================================
# 2. FUNCIONES LÓGICAS (CALLBACKS DE PYTHON)
# ==========================================
def cambiar_rango(activar):
    ESTADO["usar_rango"] = activar
    estado_str = "ACTIVADO (Escaneando toda la subred)" if activar else "DESACTIVADO (Escaneando solo un objetivo)"
    print(f"[+] Uso de rango de red: {estado_str}")
    print(f"[+] El nuevo objetivo para los escaneos es: {obtener_target()}")

def ingresar_ip_manual():
    print(f"Objetivo actual: {obtener_target()}")
    nueva_ip = input("\nIngresa la nueva IP o dominio (ej. 10.10.10.5 o scanme.nmap.org): ")
    
    if nueva_ip.strip():
        ESTADO["ip"] = nueva_ip.strip()
        ESTADO["usar_rango"] = False 
        print(f"\n[+] Objetivo actualizado exitosamente a: {ESTADO['ip']}")
    else:
        print("\n[-] Operación cancelada. Se mantiene el objetivo anterior.")

# ==========================================
# 3. CLASES DE ACCIÓN (COMMAND PATTERN)
# ==========================================
class AccionBash:
    def __init__(self, nombre, comando):
        self.nombre = nombre
        self.comando = comando

    def ejecutar(self):
        curses.endwin()
        os.system('clear')
        
        comando_final = self.comando.replace("{TARGET}", obtener_target())
        
        # Creamos la carpeta de sesión dinámicamente si el comando va a guardar resultados ahí
        if BASE_DIR in comando_final and not os.path.exists(SESSION_DIR):
            os.makedirs(SESSION_DIR, exist_ok=True)
        
        print(f"[*] Ejecutando Módulo: {self.nombre}")
        print(f"[*] Objetivo actual: {obtener_target()}")
        print(f"[*] Comando Bash: {comando_final}\n")
        print("=" * 50)
        
        try:
            subprocess.run(comando_final, shell=True)
        except Exception as e:
            print(f"[!] Error crítico al ejecutar: {e}")
            
        print("=" * 50)
        print("\n[Presiona ENTER para regresar al menú anterior]")
        input()

class AccionPython:
    def __init__(self, nombre, funcion, *args, **kwargs):
        self.nombre = nombre
        self.funcion = funcion
        self.args = args
        self.kwargs = kwargs

    def ejecutar(self):
        curses.endwin()
        os.system('clear')
        
        print(f"[*] Ejecutando Configuración Interna: {self.nombre}")
        print("=" * 50 + "\n")
        
        try:
            self.funcion(*self.args, **self.kwargs)
        except Exception as e:
            print(f"\n[!] Error crítico en la función Python: {e}")
            
        print("\n" + "=" * 50)
        print("[Presiona ENTER para regresar al menú anterior]")
        input()

class AccionMenuDinamico:
    """Clase nueva: Genera un menú al vuelo y lo inyecta en la TUI sin perder la posición actual"""
    def __init__(self, titulo, funcion_generadora):
        self.titulo = titulo
        self.funcion_generadora = funcion_generadora

    def ejecutar(self, app):
        nuevo_menu = self.funcion_generadora()
        if nuevo_menu:
            app.pila_menus.append(nuevo_menu)

# ==========================================
# 4. SISTEMA DE MENÚS (TUI Engine)
# ==========================================
class Menu:
    def __init__(self, titulo):
        self.titulo = titulo
        self.opciones = [] 
        self.indice_actual = 0

    def agregar_opcion(self, nombre, destino):
        self.opciones.append((nombre, destino))

class AplicacionTUI:
    def __init__(self, stdscr, menu_raiz):
        self.stdscr = stdscr
        self.pila_menus = [menu_raiz] 
        curses.curs_set(0)
        self.stdscr.keypad(True)

    def dibujar_interfaz(self):
        self.stdscr.clear()
        alto, ancho = self.stdscr.getmaxyx()
        
        if alto < 12 or ancho < 65:
            mensaje = "Terminal muy pequeña. Agrándala para usar la herramienta."
            try:
                self.stdscr.addstr(alto//2, max(0, (ancho//2) - (len(mensaje)//2)), mensaje)
            except curses.error: pass
            self.stdscr.refresh()
            return False

        menu_actual = self.pila_menus[-1]
        
        titulo = f"=== {menu_actual.titulo} ==="
        if len(self.pila_menus) > 1:
            subtitulo = "[ ↑/↓: Navegar | ESPACIO: Seleccionar | ←: Volver | Q: Salir ]"
        else:
            subtitulo = "[ ↑/↓: Navegar | ESPACIO: Seleccionar | Q: Salir ]"

        self.stdscr.addstr(1, (ancho // 2) - (len(titulo) // 2), titulo, curses.A_BOLD | curses.A_UNDERLINE)
        self.stdscr.addstr(2, (ancho // 2) - (len(subtitulo) // 2), subtitulo)

        for i, (nombre, _) in enumerate(menu_actual.opciones):
            texto = f" {i}. {nombre} " if menu_actual.titulo == "AUDITORÍA NMAP" else f" {i+1}. {nombre} "
            x = (ancho // 2) - (len(texto) // 2)
            y = 5 + i
            
            if y < alto - 1:
                if i == menu_actual.indice_actual:
                    self.stdscr.addstr(y, x, f">>{texto}<<", curses.A_REVERSE | curses.A_BOLD)
                else:
                    self.stdscr.addstr(y, x, f"  {texto}  ")

        self.stdscr.refresh()
        return True

    def ejecutar(self):
        while True:
            espacio_suficiente = self.dibujar_interfaz()
            tecla = self.stdscr.getch()
            
            if not espacio_suficiente:
                if tecla in [ord('q'), ord('Q')]: break
                continue

            menu_actual = self.pila_menus[-1]

            if tecla == curses.KEY_UP and menu_actual.indice_actual > 0:
                menu_actual.indice_actual -= 1
            elif tecla == curses.KEY_DOWN and menu_actual.indice_actual < len(menu_actual.opciones) - 1:
                menu_actual.indice_actual += 1
            elif tecla == ord(' '):
                destino_seleccionado = menu_actual.opciones[menu_actual.indice_actual][1]
                
                # Integración del nuevo comportamiento de menús dinámicos
                if isinstance(destino_seleccionado, Menu):
                    self.pila_menus.append(destino_seleccionado)
                elif isinstance(destino_seleccionado, AccionMenuDinamico):
                    destino_seleccionado.ejecutar(self) # Le pasamos la 'app' para que pueda apilar el menú
                elif isinstance(destino_seleccionado, (AccionBash, AccionPython)):
                    destino_seleccionado.ejecutar()
                    
            elif tecla == curses.KEY_LEFT or tecla == ord('b') or tecla == curses.KEY_BACKSPACE:
                if len(self.pila_menus) > 1:
                    self.pila_menus.pop()
            elif tecla in [ord('q'), ord('Q')]:
                break 

# ==========================================
# 5. GENERADORES DINÁMICOS PARA EL EXPLORADOR (NUEVO)
# ==========================================
def generar_menu_archivos(ruta_carpeta):
    """Escanea los archivos .txt dentro de una auditoría y crea un menú para leerlos"""
    nombre_carpeta = os.path.basename(ruta_carpeta)
    menu = Menu(f"ARCHIVOS EN {nombre_carpeta}")
    
    try:
        archivos = sorted([f for f in os.listdir(ruta_carpeta) if os.path.isfile(os.path.join(ruta_carpeta, f))])
    except Exception:
        archivos = []

    if not archivos:
        menu.agregar_opcion("Carpeta vacía (Regresar)", AccionBash("Vacío", "echo 'No hay archivos para mostrar.'"))
        return menu

    for archivo in archivos:
        ruta_archivo = os.path.join(ruta_carpeta, archivo)
        # Usamos 'less' para leer el reporte sin romper la terminal
        menu.agregar_opcion(f"{archivo}", AccionBash(f"Leyendo {archivo}", f"less '{ruta_archivo}'"))

    return menu

def generar_menu_carpetas():
    """Escanea la carpeta base y crea un menú con todas las sesiones de auditoría"""
    menu = Menu("AUDITORÍAS GUARDADAS")
    
    if not os.path.exists(BASE_DIR):
        menu.agregar_opcion("Directorio vacío (Aún no hay escaneos)", AccionBash("Vacío", "echo 'Realiza un escaneo primero.'"))
        return menu

    carpetas = sorted([d for d in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, d))], reverse=True)

    if not carpetas:
        menu.agregar_opcion("No hay auditorías guardadas", AccionBash("Vacío", "echo 'No se encontraron auditorías.'"))
        return menu

    for carpeta in carpetas:
        ruta_carpeta = os.path.join(BASE_DIR, carpeta)
        # Usamos una función lambda para inyectar la ruta correcta de forma aislada para cada iteración
        menu.agregar_opcion(f"{carpeta}", AccionMenuDinamico(carpeta, lambda r=ruta_carpeta: generar_menu_archivos(r)))

    return menu

# ==========================================
# GESTIÓN DE MACCHANGER
# ==========================================
def obtener_interfaces():
    """Lee las interfaces de red directamente del sistema operativo"""
    try:
        # Filtramos 'lo' (loopback) ya que normalmente no se le cambia la MAC
        return sorted([i for i in os.listdir('/sys/class/net/') if i != "lo"])
    except Exception:
        return []

def ingresar_mac_personalizada(interfaz):
    """Callback de Python para pedir la MAC e inyectarla en el comando"""
    print(f"[*] Interfaz a modificar: {interfaz}")
    nueva_mac = input("\nIngresa la nueva MAC (ej. 00:11:22:33:44:55): ")
    
    if nueva_mac.strip():
        # Encadenamos ifconfig down -> macchanger -> ifconfig up
        comando = f"sudo ifconfig {interfaz} down && sudo macchanger -m {nueva_mac.strip()} {interfaz} && sudo ifconfig {interfaz} up"
        print(f"\n[*] Aplicando cambios...\n")
        subprocess.run(comando, shell=True)
    else:
        print("\n[-] Operación cancelada. No se ingresó ninguna MAC.")

def generar_menu_opciones_mac(interfaz):
    """Genera las opciones de Macchanger para la interfaz seleccionada"""
    menu = Menu(f"OPCIONES MAC: {interfaz}")
    
    # Plantilla base para evitar repetir la bajada y subida de la interfaz en cada opción
    cmd_base = f"sudo ifconfig {interfaz} down && sudo macchanger {{}} {interfaz} && sudo ifconfig {interfaz} up"

    menu.agregar_opcion("Ver información actual de la MAC", AccionBash("Info MAC", f"sudo macchanger -s {interfaz}"))
    menu.agregar_opcion("Resetear a la dirección MAC original", AccionBash("Reset MAC", cmd_base.format("-p")))
    menu.agregar_opcion("Asignar una MAC aleatoria del mismo fabricante", AccionBash("MAC Mismo Fabricante", cmd_base.format("-a")))
    menu.agregar_opcion("Cambiar a una MAC random", AccionBash("MAC Random", cmd_base.format("-r")))
    menu.agregar_opcion("Utilizar una MAC personalizada", AccionPython("MAC Personalizada", ingresar_mac_personalizada, interfaz))
    # Pasamos la salida por 'less' por si la lista de fabricantes es muy larga para la pantalla
    menu.agregar_opcion("Ver la lista de fabricantes soportados", AccionBash("Fabricantes", "sudo macchanger -l | less"))
    
    return menu

def generar_menu_interfaces():
    """Genera el menú dinámico que escanea y muestra las interfaces de red"""
    menu = Menu("SELECCIONAR INTERFAZ DE RED")
    interfaces = obtener_interfaces()

    if not interfaces:
        menu.agregar_opcion("No se encontraron interfaces", AccionBash("Error", "echo 'No se detectaron interfaces de red en el sistema.'"))
        return menu

    for interfaz in interfaces:
        # Usamos una lambda aislando el valor 'i=interfaz' para evitar problemas de sobrescritura en el bucle
        menu.agregar_opcion(f"Configurar {interfaz}", AccionMenuDinamico(f"Macchanger {interfaz}", lambda i=interfaz: generar_menu_opciones_mac(i)))

    return menu

# ==========================================
# 6. ÁRBOL DE MENÚS Y COMPILACIÓN
# ==========================================
def main(stdscr):

    menu_objetivo = Menu("CONFIGURACIÓN DE OBJETIVO")
    menu_objetivo.agregar_opcion("Escanear toda la red (Activar Rango /24)", AccionPython("Activar Rango", cambiar_rango, True))
    menu_objetivo.agregar_opcion("Escanear solo la IP (Desactivar Rango)", AccionPython("Desactivar Rango", cambiar_rango, False))
    menu_objetivo.agregar_opcion("Ingresar IP o Dominio Manualmente", AccionPython("IP Manual", ingresar_ip_manual))

    # Ahora utilizamos SESSION_DIR para que todo caiga en la carpeta con la fecha actual
    menu_nmap = Menu("AUDITORÍA NMAP")
    menu_nmap.agregar_opcion("Descubrimiento de hosts", AccionBash("Host Discovery", f"nmap -sn {{TARGET}} -oN {SESSION_DIR}/00_hosts.txt"))
    menu_nmap.agregar_opcion("Escaneo de puertos comunes", AccionBash("Common Ports", f"nmap -sS {SCAN_SPEED} --top-ports 1000 {{TARGET}} -oN {SESSION_DIR}/01_common.txt"))
    menu_nmap.agregar_opcion("Escaneo completo TCP (optimizado)", AccionBash("Full TCP", f"nmap -sS -p- {SCAN_SPEED} {MIN_RATE} {{TARGET}} -oN {SESSION_DIR}/02_full_tcp.txt"))
    menu_nmap.agregar_opcion("Escaneo de servicios y versiones", AccionBash("Services & Versions", f"nmap -sV --version-intensity 5 {{TARGET}} -oN {SESSION_DIR}/03_services.txt"))
    menu_nmap.agregar_opcion("Detección de sistemas operativos", AccionBash("OS Detection", f"nmap -O --osscan-guess {{TARGET}} -oN {SESSION_DIR}/04_os.txt"))
    menu_nmap.agregar_opcion("Escaneo UDP (puertos comunes)", AccionBash("UDP Scan", f"nmap -sU --top-ports 100 {SCAN_SPEED} {{TARGET}} -oN {SESSION_DIR}/05_udp.txt"))
    menu_nmap.agregar_opcion("Escaneo de vulnerabilidades con NSE", AccionBash("Vuln Scan", f"nmap --script vuln,exploit {{TARGET}} -oN {SESSION_DIR}/06_vuln.txt"))
    menu_nmap.agregar_opcion("Escaneo agresivo completo", AccionBash("Aggressive Scan", f"nmap -A -p- {SCAN_SPEED} {{TARGET}} -oN {SESSION_DIR}/07_aggressive.txt"))
    menu_nmap.agregar_opcion("Detección de firewall/IDS", AccionBash("Firewall Evasion", f"nmap -sA -p 80,443,22,21,25 {{TARGET}} -oN {SESSION_DIR}/08_firewall.txt"))
    menu_nmap.agregar_opcion("Scripts específicos de servicios", AccionBash("Service Scripts", f"nmap --script http-enum,ssh-auth-methods,smb-enum-shares,ftp-anon {{TARGET}} -oN {SESSION_DIR}/09_scripts.txt"))
    menu_nmap.agregar_opcion("Auditoría de SSL/TLS", AccionBash("SSL/TLS Audit", f"nmap --script ssl-enum-ciphers,ssl-cert,ssl-date,ssl-heartbleed -p 443,8443 {{TARGET}} -oN {SESSION_DIR}/10_ssl.txt"))
    menu_nmap.agregar_opcion("Traceroute de red", AccionBash("Traceroute", f"nmap --traceroute {{TARGET}} -oN {SESSION_DIR}/11_traceroute.txt"))
    
    cmd_auto = f"echo '[+] Iniciando escaneo automatizado completo...' && " \
               f"nmap -sn {{TARGET}} -oN {SESSION_DIR}/12a_auto_discovery.txt && " \
               f"nmap -sS -p- {SCAN_SPEED} {MIN_RATE} {{TARGET}} -oN {SESSION_DIR}/12b_auto_ports.txt && " \
               f"nmap -sV -sC {{TARGET}} -oN {SESSION_DIR}/12c_auto_services.txt && " \
               f"echo '[+] Batería completada. Resultados en {SESSION_DIR}/'"
    menu_nmap.agregar_opcion("Escaneo completo automatizado", AccionBash("Automated Scan", cmd_auto))
    
    # Aquí inyectamos el nuevo explorador de archivos basado en menús
    menu_nmap.agregar_opcion("=> LEER RESULTADOS GUARDADOS <=", AccionMenuDinamico("Explorador", generar_menu_carpetas))

    menu_reconocimiento = Menu("RECONOCIMIENTO (Information Gathering)")
    menu_reconocimiento.agregar_opcion("Mostrar Objetivo Actual", AccionBash("Echo Target", "echo 'El objetivo configurado actualmente es: {TARGET}'"))
    menu_reconocimiento.agregar_opcion("Configurar Objetivo / Rango", menu_objetivo)
    menu_reconocimiento.agregar_opcion("Menú de Auditoría Nmap (14 Modos)", menu_nmap) 







    menu_wireless = Menu("AUDITORÍA INALÁMBRICA (WiFi)")
    menu_wireless.agregar_opcion("Activar Modo Monitor", AccionBash("Airmon-ng", "echo 'Simulando: airmon-ng start wlan0'"))
    menu_wireless.agregar_opcion("Escanear Redes (Airodump-ng)", AccionBash("Airodump", "echo 'Simulando: airodump-ng wlan0mon'"))

    menu_explotacion = Menu("EXPLOTACIÓN Y POST-EXPLOTACIÓN") 
    menu_explotacion.agregar_opcion("Iniciar Metasploit Framework", AccionBash("MSFConsole", "msfconsole -q -x 'help'"))
    menu_explotacion.agregar_opcion("Buscar Exploits (SearchSploit)", AccionBash("SearchSploit", "searchsploit linux privilege escalation"))

    menu_principal = Menu("KALI LINUX - RED TEAM TOOLBOX")
    menu_principal.agregar_opcion("Cambiar Dirección MAC (Macchanger)", AccionMenuDinamico("Interfaces", generar_menu_interfaces))
    menu_principal.agregar_opcion("Reconocimiento e Inteligencia", menu_reconocimiento)
    menu_principal.agregar_opcion("Auditoría Inalámbrica", menu_wireless)
    menu_principal.agregar_opcion("Explotación", menu_explotacion)
    menu_principal.agregar_opcion("Actualizar Repositorios Locales", AccionBash("Apt Update", "sudo apt update && sudo apt upgrade"))

    app = AplicacionTUI(stdscr, menu_principal)
    app.ejecutar()

if __name__ == "__main__":
    curses.wrapper(main)