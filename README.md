
<div align="center">

  <img src="images/logo.png" alt="logo" width="800" height="auto" />
  <h1>DragonFly System</h1>
  
  <p>
Red Team Toolbox — Auditoria Inalambrica, HID Attack & Network Offensive

  </p>
  
  
![GitHub repo size](https://img.shields.io/github/repo-size/whoamijas0n/DragonFly?style=for-the-badge)
![GitHub language count](https://img.shields.io/github/languages/count/whoamijas0n/DragonFly?style=for-the-badge)
![GitHub forks](https://img.shields.io/github/forks/whoamijas0n/DragonFly?style=for-the-badge)
![GitHub Issues or Pull Requests](https://img.shields.io/github/issues/whoamijas0n/DragonFly?style=for-the-badge)
![GitHub Issues or Pull Requests](https://img.shields.io/github/issues-pr/whoamijas0n/DragonFly?style=for-the-badge)

   
<h4>
    <a href="https://github.com/whoamijas0n/DragonFly/">View Demo</a>
  <span> · </span>
    <a href="https://github.com/whoamijas0n/DragonFly">Documentation</a>
  <span> · </span>
    <a href="https://github.com/whoamijas0n/DragonFly/issues/new">Report Bug</a>
  <span> · </span>
    <a href="https://github.com/whoamijas0n/DragonFly/issues/new">Request Feature</a>
  </h4>
</div>

<br />

### Top contributors:

<div align="center">

<a href="https://github.com/whoamijas0n/DragonFly/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=whoamijas0n/DragonFly" alt="contrib.rocks image" />
</a>


/>



---

## Tabla de Contenidos

- [Descripcion del Proyecto](#descripcion-del-proyecto)
- [Version Raspberry Pi Zero 2W](#version-raspberry-pi-zero-2w)
  - [Descripcion](#descripcion-raspi)
  - [Hardware y Sistema Operativo](#hardware-y-sistema-operativo)
  - [Funcionalidades y Menus](#funcionalidades-y-menus)
- [Version Desktop — Kali Linux](#version-desktop--kali-linux)
  - [Descripcion](#descripcion-desktop)
  - [Requisitos del Sistema](#requisitos-del-sistema)
  - [Funcionalidades y Menus](#funcionalidades-y-menus-desktop)
- [Instalacion](#instalacion)
  - [Instalacion en Raspberry Pi Zero 2W](#instalacion-en-raspberry-pi-zero-2w)
  - [Instalacion en Desktop — Kali Linux](#instalacion-en-desktop--kali-linux)
  - [Opciones del Instalador](#opciones-del-instalador)
- [Gadgets](#gadgets)
  - [BlueFly — Jammer Bluetooth de Doble Canal](#bluefly--jammer-bluetooth-de-doble-canal)
  - [Instalacion del Firmware](#instalacion-del-firmware)
- [Estructura del Repositorio](#estructura-del-repositorio)
- [Aviso Legal](#aviso-legal)
- [Licencia](#licencia)

---

## Descripcion del Proyecto

**DragonFly** es un conjunto de herramientas ofensivas de red orientado a profesionales de la seguridad informatica y equipos de Red Team. El proyecto nace de la necesidad de contar con una plataforma portatil, modular y extensible que centralice en una sola interfaz las tecnicas mas utilizadas en auditorias inalambricas modernas: desde ataques Evil Twin con portales cautivos personalizados hasta ejecucion de payloads HID estilo Rubber Ducky, pasando por escaneo activo de redes, gestion de Bluetooth y control de gadgets hardware externos.

DragonFly se presenta en dos versiones complementarias: una adaptada a la Raspberry Pi Zero 2W —pensada para operar como implante fisico de campo, compacto y autonomo— y otra para equipos de escritorio o laptops corriendo Kali Linux con entorno grafico, ideal para entornos de laboratorio o auditorias mas amplias. Ambas versiones comparten la misma filosofia de diseno: menus interactivos claros, modularidad real y hardware pensado para el trabajo en campo.

El repositorio tambien incluye una carpeta `gadgets/` con los firmwares para hardware complementario que se integra directamente con los scripts, y carpetas de recursos como `payloads/` y `evil_portals/` listas para ser pobladas con material personalizado.

> Este proyecto esta pensado exclusivamente para uso en entornos controlados y con autorizacion expresa. Consulta la seccion [Aviso Legal](#aviso-legal) antes de continuar.

---

## Version Raspberry Pi Zero 2W

### Descripcion {#descripcion-raspi}

`raspi.py` es el corazon de DragonFly en su forma mas portatil. Esta version esta disenada para ejecutarse sobre una Raspberry Pi Zero 2W equipada con pantalla tactil, lo que la convierte en un dispositivo totalmente autonomo: sin necesidad de teclado ni monitor externo. La interfaz grafica esta construida sobre `tkinter` y optimizada para pantallas tactiles de 2.4 pulgadas, con elementos de UI lo suficientemente grandes para ser operados con el dedo directamente en campo.

El script se auto-inicia al arrancar el sistema gracias al autostart configurado por el instalador, y corre con los privilegios necesarios para ejecutar herramientas de red sin intervencion del usuario. Esto lo hace ideal para escenarios de implante fisico o auditorias discretas donde la velocidad de despliegue es critica.

---

### Hardware y Sistema Operativo

El setup recomendado para `raspi.py` es el siguiente:

| Componente | Descripcion |
|---|---|
| **SBC** | Raspberry Pi Zero 2W |
| **Bateria** | PiSugar para Raspberry Pi Zero |
| **Pantalla** | Pantalla tactil de 2.4 pulgadas |
| **OS** | Raspberry Pi OS 32-bit con entorno grafico |

**Notas sobre la pantalla:** El script esta construido especificamente para pantallas tactiles. Tecnicamente puede usarse otro tipo de pantalla, pero la interaccion completa (menus, submenus, ejecucion de acciones) esta pensada y calibrada para control tactil. El uso de una pantalla no tactil requerira adaptaciones en la logica de navegacion.

**Referencias de compra:**

- [Raspberry Pi Zero 2W en Amazon](https://www.amazon.com/s?k=raspberry+pi+zero+2w)
- [PiSugar Battery para Raspberry Pi Zero en Amazon](https://www.amazon.com/s?k=pisugar+raspberry+pi+zero)
- [Pantalla tactil 2.4 pulgadas para Raspberry Pi en Amazon](https://www.amazon.com/s?k=2.4+inch+touchscreen+raspberry+pi)

**Sistema Operativo:** Se utiliza **Raspberry Pi OS de 32 bits con entorno grafico (Desktop)**. La version Lite no es compatible, ya que el script requiere un servidor de display funcional para levantar la interfaz `tkinter`.

---

### Funcionalidades y Menus

El script presenta un menu principal desde el cual se accede a cada modulo. A continuacion se documenta cada seccion y sus opciones internas.

---

#### Network Scanner

Modulo de escaneo de redes locales mediante `nmap`. Permite al operador obtener un mapa rapido de los dispositivos activos en la red a la que la Raspberry esta conectada.

- **Escanear red local** — Lanza un escaneo `nmap` sobre el segmento de red detectado automaticamente. Muestra una lista de hosts activos con sus direcciones IP y MAC.
- **Ver resultados** — Muestra en pantalla el ultimo resultado de escaneo almacenado en sesion.

Los resultados se despliegan en la propia interfaz tactil, paginados para facilitar la lectura en pantallas pequenas.

---

#### Wi-Fi Manager

Gestion de interfaces inalambricas y operaciones basicas sobre redes Wi-Fi. Actua como punto de entrada para preparar el entorno antes de ejecutar ataques mas avanzados.

- **Ver redes disponibles** — Lista las redes Wi-Fi al alcance con SSID, BSSID, canal y nivel de senal.
- **Cambiar MAC** — Invoca `macchanger` para asignar una direccion MAC aleatoria o personalizada a la interfaz de red activa.
- **Modo monitor** — Activa el modo monitor en la interfaz Wi-Fi seleccionada, requisito previo para capturas de handshakes y ataques Evil Twin.
- **Modo managed** — Devuelve la interfaz a modo administrado para reanudar conectividad normal.

---

#### Evil Twin

Uno de los modulos mas potentes del conjunto. Crea un punto de acceso falso que imita el SSID de una red legitima, combinado con un servidor DNS y un portal cautivo que captura credenciales cuando la victima intenta autenticarse.

- **Seleccionar red objetivo** — Muestra la lista de redes escaneadas para elegir el objetivo del ataque.
- **Lanzar Evil Twin** — Configura `hostapd` y `dnsmasq` automaticamente, levanta el AP falso y activa el portal cautivo asociado.
- **Seleccionar portal** — Permite elegir el portal cautivo a servir desde la carpeta `evil_portals/`.
- **Ver credenciales capturadas** — Muestra en pantalla las credenciales recibidas por el portal activo.
- **Detener** — Para todos los procesos asociados y restaura la configuracion de red.

##### Carpeta `evil_portals/`

Los portales cautivos se almacenan en la carpeta `evil_portals/` dentro del directorio del proyecto. El repositorio incluye actualmente dos portales preconfigurados listos para usar.

Para crear un portal cautivo funcional y compatible con el script, la estructura minima requerida es la siguiente:

```
evil_portals/
└── nombre_del_portal/
    ├── index.html       # Pagina principal del portal (formulario de login)
    └── post.php         # Manejador del formulario (captura y guarda credenciales)
```

El script sirve el portal usando el servidor integrado de Python (`http.server`) o un servidor ligero equivalente. El archivo `index.html` debe contener un formulario `<form>` con `method="POST"` apuntando a `post.php` o al endpoint que el script espera. Las credenciales capturadas se escriben en un archivo de texto en la raiz del portal o en la ruta configurada en el script.

**Recomendaciones para un portal convincente:**

- Replicar visualmente la pagina de login del router o del proveedor de internet que se quiere imitar (logos, fuentes, colores).
- Mantener el HTML autocontenido o con recursos locales para evitar dependencias de internet.
- Usar mensajes de error falsos tras el envio para dar mas credibilidad ("Contrasena incorrecta, intente de nuevo").
- Evitar referencias externas en el HTML que puedan delatar el portal como falso.

---

#### Rubber Ducky / HID Attack

Convierte la Raspberry Pi Zero 2W en un dispositivo de entrada HID (Human Interface Device), es decir, la hace aparecer ante cualquier computadora como un teclado USB legitimo. Al conectarla por el puerto USB al equipo objetivo, puede ejecutar payloads preconfigurados de forma automatica a la velocidad de escritura de una maquina, sin que el sistema operativo lo detecte como amenaza.

- **Seleccionar payload** — Muestra todos los archivos `.txt` dentro de la carpeta `payloads/` para elegir cual ejecutar.
- **Ejecutar payload** — Lanza el payload seleccionado escribiendo cada instruccion sobre `/dev/hidg0`.
- **Estado del gadget HID** — Verifica si el dispositivo HID esta activo y disponible.

##### Carpeta `payloads/`

Los payloads se almacenan como archivos `.txt` dentro de la carpeta `payloads/` en la raiz del proyecto. El motor de ejecucion (`ducky_logic.py`) interpreta la sintaxis estandar de Rubber Ducky Script.

**Comandos disponibles:**

| Comando | Descripcion | Ejemplo |
|---|---|---|
| `STRING` | Escribe texto literal | `STRING hola mundo` |
| `DELAY` | Espera N milisegundos | `DELAY 1000` |
| `ENTER` | Pulsa Enter | `ENTER` |
| `GUI` | Tecla Windows/Super | `GUI r` |
| `ALT` | Tecla Alt | `ALT F4` |
| `CTRL` | Tecla Control | `CTRL c` |
| `SHIFT` | Tecla Shift | `SHIFT TAB` |
| `TAB` | Tecla Tab | `TAB` |
| `ESC` | Tecla Escape | `ESC` |
| `UP / DOWN / LEFT / RIGHT` | Teclas de direccion | `UP` |
| `REM` | Comentario (ignorado) | `REM Esto es un comentario` |

**Ejemplo de payload — Abrir terminal y ejecutar comando:**

```
REM Abre terminal en Windows y ejecuta un comando
DELAY 500
GUI r
DELAY 500
STRING cmd
ENTER
DELAY 800
STRING whoami
ENTER
```

**Notas sobre compatibilidad de teclado:** El motor esta mapeado para teclado en distribucion US. Caracteres especiales como `:`, `?`, `_`, `"`, `{`, `}` estan manejados automaticamente mediante la tabla de modificadores internos del script.

##### Cambio de interfaz USB a modo Rubber Ducky

Por defecto, la Raspberry Pi Zero 2W opera su puerto micro-USB en modo OTG. Para que el sistema objetivo la reconozca como teclado HID, es necesario activar el gadget USB antes de conectarla. El script instalador se encarga de crear y configurar el script `/usr/local/bin/usb_gadget.sh`, que realiza los siguientes pasos al ejecutarse:

1. Carga los modulos del kernel `libcomposite` y `usb_f_hid`.
2. Crea un gadget HID en el filesystem `configfs` bajo `/sys/kernel/config/usb_gadget/g1`.
3. Configura el descriptor HID como teclado estandar de 8 bytes.
4. Activa el gadget sobre el UDC (USB Device Controller) disponible.

Una vez activo el gadget, el dispositivo `/dev/hidg0` queda disponible y los payloads pueden ejecutarse. Desde el menu de Rubber Ducky en el script se puede verificar el estado del gadget y lanzar payloads directamente.

> Para que el gadget persista entre reinicios, el instalador tambien configura el autostart del script. No es necesario activarlo manualmente en cada sesion.

---

#### Bluetooth Manager

Gestion basica de dispositivos Bluetooth cercanos mediante `bluez`.

- **Escanear dispositivos** — Realiza un descubrimiento Bluetooth activo y lista los dispositivos encontrados con nombre y direccion MAC.
- **Informacion del dispositivo** — Muestra detalles adicionales del dispositivo seleccionado.
- **Gadget BlueFly** — Accede al modulo de control del gadget externo BlueFly para operaciones avanzadas de interferencia Bluetooth.

---

## Version Desktop — Kali Linux

### Descripcion {#descripcion-desktop}

`desktop.py` es la version de DragonFly pensada para equipos mas potentes: laptops, PCs de escritorio, o Raspberry Pi de gama alta (Pi 4, Pi 5) que corran **Kali Linux con entorno grafico**. A diferencia de la version para Pi Zero, esta no esta limitada por el tamano de pantalla ni por la potencia del hardware, por lo que puede manejar operaciones mas intensas y una interfaz mas expandida.

La interfaz sigue siendo `tkinter`, pero con un layout adaptado a resoluciones estandar de escritorio. No requiere pantalla tactil —aunque es compatible— y esta disenada para operar con raton y teclado como cualquier aplicacion de escritorio. Su enfoque es ideal para laboratorios de seguridad, auditorias de campo con laptop o entornos de demostracion.

---

### Requisitos del Sistema

| Componente | Requerimiento |
|---|---|
| **Sistema Operativo** | Kali Linux (o cualquier distro Debian-based) con entorno grafico |
| **Python** | Python 3.x |
| **Interfaz de red** | Adaptador Wi-Fi con soporte para modo monitor |
| **Privilegios** | root o sudo para operaciones de red |
| **Dependencias** | Ver seccion de instalacion |

La version desktop no requiere hardware especifico mas alla de un adaptador Wi-Fi compatible con modo monitor y modo AP. Adaptadores con chipset **Atheros** (AR9271), **Ralink** (RT3070, RT5372) o **Realtek** (RTL8188, RTL8812AU) son los mas comunes y mejor soportados en Kali Linux.

---

### Funcionalidades y Menus {#funcionalidades-y-menus-desktop}

`desktop.py` comparte la filosofia modular de `raspi.py` y ofrece los mismos modulos principales, adaptados al contexto de escritorio.

---

#### Network Scanner

Mismo comportamiento que en la version raspi. Escaneo de red local via `nmap` con visualizacion de resultados en la ventana principal. Al correr en hardware mas potente, los escaneos son considerablemente mas rapidos.

---

#### Wi-Fi Manager

Gestion de interfaces inalambricas con las mismas opciones que la version raspi: listar redes, cambiar MAC, activar/desactivar modo monitor.

---

#### Evil Twin

Funcionalidad identica a la version raspi. Los portales cautivos de la carpeta `evil_portals/` son compatibles entre ambas versiones sin modificacion. Ver la seccion [Carpeta `evil_portals/`](#carpeta-evil_portals) para instrucciones de creacion de portales.

---

#### Rubber Ducky / HID Attack

En la version desktop, la ejecucion de payloads HID depende de que el equipo tenga configurado el gadget USB externo o un adaptador HID compatible. El modulo `ducky_logic.py` es identico en ambas versiones. Los payloads de la carpeta `payloads/` son directamente reutilizables. Ver la seccion [Carpeta `payloads/`](#carpeta-payloads) para la sintaxis y ejemplos.

---

#### Bluetooth Manager

Escaneo y gestion de dispositivos Bluetooth cercanos con la misma logica que en la version raspi, incluyendo la integracion con el gadget BlueFly si esta conectado por USB.

---

## Instalacion

El instalador automatizado `install.sh` gestiona todas las dependencias y configuraciones del sistema necesarias para poner en marcha DragonFly. Debe ejecutarse con privilegios de root desde el directorio raiz del repositorio.

```bash
git clone https://github.com/whoamijas0n/DragonFly.git
cd DragonFly
sudo ./install.sh
```

---

### Instalacion en Raspberry Pi Zero 2W

Para la version raspi, se recomienda ejecutar la **Instalacion Completa (opcion 1)** del menu del instalador. Esta opcion realiza los tres pasos de configuracion de forma secuencial y automatica:

1. Instala todas las dependencias del sistema via APT y pip.
2. Configura el gadget USB HID necesario para las funciones de Rubber Ducky.
3. Configura el autostart en el entorno grafico para que `raspi.py` se lance automaticamente al iniciar sesion, y otorga los permisos de sudoers necesarios para que el script pueda usar herramientas de red sin pedir contrasena.

**Tras la instalacion completa, se recomienda reiniciar la Raspberry Pi** para que todos los cambios surtan efecto.

---

### Instalacion en Desktop — Kali Linux

Para la version desktop, el paso relevante es unicamente la instalacion de dependencias (opcion 2). Las opciones de autostart y gadget USB son especificas del entorno de la Raspberry Pi Zero 2W y no son necesarias en un sistema de escritorio.

Tras instalar dependencias, el script puede ejecutarse directamente con:

```bash
sudo python3 desktop.py
```

---

### Opciones del Instalador

El instalador presenta un menu interactivo con las siguientes opciones:

---

#### Opcion 1 — Instalacion Completa (Todo-en-Uno)

Ejecuta las tres fases de configuracion en secuencia:

- Instala dependencias del sistema.
- Crea y configura el script del gadget USB HID.
- Configura el autostart y los permisos de sudoers.

Recomendada para una puesta en marcha limpia en Raspberry Pi Zero 2W.

---

#### Opcion 2 — Instalar Solo Dependencias (APT + Python)

Instala unicamente los paquetes del sistema necesarios para correr los scripts. Los paquetes instalados son:

```
python3  python3-tk  python3-serial
nmap  macchanger  aircrack-ng
hostapd  dnsmasq  iptables
network-manager  bluez  rfkill  lxterminal
```

Util cuando ya se tiene el sistema parcialmente configurado o cuando se quiere instalar solo en un equipo desktop sin necesidad de las otras configuraciones.

---

#### Opcion 3 — Configurar Solo USB Gadget

Crea el script `/usr/local/bin/usb_gadget.sh` con la configuracion HID completa. Este script, al ejecutarse, convierte la Raspberry Pi Zero 2W en un teclado HID ante el sistema objetivo.

Lo que hace internamente:

- Limpia cualquier gadget USB previo.
- Carga los modulos `libcomposite` y `usb_f_hid`.
- Configura el gadget con identificadores USB de Raspberry Pi.
- Escribe el descriptor HID de teclado estandar.
- Activa el gadget sobre el UDC disponible.

Util cuando ya se tienen las dependencias instaladas y solo se necesita reconfigurar el gadget (por ejemplo, tras un reinicio con configuracion perdida).

---

#### Opcion 4 — Configurar Solo Auto-Inicio y Sudoers

Crea la entrada de autostart en `~/.config/autostart/raspy.desktop` para que `raspi.py` se lance automaticamente al iniciar el entorno grafico. Tambien agrega una regla en `/etc/sudoers.d/010_dragonfly` que permite ejecutar el script con privilegios de root sin contrasena.

Util cuando el script ya estaba configurado y solo se necesita restaurar el comportamiento de inicio automatico, o cuando se cambia la ubicacion del proyecto y hay que actualizar las rutas en la configuracion de autostart.

---

#### Opcion 5 — Salir

Cierra el instalador sin realizar ninguna accion.

---

## Gadgets

La carpeta `gadgets/` contiene los firmwares para el hardware externo que se integra con DragonFly. Estos dispositivos amplian las capacidades ofensivas del sistema mas alla de lo que el software por si solo puede hacer, actuando como herramientas especializadas controladas directamente desde los scripts via comunicacion serie USB.

El protocolo de comunicacion es simple y basado en texto: el script envia comandos al gadget por el puerto serie y el gadget responde con confirmaciones o datos de estado. La clase `BLEGadget` en `gadget_handler.py` encapsula toda la logica de conexion, deteccion automatica de puerto, reconexion en caso de desconexion inesperada y comunicacion thread-safe con el dispositivo.

---

### BlueFly — Jammer Bluetooth de Doble Canal

**BlueFly** es un jammer Bluetooth de doble canal basado en ESP32 y dos modulos nRF24L01+. Aprovecha los dos buses SPI del ESP32 (VSPI y HSPI) para operar ambos modulos de radio de forma simultanea e independiente, cada uno asignado a un nucleo del procesador, logrando una cobertura de la banda de 2.4 GHz amplia y continua.

El firmware (`BlueFly_Firmware.ino`) implementa dos estrategias de interferencia seleccionables mediante un switch fisico conectado al pin GPIO 33:

- **Modo Sweep (switch HIGH):** Barrido de canales con paso complementario. El modulo VSPI realiza un barrido con paso +2/-2 entre los canales 2 y 79, mientras el HSPI realiza un barrido con paso +3/-3 partiendo de un canal diferente, garantizando cobertura cruzada de toda la banda.
- **Modo Random (switch LOW):** Salto aleatorio entre los primeros 15 canales en VSPI y los 15 canales superiores en HSPI, generando un patron impredecible de interferencia.

El gadget incluye una pequena pantalla OLED de 0.96" que muestra el estado en tiempo real (activo / detenido) con un indicador parpadeante durante el jamming.

**Comandos disponibles via serie (115200 baud):**

| Comando | Descripcion |
|---|---|
| `SWEEP_JAM <modulo> <segundos>` | Inicia el jamming durante N segundos (0 = indefinido) |
| `STOP <modulo>` | Detiene el jamming del modulo indicado |
| `STATUS` | Consulta el estado actual del gadget |

El script detecta automaticamente el puerto al que esta conectado el ESP32 (buscando descriptores `CP210`, `CH340`, `USB2.0-Serial`, etc.) y establece la conexion sin necesidad de configuracion manual.

---

#### Pinout — BlueFly

##### HSPI (1er modulo nRF24L01)

| Pin nRF24L01 | Pin HSPI (ESP32) | Capacitor 10uF |
|---|---|---|
| VCC | 3.3V | (+) capacitor |
| GND | GND | (-) capacitor |
| CE | GPIO 16 | |
| CSN | GPIO 15 | |
| SCK | GPIO 14 | |
| MOSI | GPIO 13 | |
| MISO | GPIO 12 | |
| IRQ | — | |

##### VSPI (2do modulo nRF24L01)

| Pin nRF24L01 | Pin VSPI (ESP32) | Capacitor 10uF |
|---|---|---|
| VCC | 3.3V | (+) capacitor |
| GND | GND | (-) capacitor |
| CE | GPIO 22 | |
| CSN | GPIO 21 | |
| SCK | GPIO 18 | |
| MOSI | GPIO 23 | |
| MISO | GPIO 19 | |
| IRQ | — | |

##### OLED Display I2C — 0.96" (opcional)

> Asegurate de usar la version del firmware con soporte OLED si incluyes la pantalla.

| Pin OLED (I2C) | Pin ESP32 |
|---|---|
| GND | GND |
| VCC | 3.3V |
| SCL | GPIO 5 |
| SDA | GPIO 4 |

> **Nota sobre los capacitores:** Se recomienda colocar un capacitor electrolitico de 10uF entre VCC y GND de cada modulo nRF24L01 lo mas cerca posible de los pines de alimentacion del modulo. Los nRF24L01 son notoriamente sensibles a caidas de tension, y el capacitor estabiliza el suministro y previene comportamientos erraticos o fallo de inicializacion.

---

### Instalacion del Firmware

El firmware de BlueFly se instala mediante el **Arduino IDE** con soporte para ESP32.

**Paso 1 — Configurar Arduino IDE para ESP32:**

Abre Arduino IDE y ve a `Archivo > Preferencias`. En el campo "Gestor de URLs adicionales de tarjetas", agrega la siguiente URL:

```
https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
```

Luego ve a `Herramientas > Placa > Gestor de tarjetas`, busca **esp32** e instala el paquete de Espressif Systems.

**Paso 2 — Instalar librerias requeridas:**

Desde `Herramientas > Administrar bibliotecas`, instala las siguientes librerias:

| Libreria | Autor |
|---|---|
| `RF24` | TMRh20 |
| `ezButton` | ArduinoGetStarted |
| `Adafruit SSD1306` | Adafruit |
| `Adafruit GFX Library` | Adafruit |

**Paso 3 — Seleccionar la placa correcta:**

Ve a `Herramientas > Placa` y selecciona **ESP32 Dev Module** (o la variante que corresponda a tu ESP32 especifico).

Configura los parametros:
- Upload Speed: `921600`
- CPU Frequency: `240MHz`
- Flash Frequency: `80MHz`
- Flash Size: `4MB`

**Paso 4 — Cargar el firmware:**

Abre el archivo `gadgets/BlueFly/BlueFly_Firmware.ino` en Arduino IDE. Conecta el ESP32 por USB, selecciona el puerto correcto en `Herramientas > Puerto` y haz clic en **Subir**.

Una vez completada la carga, el ESP32 reiniciara automaticamente y mostrara `Gadget listo. Esperando comando SWEEP_JAM...` en el monitor serie a 115200 baud, indicando que esta listo para operar.

---

## Estructura del Repositorio

```
DragonFly/
├── raspi.py                  # Script principal — Raspberry Pi Zero 2W
├── desktop.py                # Script principal — Desktop / Kali Linux
├── ducky_logic.py            # Motor de ejecucion de payloads HID
├── gadget_handler.py         # Controlador de gadgets externos (serie USB)
├── install.sh                # Instalador automatizado
│
├── payloads/                 # Payloads Rubber Ducky (.txt)
│   └── ejemplo_payload.txt
│
├── evil_portals/             # Portales cautivos para Evil Twin
│   ├── portal_1/
│   │   ├── index.html
│   │   └── post.php
│   └── portal_2/
│       ├── index.html
│       └── post.php
│
└── gadgets/
    └── BlueFly/
        └── BlueFly_Firmware.ino
```

---

## Aviso Legal

DragonFly es una herramienta de investigacion en ciberseguridad. Su uso esta destinado exclusivamente a:

- Entornos de laboratorio controlados.
- Auditorias de seguridad con autorizacion escrita del propietario de la red o sistema.
- Investigacion y educacion en el campo de la seguridad informatica.

El uso de estas herramientas contra redes, sistemas o dispositivos sin autorizacion expresa es ilegal en la mayoria de jurisdicciones y puede acarrear sanciones penales y civiles. El autor del proyecto no se hace responsable del uso indebido de este software. Al clonar, instalar o ejecutar cualquier componente de este repositorio, aceptas que lo haces bajo tu exclusiva responsabilidad y en cumplimiento de las leyes aplicables en tu pais.

---

## Licencia

```
MIT License

Copyright (c) 2024 whoamijas0n

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

<div align="center">

Construido con intencion — para quienes entienden que la seguridad se aprende atacando.

[github.com/whoamijas0n/DragonFly](https://github.com/whoamijas0n/DragonFly.git)

</div>
