/**
 * DRAGON FLY - ESP32 BLE Gadget Firmware (v3.0 final + OLED 0.96")
 * 
 * ADVERTENCIA LEGAL: Solo para uso autorizado en auditorías con consentimiento.
 * 
 * Controla dos módulos nRF24L01+PA+LNA (HSPI y VSPI) para:
 *   - Escaneo BLE (sniffer de direcciones MAC)
 *   - Publicidad Bluejacking (envío de nombre personalizado)
 *   - Beacon Flooding (nombres aleatorios)
 *   - Jamming de portadora continua en un canal
 * 
 * Añadida pantalla OLED SSD1306 128x64 I2C para monitorización local.
 * Pines OLED: SDA=4, SCL=5 (evita conflicto con VSPI que usa 21 y 22)
 */

#include <SPI.h>
#include <RF24.h>
#include <BTLE.h>

// --- Librerías para pantalla OLED ---
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// -------------------------------------------------------------------
// Configuración de la pantalla OLED (pines libres: 4 y 5)
// -------------------------------------------------------------------
#define OLED_SDA      4      // Pin SDA del I2C
#define OLED_SCL      5      // Pin SCL del I2C
#define OLED_ADDR     0x3C   // Dirección I2C más común (verificar con escáner)
#define SCREEN_WIDTH  128
#define SCREEN_HEIGHT 64
#define OLED_RESET    -1     // Sin pin de reset (se comparte con el reset del ESP32)

// Objeto de la pantalla
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// Intervalo de actualización de pantalla (ms) – no bloqueante
const unsigned long DISPLAY_UPDATE_MS = 200;

// Variables globales para el display
String lastCommand = "";               // Último comando recibido (se muestra en pantalla)
int deviceCount[2] = {0, 0};          // Contador de dispositivos BLE encontrados en cada módulo
unsigned long lastDisplayUpdate = 0;  // Último momento en que se actualizó la pantalla

// -------------------------------------------------------------------
// Pinout exacto para ESP32 (HSPI y VSPI)
// -------------------------------------------------------------------
const int HSPI_SCK  = 14;
const int HSPI_MISO = 12;
const int HSPI_MOSI = 13;
const int HSPI_SS   = 15;
const int HSPI_CE   = 16;

const int VSPI_SCK  = 18;
const int VSPI_MISO = 19;
const int VSPI_MOSI = 23;
const int VSPI_SS   = 21;
const int VSPI_CE   = 22;

// Instancias de SPI y radios
SPIClass hspi(HSPI);
SPIClass vspi(VSPI);

RF24 radio0(HSPI_CE, HSPI_SS);
RF24 radio1(VSPI_CE, VSPI_SS);

BTLE btle0(&radio0);
BTLE btle1(&radio1);

// -------------------------------------------------------------------
// Estados de cada módulo
// -------------------------------------------------------------------
enum ModuleState {
  IDLE,
  SCANNING,
  ADVERTISING,
  FLOODING,
  JAMMING,
  SWEEP_JAMMING
};

struct ModuleInfo {
  ModuleState state;
  bool stopRequested;
  unsigned long startTime;       // tiempo de inicio de la operación
  unsigned long scanDuration;    // duración del escaneo en ms
  String advertiseMsg;           // mensaje para advertising
  int floodCount;                // total de beacons
  int floodInterval;             // intervalo entre beacons (ms)
  int floodCurrent;              // beacons enviados
  unsigned long lastBeaconTime;  // último instante de envío
  int jamChannel;                // canal de jamming
  unsigned long jamEndTime;      // momento de finalización del jam
  bool jammingActive;            // portadora activa (para jam)
};

ModuleInfo modules[2] = {
  { IDLE, false, 0, 0, "" },
  { IDLE, false, 0, 0, "" }
};

// -------------------------------------------------------------------
// Configuración para escaneo BLE (sniffer)
// -------------------------------------------------------------------
void configureRadioForSniffing(RF24 &radio) {
  radio.stopListening();
  radio.setAutoAck(false);
  radio.setCRCLength(RF24_CRC_DISABLED);
  radio.setDataRate(RF24_1MBPS);
  radio.setChannel(37);               // Canal de advertising BLE
  uint8_t addr[5] = {0x8E, 0x89, 0xBE, 0xD6, 0x02}; // dirección de broadcast
  radio.openReadingPipe(0, addr);
  radio.startListening();
}

bool sniffBLEPacket(RF24 &radio, uint8_t *buffer, uint8_t &len, int &rssi) {
  if (!radio.available()) return false;
  len = radio.getPayloadSize();
  radio.read(buffer, len);
  // Estimación simple de RSSI (RPD = Receive Power Detector)
  rssi = radio.testRPD() ? -40 : -80;
  return true;
}

