<div align="center">

<img src="images/logo.png" alt="logo" width="800" height="auto" />

<h1>DragonFly System</h1>

**Red Team Toolbox** — Auditoría Inalámbrica, HID Attack & Network Offensive

<br/>

[![GitHub repo size](https://img.shields.io/github/repo-size/whoamijas0n/DragonFly?style=for-the-badge&color=1a1a2e&labelColor=0d0d1a)](https://github.com/whoamijas0n/DragonFly)
[![GitHub language count](https://img.shields.io/github/languages/count/whoamijas0n/DragonFly?style=for-the-badge&color=1a1a2e&labelColor=0d0d1a)](https://github.com/whoamijas0n/DragonFly)
[![GitHub forks](https://img.shields.io/github/forks/whoamijas0n/DragonFly?style=for-the-badge&color=1a1a2e&labelColor=0d0d1a)](https://github.com/whoamijas0n/DragonFly)
[![GitHub Issues](https://img.shields.io/github/issues/whoamijas0n/DragonFly?style=for-the-badge&color=1a1a2e&labelColor=0d0d1a)](https://github.com/whoamijas0n/DragonFly/issues/new)
[![GitHub Pull Requests](https://img.shields.io/github/issues-pr/whoamijas0n/DragonFly?style=for-the-badge&color=1a1a2e&labelColor=0d0d1a)](https://github.com/whoamijas0n/DragonFly/issues/new)


<br/>

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-A22846?style=for-the-badge&logo=Raspberry%20Pi&logoColor=white)
![Kali Linux](https://img.shields.io/badge/Kali_Linux-557C94?style=for-the-badge&logo=kali-linux&logoColor=white)
![Espressif](https://img.shields.io/badge/ESP32-E7352C?style=for-the-badge&logo=espressif&logoColor=white)

<br/>


<h4>
  <a href="https://github.com/whoamijas0n/DragonFly/">[-]  View Demo</a>
  &nbsp;|&nbsp;
  <a href="https://github.com/whoamijas0n/DragonFly">[-]  Documentation</a>
  &nbsp;|&nbsp;
  <a href="https://github.com/whoamijas0n/DragonFly/issues/new">[-]  Report Bug</a>
  &nbsp;|&nbsp;
  <a href="https://github.com/whoamijas0n/DragonFly/issues/new">[-]  Request Feature</a>
</h4>

</div>

<br/>

DragonFly es una suite de auditoría y pentesting modular diseñada para operaciones de Red Team en entornos controlados. Proporciona una interfaz unificada para ejecutar técnicas de reconocimiento, ataques inalámbricos, inyección de pulsaciones HID y manipulación de señales RF/Bluetooth, con soporte nativo para hardware portátil basado en SBC y estaciones de trabajo convencionales.

La arquitectura del sistema separa claramente la lógica de ataque de la capa de presentación, permitiendo despliegues escalables desde una Raspberry Pi Zero con pantalla táctil hasta un entorno de escritorio completo con Kali Linux.

---

## Advertencia Legal:

DragonFly ha sido desarrollado exclusivamente con fines educativos y para la realización de auditorías de seguridad autorizadas por escrito. El uso de esta herramienta contra sistemas o redes sin el consentimiento explícito del propietario constituye una violación de las leyes de ciberseguridad en la mayoría de jurisdicciones. Los desarrolladores no asumen responsabilidad por el mal uso de este software. La ética profesional y el cumplimiento normativo son responsabilidad exclusiva del operador.

---

<div align="center">
  
## Edición Raspberry Pi (raspi.py)

</div>

### Descripción Técnica

Esta variante está optimizada para ejecución en hardware de recursos limitados con interfaces táctiles de baja resolución (320x240 píxeles). Implementa un sistema de navegación por menús jerárquicos con retroalimentación visual en tiempo real, gestión de memoria mediante garbage collection explícito y ejecución asíncrona de comandos para mantener la capacidad de respuesta de la interfaz.

### Hardware y Sistema Operativo

El entorno de ejecución recomendado es el siguiente:

<div align="center">



| Componente | Especificación |
|---|---|
| Placa | Raspberry Pi Zero 2 WH |
| Alimentación | Batería PiSugar 3 (o compatible) |
| Pantalla | Pantalla táctil resistiva/capacitiva de 2.4" (320x240) |
| Sistema Operativo | Raspberry Pi OS 32-bits con entorno gráfico (Legacy o Bookworm Desktop) |


</div>

> Los siguientes enlaces son referencias de ejemplo para orientar la compra del hardware. Los precios y la disponibilidad pueden variar.
>
> - Raspberry Pi Zero 2 WH: [https://amzn.to/example-rpizero2](https://amzn.to/example-rpizero2)
> - Batería PiSugar 3: [https://amzn.to/example-pisugar3](https://amzn.to/example-pisugar3)
> - Pantalla Táctil 2.4": [https://amzn.to/example-24screen](https://amzn.to/example-24screen)

---

### Desglose de Herramientas

#### 1. Reconocimiento (Nmap)

Módulo de escaneo de red basado en `nmap`. El operador introduce una IP objetivo mediante un teclado numérico táctil emergente y opcionalmente activa un modo de rango CIDR (`/8`, `/16`, `/24`, `/32`). Los comandos disponibles cubren los flujos de reconocimiento más comunes en un pentest:

<div align="center">


| Opción | Descripción |
|---|---|
| Descubrimiento | Detección de hosts activos (`-sn`) |
| Puertos comunes | Top 1000 puertos TCP (`-sS -T3 --top-ports 1000`) |
| Full TCP | Escaneo completo de los 65535 puertos |
| Servicios/Versión | Detección de versiones de servicios (`-sV`) |
| Detección OS | Identificación del sistema operativo (`-O`) |
| UDP Comunes | Top 100 puertos UDP |
| Vulnerabilidades | Scripts `vuln` y `exploit` de Nmap |
| Agresivo | Escaneo combinado (`-A -p-`) |
| Firewall/IDS | Prueba de reglas de filtrado ACK scan |
| Scripts servicios | Enumeración HTTP, SMB, FTP, SSH |
| SSL/TLS | Auditoría de cifrados y certificados |
| Traceroute | Mapeo de ruta hasta el objetivo |
| Automatizado | Pipeline completo: descubrimiento, puertos y servicios en secuencia |


</div>

Cada escaneo crea automáticamente una carpeta de sesión con la marca temporal dentro de `Resultados_Nmap/Auditoria-YYYY-MM-DD-HH-MM-SS/` y guarda la salida en archivos `.txt` numerados. El botón "Ver Resultados" permite navegar y leer estos archivos directamente desde la interfaz táctil.

#### 2. MAC Changer

Permite cambiar la dirección MAC de cualquier interfaz de red detectada en el sistema. Las operaciones disponibles son:

- **Ver Estado**: muestra la MAC actual y la original de fábrica.
- **MAC Random**: genera y aplica una dirección completamente aleatoria.
- **Reset Original**: restaura la MAC de fábrica del adaptador.
- **Mismo Fabricante**: aleatoriza solo la porción de dispositivo manteniendo el OUI del fabricante.

Cada operación baja la interfaz, aplica el cambio con `macchanger` y la vuelve a levantar automáticamente.

#### 3. Auditoría WiFi

Módulo central de auditoría inalámbrica. Agrupa cinco flujos de ataque/análisis:

- **Activar Monitor**: pone la interfaz seleccionada en modo monitor usando `airmon-ng`, terminando procesos conflictivos antes.
- **Captura Handshake**: escanea redes disponibles durante 15 segundos, permite seleccionar el objetivo y un cliente (o broadcast), y lanza `airodump-ng` para captura simultánea con `aireplay-ng -0` para forzar la reautenticación. Los archivos `.cap` se guardan en `Resultados_Handshake/Auditoria-{timestamp}/`.
- **Ataque Evil Twin**: flujo completo de AP falso con portal cautivo (ver sección dedicada más adelante).
- **Desautenticación**: envía paquetes deauth dirigidos a un cliente o en broadcast contra un BSSID objetivo.
- **Explorar Handshakes / Explorar Evil Twin**: navegador de archivos integrado para revisar capturas y credenciales de sesiones anteriores.

#### 4. Gadget BLE

Interfaz de control para el hardware externo Blue-Fly (ESP32). La aplicación detecta automáticamente el puerto serie (`/dev/ttyACM*`, `/dev/ttyUSB*`) y sincroniza con el firmware esperando el mensaje `Gadget listo`. Si el dispositivo se desconecta durante la sesión, el módulo gestiona la reconexión automática sin bloquear la interfaz gráfica. Las funciones disponibles son: iniciar Sweep Jam, detener la interferencia y consultar el estado activo del módulo.

#### 5. Rubber Ducky

Ejecuta scripts de inyección de pulsaciones a través del dispositivo HID USB configurado (`/dev/hidg0`). El módulo lista automáticamente todos los archivos `.txt` contenidos en la carpeta `payloads/` y permite ejecutarlos con un toque. Antes de ejecutar cualquier payload, espera 2 segundos para que el operador posicione el cursor en el sistema objetivo.

#### 6. Utilidades OS

Conjunto de herramientas de soporte operacional:

- Cambio de interfaz USB (Host/Gadget) con reinicio controlado.
- Gestión de interfaces de red y estado del sistema.
- Escáner y gestor de conexiones Bluetooth.
- Herramientas de diagnóstico de conectividad.

---

### Gestión de Archivos y Sesiones

El script crea y mantiene tres directorios raíz en la misma ubicación desde donde se ejecuta:

<div align="center">

| Directorio | Contenido |
|---|---|
| `Resultados_Nmap/` | Carpetas de sesión con archivos `.txt` de salida de Nmap |
| `Resultados_Handshake/` | Capturas `.cap` de handshakes WPA/WPA2 |
| `Resultados_EvilTwin/` | Archivos `credentials.log` con datos capturados por el portal |

</div>

Cada sesión genera su propia subcarpeta con nombre `Auditoria-{YYYY-MM-DD-HH-MM-SS}`, garantizando que múltiples ejecuciones no sobreescriban datos anteriores.

---

### Evil Twin y Portales Cautivos

El flujo del ataque Evil Twin opera en cuatro fases coordinadas:

1. **Selección de interfaz de AP**: el operador elige la interfaz que emitirá el AP falso.
2. **Selección de red objetivo**: la herramienta escanea y muestra las redes disponibles. Al seleccionar una, clona su SSID y canal.
3. **Selección de portal cautivo**: el script lee la carpeta `evil_portals/` y lista todos los subdirectorios que contengan un archivo `index.html`. Cada subdirectorio es un portal independiente.
4. **Modo de desautenticación**: el operador elige entre deauth broadcast (expulsa a todos los clientes simultáneamente) o deauth dirigido (escanea clientes asociados y selecciona uno o varios).

Durante el ataque, la herramienta levanta `hostapd` para el AP falso, `dnsmasq` como servidor DHCP/DNS con resolución universal hacia la IP del AP, y un servidor web Python integrado en el puerto 80 que sirve el portal seleccionado. Cualquier petición HTTP que no corresponda a un archivo local es redirigida a `index.html`, completando la trampa del portal cautivo. Las credenciales enviadas por formularios GET y POST se escriben en tiempo real en `Resultados_EvilTwin/Auditoria-{timestamp}/credentials.log`.

#### Estructura de la carpeta `evil_portals/`


```
evil_portals/
└── nombre_del_portal/
    ├── index.html          # Página principal del portal (obligatorio)
    ├── success.html        # Página de redirección post-credencial (opcional)
    ├── assets/             # Recursos estáticos: CSS, JS, imágenes (opcional)
    └── capture.php         # Alternativa backend para procesamiento de credenciales (opcional)
```


El repositorio incluye dos portales por defecto. Para crear un portal personalizado funcional, el usuario debe cumplir los siguientes requisitos:

- Crear un subdirectorio dentro de `evil_portals/` con cualquier nombre sin espacios.
- El directorio debe contener obligatoriamente un archivo `index.html` en su raíz. Sin él, el portal no aparecerá listado en la interfaz.
- El formulario de captura debe enviar los datos mediante `method="GET"` o `method="POST"` con `action="/"` o sin atributo de acción. El servidor de captura registra ambos métodos.
- Los archivos estáticos (CSS, imágenes, JS) deben referenciarse con rutas relativas. El servidor copia todo el contenido del directorio del portal a `/tmp/` antes de servirlo.
- El portal debe ser autónomo: no puede depender de recursos externos (CDNs, APIs) ya que el dispositivo víctima no tendrá acceso a internet durante el ataque.

---

### Rubber Ducky — Payloads y Sintaxis

Los scripts de inyección se almacenan como archivos `.txt` dentro de la carpeta `payloads/`. El módulo `ducky_logic.py` los lee línea por línea y los traduce a reportes HID de 8 bytes escritos directamente en `/dev/hidg0`.

#### Sintaxis básica soportada

<div align="center">

| Comando | Argumento | Descripción |
|---|---|---|
| `STRING` | texto | Escribe la cadena carácter por carácter |
| `DELAY` | milisegundos | Pausa la ejecución el tiempo indicado |
| `ENTER` | — | Tecla Enter |
| `GUI` | tecla | Tecla Windows/Super + tecla adicional |
| `ALT` | tecla | Alt + tecla adicional |
| `CTRL` | tecla | Control + tecla adicional |
| `SHIFT` | tecla | Shift + tecla adicional |
| `TAB` | — | Tecla Tab |
| `ESC` | — | Tecla Escape |
| `UP / DOWN / LEFT / RIGHT` | — | Teclas de dirección |
| `SPACE` | — | Barra espaciadora |
| `BACKSPACE` | — | Retroceso |
| `DELETE` | — | Suprimir |
| `REM` | comentario | Línea ignorada (comentario) |

</div>

Los caracteres en mayúscula son tratados automáticamente como `Shift + minúscula`. Los caracteres especiales que requieren Shift en distribución US (`:`  `?`  `_`  `+`  `"`  `>`  `<`  `|`  `{`  `}` `~`) están mapeados correctamente. Las combinaciones de dos teclas se escriben en la misma línea separadas por espacio (`GUI r`, `CTRL ALT t`).

**Ejemplo de payload:**

```
REM Abrir terminal en Windows
DELAY 500
GUI r
DELAY 400
STRING cmd
ENTER
DELAY 800
STRING whoami
ENTER
```

---

### Cambio de Interfaz USB: Host vs. Gadget

La Pi Zero 2 W dispone de un único puerto USB OTG que puede operar en dos modos excluyentes:

- **Modo Host**: la Pi actúa como controladora USB, permitiendo conectar dispositivos externos como antenas Wi-Fi USB o teclados.
- **Modo Gadget (HID)**: la Pi se anuncia al ordenador anfitrión como un teclado USB estándar, habilitando la ejecución de payloads Rubber Ducky a través de `/dev/hidg0`.

Cambiar entre ambos modos requiere modificar la configuración del kernel y recargar los módulos del sistema, lo que hace necesario un reinicio completo del dispositivo. Esta operación está disponible desde el menú "Utilidades OS" y muestra una advertencia antes de ejecutarse. Es la razón por la que el flujo de instalación para la versión Raspi incluye un paso dedicado a configurar el gadget HID al inicio del sistema.

---

<div align="center">
  
## Edición de Escritorio — `desktop.py`

</div>

### Descripción Técnica

La edición de escritorio está adaptada para laptops o placas Raspberry Pi más potentes (Pi 4, Pi 5) que ejecuten Kali Linux con entorno gráfico. La GUI utiliza `customtkinter` en lugar del `tkinter` nativo, proporcionando widgets modernos con bordes redondeados y una estética dark más refinada. La ventana arranca en modo pantalla completa con topmost activo, presentando un sidebar fijo con los módulos de navegación en la columna izquierda y un panel de contenido scrollable en la columna derecha.

### Diferencias respecto a la edición Raspberry Pi

<div align="center">

| Característica | Edición Raspi | Edición Desktop |
|---|---|---|
| Framework GUI | `tkinter` nativo | `customtkinter` |
| Navegación | Táctil, scroll por arrastre | Ratón y teclado estándar |
| Layout | Menús apilados en panel único | Sidebar fijo + panel principal |
| Cambio USB Host/Gadget | Disponible (hardware OTG) | No disponible (laptops estándar sin OTG) |
| Teclados táctiles emergentes | Sí (numérico y alfanumérico) | No (se usa el teclado físico) |
| Rubber Ducky | Requiere USB Gadget HID activo | Requiere adaptador USB HID externo compatible |
| Integración BLE Gadget | Via USB serie | Via USB serie (mismo módulo `gadget_handler.py`) |

</div>

Las funcionalidades de Reconocimiento Nmap, MAC Changer, Auditoría WiFi, Evil Twin, Rubber Ducky y Gadget BLE operan de forma idéntica en cuanto a lógica y comandos subyacentes. La diferencia está en la interacción: en la edición desktop el operador usa la navegación estándar de ventanas, atajos de teclado y el ratón, sin los teclados emergentes táctiles ni la lógica de scroll por gestos.

La barra lateral presenta los módulos numerados del 0 al 6 y permanece visible en todo momento, permitiendo saltar entre secciones sin necesidad de volver a un menú raíz. La consola de salida de comandos se muestra directamente en el panel principal con fuente monoespaciada y actualización en tiempo real.

---

<div align="center">


## Instalación — `install.sh`

</div>

### Clonar el repositorio

```bash
git clone https://github.com/whoamijas0n/DragonFly.git
cd DragonFly
sudo ./install.sh
```

El script requiere privilegios de root. Si se ejecuta con `sudo`, detecta automáticamente el usuario real mediante `$SUDO_USER` para aplicar la configuración de autostart en el directorio home correcto.

### Opciones del menú de instalación

<div align="center">

| Opción | Descripción |
|---|---|
| 1) Instalación Completa | Ejecuta las tres fases en secuencia (Todo-en-Uno) |
| 2) Solo Dependencias | Instala paquetes APT y librerías Python |
| 3) Solo USB Gadget | Configura el script HID en `/usr/local/bin/usb_gadget.sh` |
| 4) Solo Auto-Inicio | Crea la entrada `.desktop` de autostart y regla sudoers |
| 5) Salir | Termina sin realizar cambios |

</div>

---

### Flujo recomendado: Edición Raspberry Pi

La instalación para la Pi Zero 2 W requiere las tres fases. Se recomienda ejecutarlas en el orden que ofrece la opción 1 (Todo-en-Uno) o manualmente en este orden:

**Paso 1 — Dependencias (Opción 2)**

Instala todos los paquetes de sistema necesarios:

```
python3, python3-tk, python3-serial
nmap, macchanger, aircrack-ng, hostapd, dnsmasq, iptables
network-manager, bluez, rfkill, lxterminal
```

**Paso 2 — USB Gadget (Opción 3)**

Crea el script `/usr/local/bin/usb_gadget.sh` que configura el descriptor HID de teclado en el subsistema `configfs` del kernel (`/sys/kernel/config/usb_gadget/g1`). El descriptor reporta al host anfitrión como un teclado HID estándar con report length de 8 bytes y el descriptor HID completo embebido. Este script debe ejecutarse antes de iniciar `raspi.py` para que `/dev/hidg0` esté disponible.

**Paso 3 — Auto-Inicio (Opción 4)**

Crea la entrada `~/.config/autostart/raspy.desktop` para que LXDE/Openbox lance automáticamente `raspi.py` al iniciar el entorno gráfico, dentro de un terminal `lxterminal` con permisos sudo. Además, añade una regla `NOPASSWD` en `/etc/sudoers.d/010_dragonfly` para que el script pueda ejecutar comandos privilegiados sin solicitar contraseña, requisito indispensable para las funciones de red y HID.

Tras completar las tres fases, se recomienda reiniciar la Raspberry Pi para que todos los módulos del kernel y la configuración de autostart tomen efecto.

---

### Flujo recomendado: Edición Desktop

Para laptops con Kali Linux, solo es necesaria la opción de dependencias:

**Paso 1 — Dependencias (Opción 2)**

El proceso es idéntico al descrito para Raspi. Una vez completado, la herramienta se lanza manualmente:

```bash
cd DragonFly
sudo python3 desktop.py
```

No se configura autostart ni USB Gadget, ya que los portátiles estándar no disponen del controlador USB OTG necesario para emular un dispositivo HID. Si el operador dispone de un adaptador USB HID externo compatible, puede configurar el gadget manualmente y ajustar la variable `HID_DEVICE` en `ducky_logic.py` si la ruta del dispositivo difiere de `/dev/hidg0`.

---

<div align="center">


## Gadgets de Hardware — Firmware


</div>

La carpeta `gadgets/` contiene el firmware para extender las capacidades físicas del sistema más allá de lo que ofrece el software puro. Estos módulos de hardware se comunican con la aplicación principal a través del puerto serie USB y son gestionados por `gadget_handler.py`.

---

### Blue-Fly

**Archivo de firmware:** `BlueFly_Firmware.ino`
**Gestor de software:** `gadget_handler.py`

Blue-Fly es un gadget de interferencia y análisis de radiofrecuencia en la banda de 2.4 GHz, construido sobre un ESP32 con dos módulos nRF24L01 conectados a los buses VSPI y HSPI del microcontrolador. El firmware aprovecha la arquitectura dual-core del ESP32 para maximizar la cobertura espectral: Core 0 gestiona el módulo VSPI (comenzando en el canal 45) y Core 1 gestiona el módulo HSPI (comenzando en el canal 60) de forma completamente paralela e independiente.

#### Capacidades

- **Jammer de 2.4 GHz (Sweep Jam)**: los dos módulos nRF24L01 recorren los 84 canales de la banda de 2.4 GHz a máxima potencia (`RF24_PA_MAX`), tasa de datos de 2 Mbps y sin CRC, transmitiendo payloads de ruido de 5 bytes. La saturación simultánea desde dos módulos en canales complementarios maximiza la densidad de interferencia, afectando comunicaciones Wi-Fi, Bluetooth y Zigbee que operen en la misma banda.
- **Frequency Hopping**: un toggle switch físico conectado al GPIO 33 selecciona el modo de salto entre **SWEEP** (barrido secuencial) y **RANDOM** (salto aleatorio), sin necesidad de modificar el firmware ni reiniciar el dispositivo.
- **Control por duración**: el comando `SWEEP_JAM <modo> <segundos>` activa la interferencia durante un tiempo definido y la detiene automáticamente al expirar. Pasar `0` segundos activa el modo indefinido.
- **Pantalla OLED**: un display SSD1306 de 128x64 conectado por I2C muestra el estado del gadget (Iniciado / Detenido) con un indicador parpadeante durante la operación activa.
- **Protocolo serie**: la comunicación con el software anfitrión se realiza a 115200 baudios. Los comandos soportados son `SWEEP_JAM`, `STOP` y `STATUS`. El firmware responde con `JAMMING_STARTED`, `STOPPED`, `JAMMING_ACTIVE` o `JAMMING_INACTIVE` según corresponda.

El módulo `gadget_handler.py` gestiona la conexión serie con reconexión automática y hot-plugging. Al iniciar, espera la cadena `Gadget listo` que el firmware emite en `setup()`. Si el dispositivo se desconecta físicamente durante la sesión, el gestor detecta la ausencia del archivo de dispositivo en `/dev/` y limpia el estado de forma segura, permitiendo una reconexión posterior sin reiniciar la aplicación.



---

### Pinout Físico — Blue-Fly

<div align="center">


### HSPI

| 1st nRF24L01 module Pin | HSPI Pin (ESP32) | 10uf capacitor |
|---------------|------------------|--------------------|
| VCC           | 3.3V             | (+) capacitor |
| GND           | GND              | (-) capacitor |
| CE            | GPIO 16          |
| CSN           | GPIO 15          |
| SCK           | GPIO 14          |
| MOSI          | GPIO 13          |
| MISO          | GPIO 12          |
| IRQ           |                  |



### VSPI 



| 2nd nRF24L01 module Pin | VSPI Pin (ESP32) | 10uf capacitor |
|---------------|------------------|--------------------|
| VCC           | 3.3V             | (+) capacitor |
| GND           | GND              | (-) capacitor |
| CE            | GPIO 22          |
| CSN           | GPIO 21          |
| SCK           | GPIO 18          |
| MOSI          | GPIO 23          |
| MISO          | GPIO 19          |
| IRQ           |                  |



> Se recomienda colocar un condensador electrolítico de 100 µF entre VCC y GND en cada módulo nRF24L01 para estabilizar la alimentación durante los picos de transmisión a máxima potencia. La ausencia de este condensador puede causar reinicios inesperados del ESP32 o comportamiento errático de los módulos de radio.

### OLED Display I2C 



| 0.96" OLED Display I2C | ESP32 |
|------------------------|-------|
|          GND           |  GND  |
|          VCC           | 3.3V  |
|          SCL           |GPIO 5 |
|          SDA           |GPIO 4 |

</div>

---

<div align="center">

## Estructura del Repositorio

</div>

```
DragonFly/
├── raspi.py                # Interfaz táctil para Raspberry Pi
├── desktop.py              # Interfaz desktop para Kali Linux
├── ducky_logic.py          # Motor de inyección HID Rubber Ducky
├── gadget_handler.py       # Gestor de comunicación serie con ESP32
├── install.sh              # Instalador automatizado
├── payloads/               # Scripts Rubber Ducky (.txt)
├── evil_portals/           # Portales cautivos HTML
│   ├── portal_01/
│   │   └── index.html
│   └── portal_02/
│       └── index.html
└── gadgets/
    └── BlueFly_Firmware.ino
```

---

<div align="center">


## Top de contribuidores

</div>

<div align="center">

<a href="https://github.com/whoamijas0n/DragonFly/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=whoamijas0n/DragonFly" alt="contrib.rocks image" />
</a>

</div>

---

<div align="center">

## Licencia

</div>

Este proyecto se distribuye bajo los términos de la licencia MIT. Consulta el archivo `LICENSE` en la raíz del repositorio para más información.

---
<div align="center">
<h2>GET FREEDOM</h2>
</div>
