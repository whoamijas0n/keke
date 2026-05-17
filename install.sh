#!/bin/bash

# ==============================================================================
# DRAGON FLY SYSTEM - AUTO INSTALLER
# ==============================================================================

# Colores
RED='\033[0;31m'
DARK_GRAY='\033[1;30m'
WHITE='\033[1;37m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Detectar usuario real (incluso si se ejecuta con sudo)
TARGET_USER=${SUDO_USER:-$(whoami)}
TARGET_HOME=$(getent passwd "$TARGET_USER" | cut -d: -f6)
PROJECT_DIR=$(pwd)

# Función para centrar texto de una sola línea en la terminal
print_center() {
    local text="$1"
    local color="$2"
    local term_width=$(tput cols 2>/dev/null || echo 80)
    local padding="$(printf '%0.1s' ' '{1..500})"
    local text_len=${#text}
    local pad_len=$(( (term_width - text_len) / 2 ))
    [[ $pad_len -lt 0 ]] && pad_len=0
    printf "${color}%*.*s%s${NC}\n" 0 "$pad_len" "$padding" "$text"
}

# Banner con Arte ASCII centrado dinámicamente
draw_banner() {
    clear
    local term_width=$(tput cols 2>/dev/null || echo 80)
    
    # La línea más larga de este ASCII art tiene 61 caracteres
    local max_len=61 
    local pad_len=$(( (term_width - max_len) / 2 ))
    [[ $pad_len -lt 0 ]] && pad_len=0
    
    # Crear el espacio de margen izquierdo
    local padding=$(printf '%*s' "$pad_len" "")

    echo -e "${RED}"
    # Leer el ASCII art línea por línea y agregarle el margen izquierdo
    while IFS= read -r line; do
        echo "${padding}${line}"
    done << 'EOF'


     ·▄▄▄▄  ▄▄▄   ▄▄▄·  ▄▄ •        ▐ ▄ ·▄▄▄▄▄▌   ▄· ▄▌
     ██▪ ██ ▀▄ █·▐█ ▀█ ▐█ ▀ ▪▪     •█▌▐█▐▄▄·██•  ▐█▪██▌
     ▐█· ▐█▌▐▀▀▄ ▄█▀▀█ ▄█ ▀█▄ ▄█▀▄ ▐█▐▐▌██▪ ██▪  ▐█▌▐█▪
     ██. ██ ▐█•█▌▐█ ▪▐▌▐█▄▪▐█▐█▌.▐▌██▐█▌██▌.▐█▌▐▌ ▐█▀·.
     ▀▀▀▀▀• .▀  ▀ ▀  ▀ ·▀▀▀▀  ▀█▄▀▪▀▀ █▪▀▀▀ .▀▀▀   ▀ • 

EOF
    echo -e "${NC}"
    
    print_center "=== INSTALADOR AUTOMATIZADO - RED TEAM TOOLBOX ===" "${WHITE}"
    print_center "Preparando entorno para automatizar tus auditorias" "${DARK_GRAY}"
    echo ""
}

# 1. Instalar Dependencias
instalar_dependencias() {
    print_center "[*] Actualizando repositorios e instalando dependencias base..." "${RED}"
    apt-get update -y
    
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        python3 python3-tk python3-serial \
        nmap macchanger aircrack-ng hostapd dnsmasq iptables \
        network-manager bluez rfkill lxterminal

    print_center "[+] Dependencias instaladas correctamente." "${GREEN}"
    sleep 2
}

# 2. Configurar USB Gadget (Rubber Ducky)
configurar_gadget() {
    print_center "[*] Creando script USB Gadget (/usr/local/bin/usb_gadget.sh)..." "${RED}"
    
    cat << 'EOF' > /usr/local/bin/usb_gadget.sh
#!/bin/bash
# Limpiar cualquier gadget anterior
if [ -d /sys/kernel/config/usb_gadget/g1 ]; then
    echo "" > /sys/kernel/config/usb_gadget/g1/UDC 2>/dev/null
    sleep 1
    rm -rf /sys/kernel/config/usb_gadget/g1
fi

# Cargar módulos (por si no estaban)
modprobe libcomposite
modprobe usb_f_hid

# Crear gadget
mkdir -p /sys/kernel/config/usb_gadget/g1
cd /sys/kernel/config/usb_gadget/g1

echo 0x1d6b > idVendor
echo 0x0104 > idProduct
echo 0x0100 > bcdDevice
echo 0x0200 > bcdUSB

mkdir -p strings/0x409
echo "1234567890" > strings/0x409/serialnumber
echo "Raspberry Pi" > strings/0x409/manufacturer
echo "Pi Zero HID Keyboard" > strings/0x409/product

mkdir -p configs/c.1/strings/0x409
echo "Teclado HID" > configs/c.1/strings/0x409/configuration
echo 500 > configs/c.1/MaxPower

mkdir -p functions/hid.usb0
echo 1 > functions/hid.usb0/protocol
echo 1 > functions/hid.usb0/subclass
echo 8 > functions/hid.usb0/report_length
printf "\x05\x01\x09\x06\xa1\x01\x05\x07\x19\xe0\x29\xe7\x15\x00\x25\x01\x75\x01\x95\x08\x81\x02\x95\x01\x75\x08\x81\x03\x95\x06\x75\x08\x15\x00\x25\x65\x05\x07\x19\x00\x29\x65\x81\x00\xc0" > functions/hid.usb0/report_desc

ln -s functions/hid.usb0 configs/c.1/

# Pequeña pausa para que el sistema USB esté listo
sleep 2

# Activar
UDC_DEV=$(ls /sys/class/udc | head -1)
echo "$UDC_DEV" > UDC
echo "Gadget HID activado en $UDC_DEV"
EOF

    chmod +x /usr/local/bin/usb_gadget.sh
    print_center "[+] Script USB Gadget configurado." "${GREEN}"
    sleep 2
}

# 3. Configurar Auto-Inicio y Permisos (Sudoers)
configurar_sistema() {
    print_center "[*] Configurando Auto-inicio en entorno gráfico..." "${RED}"
    
    mkdir -p "$TARGET_HOME/.config/autostart"
    
    cat << EOF > "$TARGET_HOME/.config/autostart/raspy.desktop"
[Desktop Entry]
Type=Application
Name=Raspy
Comment=Mi script DragonFly
Exec=lxterminal -e "bash -c 'cd $PROJECT_DIR && sudo /usr/bin/python3 $PROJECT_DIR/raspi.py'"
Terminal=false
X-GNOME-Autostart-enabled=true
EOF
    
    chown -R "$TARGET_USER:$TARGET_USER" "$TARGET_HOME/.config/autostart"

    print_center "[*] Otorgando permisos de ejecución NOPASSWD en sudoers..." "${RED}"
    echo "$TARGET_USER ALL=(ALL) NOPASSWD: /usr/bin/python3 $PROJECT_DIR/raspi.py" | sudo tee /etc/sudoers.d/010_dragonfly > /dev/null
    chmod 0440 /etc/sudoers.d/010_dragonfly

    print_center "[+] Sistema configurado correctamente." "${GREEN}"
    sleep 2
}

# Menú interactivo centrado
main_menu() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}Por favor, ejecuta este script como root (sudo ./install.sh)${NC}"
        exit 1
    fi

    while true; do
        draw_banner
        
        # Opciones centradas visualmente sumando márgenes
        local term_width=$(tput cols 2>/dev/null || echo 80)
        local menu_width=50
        local pad_len=$(( (term_width - menu_width) / 2 ))
        [[ $pad_len -lt 0 ]] && pad_len=0
        local padding=$(printf '%*s' "$pad_len" "")

        echo "${padding}1) Instalación Completa (Todo-en-Uno)"
        echo "${padding}2) Instalar Solo Dependencias (APT + Python)"
        echo "${padding}3) Configurar Solo USB Gadget"
        echo "${padding}4) Configurar Solo Auto-Inicio y Sudoers"
        echo "${padding}5) Salir"
        echo ""
        
        # El prompt lo dejamos normal para que el usuario escriba
        read -p "${padding}Selecciona una opción [1-5]: " opcion

        case $opcion in
            1)
                instalar_dependencias
                configurar_gadget
                configurar_sistema
                print_center "¡INSTALACIÓN COMPLETADA CON ÉXITO!" "${GREEN}"
                echo ""
                print_center "Se recomienda reiniciar la Raspberry Pi." "${WHITE}"
                read -p "Presiona ENTER para salir..."
                break
                ;;
            2)
                instalar_dependencias
                ;;
            3)
                configurar_gadget
                ;;
            4)
                configurar_sistema
                ;;
            5)
                echo ""
                print_center "Saliendo..." "${DARK_GRAY}"
                exit 0
                ;;
            *)
                echo ""
                print_center "Opción no válida." "${RED}"
                sleep 1
                ;;
        esac
    done
}

main_menu