bool isBLEAdvertising(uint8_t *buffer, uint8_t len) {
  if (len < 2) return false;
  uint8_t pduType = buffer[0] & 0x0F;
  return (pduType >= 0 && pduType <= 3);
}

void extractMAC(uint8_t *buffer, uint8_t len, uint8_t *mac) {
  // La MAC está en los bytes 2-7 del header de advertising BLE
  memcpy(mac, buffer + 2, 6);
}

// -------------------------------------------------------------------
// Prototipos
// -------------------------------------------------------------------
void processCommand(String cmd);
void initRadio(RF24 &radio, SPIClass &spi, uint8_t sck, uint8_t miso, uint8_t mosi);
void handleModule(int index, BTLE &btle, RF24 &radio, ModuleInfo &mod);
void doScan(int index, RF24 &radio, ModuleInfo &mod);
void doAdvertise(int index, BTLE &btle, ModuleInfo &mod);
void doFlood(int index, BTLE &btle, ModuleInfo &mod);
void doJam(int index, RF24 &radio, ModuleInfo &mod);
void stopModule(int index, BTLE &btle, RF24 &radio, ModuleInfo &mod);
void updateDisplay();  // Actualiza la pantalla OLED

// -------------------------------------------------------------------
// SETUP
// -------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(100);

  // Inicializar pantalla OLED (pines SDA=4, SCL=5)
  Wire.begin(OLED_SDA, OLED_SCL);
  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    Serial.println("ERROR: OLED no encontrada");
    // Se continúa sin pantalla; no detiene el funcionamiento
  } else {
    // Mostrar pantalla de inicio
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(10, 20);
    display.println("DRAGON FLY");
    display.setCursor(10, 40);
    display.println("GADGET OLED");
    display.display();
    delay(1500);  // Permite leer el mensaje de bienvenida
    display.clearDisplay();
    display.display();
  }

  Serial.println("DRAGON FLY GADGET READY");

  initRadio(radio0, hspi, HSPI_SCK, HSPI_MISO, HSPI_MOSI);
  initRadio(radio1, vspi, VSPI_SCK, VSPI_MISO, VSPI_MOSI);

  // Inicializar BTLE con un nombre por defecto (necesario para begin)
  btle0.begin("GADGET0");
  btle1.begin("GADGET1");

  Serial.println("MODULOS LISTOS");
}

void initRadio(RF24 &radio, SPIClass &spi, uint8_t sck, uint8_t miso, uint8_t mosi) {
  spi.begin(sck, miso, mosi, -1); // SS se maneja externamente
  if (!radio.begin(&spi)) {
    Serial.println("ERROR:INIT_RADIO");
    while(1); // Detener si falla la inicialización
  }
  radio.setAutoAck(false);
  radio.setDataRate(RF24_1MBPS);
  radio.setCRCLength(RF24_CRC_DISABLED);
  radio.setChannel(37);
  radio.powerUp();
}

// -------------------------------------------------------------------
// LOOP PRINCIPAL
// -------------------------------------------------------------------
void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.length() > 0) {
      processCommand(cmd);
    }
  }

  handleModule(0, btle0, radio0, modules[0]);
  handleModule(1, btle1, radio1, modules[1]);

  // Actualizar pantalla OLED periódicamente (no bloqueante)
  updateDisplay();
}

// -------------------------------------------------------------------
// Procesador de comandos
// -------------------------------------------------------------------
void processCommand(String cmd) {
  // Guardar el comando original para mostrar en pantalla (máx 20 caracteres)
  lastCommand = cmd.length() > 20 ? cmd.substring(0, 20) : cmd;

  cmd.toUpperCase();
  int firstSpace = cmd.indexOf(' ');
  String op = (firstSpace == -1) ? cmd : cmd.substring(0, firstSpace);
  
  if (op == "SCAN") {
    int m = cmd.substring(5, cmd.indexOf(' ', 5)).toInt();
    int dur = cmd.substring(cmd.lastIndexOf(' ') + 1).toInt();
    if (m >= 0 && m <= 1 && dur > 0) {
      if (modules[m].state == IDLE) {
        modules[m].state = SCANNING;
        modules[m].startTime = millis();
        modules[m].scanDuration = dur * 1000UL;
        modules[m].stopRequested = false;
        configureRadioForSniffing(m == 0 ? radio0 : radio1);
        deviceCount[m] = 0;   // Reiniciar contador para este módulo
        Serial.println("SCANNING_STARTED");
      } else {
        Serial.println("ERROR:MODULE_BUSY");
      }
    } else {
      Serial.println("ERROR:INVALID_PARAMS");
    }
  } else if (op == "ADVERTISE") {
    int m = cmd.substring(9, cmd.indexOf(' ', 9)).toInt();
    String msg = cmd.substring(cmd.indexOf(' ', 9) + 1);
    msg.trim();
    if (m >= 0 && m <= 1 && msg.length() > 0) {
      if (modules[m].state == IDLE) {
        modules[m].state = ADVERTISING;
        modules[m].advertiseMsg = msg;
        modules[m].stopRequested = false;
        Serial.println("ADVERTISING_STARTED");
      } else {
        Serial.println("ERROR:MODULE_BUSY");
      }
    } else {
      Serial.println("ERROR:INVALID_PARAMS");
    }
  } else if (op == "BEACON_FLOOD") {
    int m = cmd.substring(12, cmd.indexOf(' ', 12)).toInt();
    int sp2 = cmd.lastIndexOf(' ');
    int sp1 = cmd.lastIndexOf(' ', sp2 - 1);
    int count = cmd.substring(sp1 + 1, sp2).toInt();
    int interval = cmd.substring(sp2 + 1).toInt();
    if (m >= 0 && m <= 1 && count > 0 && interval > 0) {
      if (modules[m].state == IDLE) {
        modules[m].state = FLOODING;
        modules[m].floodCount = count;
        modules[m].floodInterval = interval;
        modules[m].floodCurrent = 0;
        modules[m].lastBeaconTime = millis();
        modules[m].stopRequested = false;
        Serial.println("FLOODING_STARTED");
      } else {
        Serial.println("ERROR:MODULE_BUSY");
      }
    } else {
      Serial.println("ERROR:INVALID_PARAMS");
    }
  } else if (op == "JAM") {
    int m = cmd.substring(3, cmd.indexOf(' ', 3)).toInt();
    int ch = cmd.substring(cmd.indexOf(' ', 3) + 1, cmd.lastIndexOf(' ')).toInt();
    int dur = cmd.substring(cmd.lastIndexOf(' ') + 1).toInt();
    if (m >= 0 && m <= 1 && ch >= 0 && ch <= 78 && dur > 0) {
      if (modules[m].state == IDLE) {
        modules[m].state = JAMMING;
        modules[m].jamChannel = ch;
        modules[m].jamEndTime = millis() + dur * 1000UL;
        modules[m].stopRequested = false;
        modules[m].jammingActive = false; // se activará en doJam
        Serial.println("JAMMING_STARTED");
      } else {
        Serial.println("ERROR:MODULE_BUSY");
      }
    } else {
      Serial.println("ERROR:INVALID_PARAMS");
    }



  else if (op == "SWEEP_JAM") {
    // Formato: SWEEP_JAM <module> <duration>
    int m = cmd.substring(9, cmd.indexOf(' ', 9)).toInt();
    int dur = cmd.substring(cmd.lastIndexOf(' ') + 1).toInt();
    if (m >= 0 && m <= 1 && dur > 0) {
      if (modules[m].state == IDLE) {
        modules[m].state = SWEEP_JAMMING;
        modules[m].jamChannel = 0;        // canal inicial
        modules[m].jamEndTime = millis() + dur * 1000UL;
        modules[m].stopRequested = false;
        modules[m].jammingActive = false;
        Serial.println("SWEEP_JAMMING_STARTED");
      } else {
        Serial.println("ERROR:MODULE_BUSY");
      }
    } else {
      Serial.println("ERROR:INVALID_PARAMS");
    }
}

  } else if (op == "STOP") {
    int m = cmd.substring(4).toInt();

    if (m >= 0 && m <= 1) {
      modules[m].stopRequested = true;
      Serial.println("STOPPING");
    } else {
      Serial.println("ERROR:INVALID_MODULE");
    }
  } else if (cmd == "STATUS") {
    Serial.print("STATUS:OK,MOD0=");
    Serial.print(modules[0].state == IDLE ? "IDLE" : 
                 modules[0].state == SCANNING ? "SCANNING" : 
                 modules[0].state == ADVERTISING ? "ADVERTISING" : 
                 modules[0].state == FLOODING ? "FLOODING" : "JAMMING");
    Serial.print(",MOD1=");
    Serial.println(modules[1].state == IDLE ? "IDLE" : 
                   modules[1].state == SCANNING ? "SCANNING" : 
                   modules[1].state == ADVERTISING ? "ADVERTISING" : 
                   modules[1].state == FLOODING ? "FLOODING" : "JAMMING");
  } else {
    Serial.println("ERROR:UNKNOWN_COMMAND");
  }
}

// -------------------------------------------------------------------
// Manejo de módulos (no bloqueante)
// -------------------------------------------------------------------
void handleModule(int index, BTLE &btle, RF24 &radio, ModuleInfo &mod) {
  if (mod.stopRequested) {
    stopModule(index, btle, radio, mod);
    mod.stopRequested = false;
  }
  switch (mod.state) {
    case SCANNING:   doScan(index, radio, mod); break;
    case ADVERTISING: doAdvertise(index, btle, mod); break;
    case FLOODING:   doFlood(index, btle, mod); break;
    case JAMMING:    doJam(index, radio, mod); break;
    case SWEEP_JAMMING: doSweepJam(index, radio, mod); break;
    default: break;
  }
}

void doScan(int index, RF24 &radio, ModuleInfo &mod) {
  uint8_t buf[32];
  uint8_t len;
  int rssi;
  if (sniffBLEPacket(radio, buf, len, rssi)) {
    if (isBLEAdvertising(buf, len)) {
      uint8_t mac[6];
      extractMAC(buf, len, mac);
      char macStr[18];
      sprintf(macStr, "%02X:%02X:%02X:%02X:%02X:%02X", 
              mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
      Serial.print("DEVICE:");
      Serial.print(macStr);
      Serial.print(",");
      Serial.print(rssi);
      Serial.println(",Unknown");
      // Incrementar contador de dispositivos para este módulo
      deviceCount[index]++;
    }
  }
  if (millis() - mod.startTime >= mod.scanDuration) {
    Serial.println("SCAN_DONE");
    mod.state = IDLE;
    radio.stopListening();
    // Opcional: dejar el contador como está o resetearlo
    // deviceCount[index] = 0;
  }
}

// Publicidad: envía el mensaje como Nombre Completo (0x09)
void doAdvertise(int index, BTLE &btle, ModuleInfo &mod) {
  if (mod.advertiseMsg.length() == 0) return;
  const char* msg = mod.advertiseMsg.c_str();
  // data_type 0x09 = Complete Local Name
  btle.advertise(0x09, (void*)msg, strlen(msg));
  delay(100); // Pequeña pausa para no saturar el loop
}

void doFlood(int index, BTLE &btle, ModuleInfo &mod) {
  if (mod.floodCurrent >= mod.floodCount) {
    Serial.println("FLOOD_DONE");
    mod.state = IDLE;
    return;
  }
  unsigned long now = millis();
  if (now - mod.lastBeaconTime >= mod.floodInterval) {
    const char* ssids[] = {"FreeWiFi","Starbucks","AirportWifi","Corporate","Guest","HomeNetwork","PublicWiFi","Office"};
    int idx = random(0, 8);
    String randomName = String(ssids[idx]) + String(random(100, 999));
    btle.advertise(0x09, (void*)randomName.c_str(), randomName.length());
    mod.floodCurrent++;
    mod.lastBeaconTime = now;
  }
}

void doJam(int index, RF24 &radio, ModuleInfo &mod) {
  if (millis() >= mod.jamEndTime) {
    if (mod.jammingActive) {
      radio.stopConstCarrier();
      mod.jammingActive = false;
    }
    radio.powerDown();
    radio.powerUp(); // Reiniciar radio en estado normal
    Serial.println("JAM_DONE");
    mod.state = IDLE;
    return;
  }
  // Iniciar portadora si no está ya activa
  if (!mod.jammingActive) {
    radio.setChannel(mod.jamChannel);
    radio.startConstCarrier(RF24_PA_MAX, mod.jamChannel);
    mod.jammingActive = true;
  }
}

void stopModule(int index, BTLE &btle, RF24 &radio, ModuleInfo &mod) {
  switch (mod.state) {
    case SCANNING:
      radio.stopListening();
      // Limpiar contador al detener el escaneo
      deviceCount[index] = 0;
      break;
    case ADVERTISING:
    case FLOODING:
      // BTLE no tiene stop explícito; simplemente se dejará de llamar a advertise
      break;
    case JAMMING:
      if (mod.jammingActive) {
        radio.stopConstCarrier();
        mod.jammingActive = false;
      }
      radio.powerDown();
      radio.powerUp();
      break;
    default: break;
  }
  case SWEEP_JAMMING:
  if (mod.jammingActive) {
    radio.stopConstCarrier();
    mod.jammingActive = false;
  }
  radio.powerDown();
  radio.powerUp();
  break;
  mod.state = IDLE;
  Serial.println("STOPPED");
}

void doSweepJam(int index, RF24 &radio, ModuleInfo &mod) {
  if (millis() >= mod.jamEndTime) {
    // Tiempo terminado → apagar portadora y limpiar
    if (mod.jammingActive) {
      radio.stopConstCarrier();
      mod.jammingActive = false;
    }
    radio.powerDown();
    radio.powerUp();
    Serial.println("SWEEP_JAM_DONE");
    mod.state = IDLE;
    return;
  }

  // Si no está activa la portadora, iniciarla en el canal 0
  if (!mod.jammingActive) {
    radio.setChannel(0);
    radio.startConstCarrier(RF24_PA_MAX, 0);   // PA máxima y canal inicial
    mod.jammingActive = true;
  }

  // Barrido rápido: cambiar canal cada pocos microsegundos
  // Escribimos directamente el registro RF_CH (0x2B) en el nRF24L01
  const int sweep_delay_us = 30;  // microsegundos por canal (ajustable)
  for (int ch = 0; ch <= 76; ch++) {
    // Salir si se solicitó parada o pasó el tiempo
    if (mod.stopRequested || millis() >= mod.jamEndTime) break;

    // Escribir canal en registro RF_CH
    // La función write_register de RF24 no es accesible desde aquí,
    // pero podemos enviar el comando SPI manualmente.
    // Usamos la biblioteca SPI para escribir 0x20 | 0x2B → write register 0x2B
    uint8_t reg = 0x2B;          // RF_CH
    uint8_t val = ch & 0x7F;     // rango 0..76
    // Secuencia SPI: bajar CS, enviar W_REGISTER | reg, enviar valor, subir CS
    digitalWrite(radio.cePin(), LOW); // asegurar que CS esté bajo (el SS es controlado por RF24)
    // En realidad el SS lo maneja la librería; mejor usamos la misma clase SPI.
    // Podemos hacer: radio.setChannel(ch) es más fácil, aunque ligeramente más lento.
    // Para este prototipo, usemos setChannel; si necesitas más velocidad luego optimizas con SPI directo.
    // Opto por setChannel que ya es bastante rápido (~30 µs).
    radio.setChannel(ch);
    delayMicroseconds(sweep_delay_us);
  }
}

// -------------------------------------------------------------------
// ACTUALIZACIÓN DE LA PANTALLA OLED (no bloqueante)
// -------------------------------------------------------------------
void updateDisplay() {
  // No hacer nada si el intervalo de refresco no ha pasado
  if (millis() - lastDisplayUpdate < DISPLAY_UPDATE_MS) {
    return;
  }
  lastDisplayUpdate = millis();

  // Si la pantalla no se pudo inicializar, salir sin errores
  if (!display.getBuffer()) return;

  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);

  // Título
  display.setCursor(20, 0);
  display.println("DRAGON FLY GADGET");

  // Función auxiliar para convertir estado a texto
  auto stateToStr = [](ModuleState s) -> const char* {
    switch (s) {
      case IDLE:         return "IDLE";
      case SCANNING:     return "SCANNING";
      case ADVERTISING:  return "ADVERTISING";
      case FLOODING:     return "FLOODING";
      case JAMMING:      return "JAMMING";
      case SWEEP_JAMMING: return "SWEEP_JAM";
      default:           return "???";
    }
  };

  // Estado módulo 0 (HSPI)
  display.setCursor(0, 16);
  display.print("Mod0: ");
  display.println(stateToStr(modules[0].state));

  // Si está escaneando, añadir contador
  if (modules[0].state == SCANNING) {
    display.setCursor(60, 16);
    display.print("Cnt:");
    display.print(deviceCount[0]);
  }

  // Estado módulo 1 (VSPI)
  display.setCursor(0, 28);
  display.print("Mod1: ");
  display.println(stateToStr(modules[1].state));
  if (modules[1].state == SCANNING) {
    display.setCursor(60, 28);
    display.print("Cnt:");
    display.print(deviceCount[1]);
  }

  // Último comando
  display.setCursor(0, 44);
  display.print("Cmd: ");
  display.println(lastCommand);

  // Información adicional: canal de jamming si alguno está activo
  if (modules[0].state == JAMMING) {
    display.setCursor(0, 56);
    display.print("J0 CH:");
    display.print(modules[0].jamChannel);
  } else if (modules[1].state == JAMMING) {
    display.setCursor(0, 56);
    display.print("J1 CH:");
    display.print(modules[1].jamChannel);
  }
  
  else if (modules[0].state == SWEEP_JAMMING || modules[1].state == SWEEP_JAMMING) {
    int idx = (modules[0].state == SWEEP_JAMMING) ? 0 : 1;
    display.setCursor(0, 56);
    display.print("SWEEP JAM");
}
  display.display();
}