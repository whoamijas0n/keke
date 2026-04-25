/**
 * DRAGON FLY - ESP32 BLE Gadget Firmware (v3.1 + Sweep Jammer)
 *
 * ADVERTENCIA LEGAL: Solo para uso autorizado en auditorías con consentimiento.
 *
 * Controla dos módulos nRF24L01+PA+LNA (HSPI y VSPI) para:
 *   - Escaneo BLE (sniffer de direcciones MAC)
 *   - Publicidad Bluejacking (envío de nombre personalizado)
 *   - Beacon Flooding (nombres aleatorios)
 *   - Jamming de portadora continua en un canal
 *   - Barrido de frecuencia (Sweep Jammer) 0-76
 *
 * Pantalla OLED SSD1306 128x64 I2C (SDA=4, SCL=5)
 */

#include <SPI.h>
#include <RF24.h>
#include <BTLE.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// -------------------------------------------------------------------
// OLED
// -------------------------------------------------------------------
#define OLED_SDA      4
#define OLED_SCL      5
#define OLED_ADDR     0x3C
#define SCREEN_WIDTH  128
#define SCREEN_HEIGHT 64
#define OLED_RESET    -1

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

const unsigned long DISPLAY_UPDATE_MS = 200;

String lastCommand = "";
int deviceCount[2] = {0, 0};
unsigned long lastDisplayUpdate = 0;

// -------------------------------------------------------------------
// Pinout HSPI y VSPI
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

SPIClass hspi(HSPI);
SPIClass vspi(VSPI);

RF24 radio0(HSPI_CE, HSPI_SS);
RF24 radio1(VSPI_CE, VSPI_SS);

BTLE btle0(&radio0);
BTLE btle1(&radio1);

// -------------------------------------------------------------------
// Estados de cada módulo (añadido SWEEP_JAMMING)
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
  unsigned long startTime;
  unsigned long scanDuration;
  String advertiseMsg;
  int floodCount;
  int floodInterval;
  int floodCurrent;
  unsigned long lastBeaconTime;
  int jamChannel;
  unsigned long jamEndTime;
  bool jammingActive;
};

ModuleInfo modules[2] = {
  { IDLE, false, 0, 0, "" },
  { IDLE, false, 0, 0, "" }
};

// -------------------------------------------------------------------
// Sniffer BLE
// -------------------------------------------------------------------
void configureRadioForSniffing(RF24 &radio) {
  radio.stopListening();
  radio.setAutoAck(false);
  radio.setCRCLength(RF24_CRC_DISABLED);
  radio.setDataRate(RF24_1MBPS);
  radio.setChannel(37);
  uint8_t addr[5] = {0x8E, 0x89, 0xBE, 0xD6, 0x02};
  radio.openReadingPipe(0, addr);
  radio.startListening();
}

bool sniffBLEPacket(RF24 &radio, uint8_t *buffer, uint8_t &len, int &rssi) {
  if (!radio.available()) return false;
  len = radio.getPayloadSize();
  radio.read(buffer, len);
  rssi = radio.testRPD() ? -40 : -80;
  return true;
}

bool isBLEAdvertising(uint8_t *buffer, uint8_t len) {
  if (len < 2) return false;
  uint8_t pduType = buffer[0] & 0x0F;
  return (pduType >= 0 && pduType <= 3);
}

void extractMAC(uint8_t *buffer, uint8_t len, uint8_t *mac) {
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
void doSweepJam(int index, RF24 &radio, ModuleInfo &mod);
void stopModule(int index, BTLE &btle, RF24 &radio, ModuleInfo &mod);
void updateDisplay();

// -------------------------------------------------------------------
// SETUP
// -------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(100);

  Wire.begin(OLED_SDA, OLED_SCL);
  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    Serial.println("ERROR: OLED no encontrada");
  } else {
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(10, 20);
    display.println("DRAGON FLY");
    display.setCursor(10, 40);
    display.println("GADGET OLED");
    display.display();
    delay(1500);
    display.clearDisplay();
    display.display();
  }

  Serial.println("DRAGON FLY GADGET READY");

  initRadio(radio0, hspi, HSPI_SCK, HSPI_MISO, HSPI_MOSI);
  initRadio(radio1, vspi, VSPI_SCK, VSPI_MISO, VSPI_MOSI);

  btle0.begin("GADGET0");
  btle1.begin("GADGET1");

  Serial.println("MODULOS LISTOS");
}

void initRadio(RF24 &radio, SPIClass &spi, uint8_t sck, uint8_t miso, uint8_t mosi) {
  spi.begin(sck, miso, mosi, -1);
  if (!radio.begin(&spi)) {
    Serial.println("ERROR:INIT_RADIO");
    while(1);
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

  updateDisplay();
}

// -------------------------------------------------------------------
// Procesador de comandos (añadido SWEEP_JAM)
// -------------------------------------------------------------------
void processCommand(String cmd) {
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
        deviceCount[m] = 0;
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
        modules[m].jammingActive = false;
        Serial.println("JAMMING_STARTED");
      } else {
        Serial.println("ERROR:MODULE_BUSY");
      }
    } else {
      Serial.println("ERROR:INVALID_PARAMS");
    }
  } else if (op == "SWEEP_JAM") {
    int m = cmd.substring(9, cmd.indexOf(' ', 9)).toInt();
    int dur = cmd.substring(cmd.lastIndexOf(' ') + 1).toInt();
    if (m >= 0 && m <= 1 && dur > 0) {
      if (modules[m].state == IDLE) {
        modules[m].state = SWEEP_JAMMING;
        modules[m].jamChannel = 0;
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
                 modules[0].state == FLOODING ? "FLOODING" :
                 modules[0].state == JAMMING ? "JAMMING" : "SWEEP_JAM");
    Serial.print(",MOD1=");
    Serial.println(modules[1].state == IDLE ? "IDLE" :
                   modules[1].state == SCANNING ? "SCANNING" :
                   modules[1].state == ADVERTISING ? "ADVERTISING" :
                   modules[1].state == FLOODING ? "FLOODING" :
                   modules[1].state == JAMMING ? "JAMMING" : "SWEEP_JAM");
  } else {
    Serial.println("ERROR:UNKNOWN_COMMAND");
  }
}

// -------------------------------------------------------------------
// Manejo de módulos (añadido caso SWEEP_JAMMING)
// -------------------------------------------------------------------
void handleModule(int index, BTLE &btle, RF24 &radio, ModuleInfo &mod) {
  if (mod.stopRequested) {
    stopModule(index, btle, radio, mod);
    mod.stopRequested = false;
  }
  switch (mod.state) {
    case SCANNING:    doScan(index, radio, mod); break;
    case ADVERTISING: doAdvertise(index, btle, mod); break;
    case FLOODING:    doFlood(index, btle, mod); break;
    case JAMMING:     doJam(index, radio, mod); break;
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
      deviceCount[index]++;
    }
  }
  if (millis() - mod.startTime >= mod.scanDuration) {
    Serial.println("SCAN_DONE");
    mod.state = IDLE;
    radio.stopListening();
  }
}

void doAdvertise(int index, BTLE &btle, ModuleInfo &mod) {
  if (mod.advertiseMsg.length() == 0) return;
  const char* msg = mod.advertiseMsg.c_str();
  btle.advertise(0x09, (void*)msg, strlen(msg));
  delay(100);
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
    radio.powerUp();
    Serial.println("JAM_DONE");
    mod.state = IDLE;
    return;
  }
  if (!mod.jammingActive) {
    radio.setChannel(mod.jamChannel);
    radio.startConstCarrier(RF24_PA_MAX, mod.jamChannel);
    mod.jammingActive = true;
  }
}

// -------------------- NUEVA FUNCIÓN DE BARRIDO --------------------
void doSweepJam(int index, RF24 &radio, ModuleInfo &mod) {
  if (millis() >= mod.jamEndTime) {
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

  // Iniciar portadora en canal 0 si aún no está activa
  if (!mod.jammingActive) {
    radio.setChannel(0);
    radio.startConstCarrier(RF24_PA_MAX, 0);
    mod.jammingActive = true;
  }

  // Barrido rápido por canales 0-76
  for (int ch = 0; ch <= 76; ch++) {
    if (mod.stopRequested || millis() >= mod.jamEndTime) break;
    radio.setChannel(ch);
    delayMicroseconds(60);  // 60 µs por canal, ciclo total ~4.6ms
  }
}

void stopModule(int index, BTLE &btle, RF24 &radio, ModuleInfo &mod) {
  switch (mod.state) {
    case SCANNING:
      radio.stopListening();
      deviceCount[index] = 0;
      break;
    case ADVERTISING:
    case FLOODING:
      break;
    case JAMMING:
      if (mod.jammingActive) {
        radio.stopConstCarrier();
        mod.jammingActive = false;
      }
      radio.powerDown();
      radio.powerUp();
      break;
    case SWEEP_JAMMING:
      if (mod.jammingActive) {
        radio.stopConstCarrier();
        mod.jammingActive = false;
      }
      radio.powerDown();
      radio.powerUp();
      break;
    default: break;
  }
  mod.state = IDLE;
  Serial.println("STOPPED");
}

// -------------------------------------------------------------------
// Pantalla OLED (añadido SWEEP_JAM)
// -------------------------------------------------------------------
void updateDisplay() {
  if (millis() - lastDisplayUpdate < DISPLAY_UPDATE_MS) return;
  lastDisplayUpdate = millis();

  if (!display.getBuffer()) return;

  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);

  display.setCursor(20, 0);
  display.println("DRAGON FLY GADGET");

  auto stateToStr = [](ModuleState s) -> const char* {
    switch (s) {
      case IDLE:         return "IDLE";
      case SCANNING:     return "SCANNING";
      case ADVERTISING:  return "ADVERTISING";
      case FLOODING:     return "FLOODING";
      case JAMMING:      return "JAMMING";
      case SWEEP_JAMMING:return "SWEEP_JAM";
      default:           return "???";
    }
  };

  display.setCursor(0, 16);
  display.print("Mod0: ");
  display.println(stateToStr(modules[0].state));
  if (modules[0].state == SCANNING) {
    display.setCursor(60, 16);
    display.print("Cnt:");
    display.print(deviceCount[0]);
  }

  display.setCursor(0, 28);
  display.print("Mod1: ");
  display.println(stateToStr(modules[1].state));
  if (modules[1].state == SCANNING) {
    display.setCursor(60, 28);
    display.print("Cnt:");
    display.print(deviceCount[1]);
  }

  display.setCursor(0, 44);
  display.print("Cmd: ");
  display.println(lastCommand);

  if (modules[0].state == JAMMING) {
    display.setCursor(0, 56);
    display.print("J0 CH:");
    display.print(modules[0].jamChannel);
  } else if (modules[1].state == JAMMING) {
    display.setCursor(0, 56);
    display.print("J1 CH:");
    display.print(modules[1].jamChannel);
  } else if (modules[0].state == SWEEP_JAMMING || modules[1].state == SWEEP_JAMMING) {
    display.setCursor(0, 56);
    display.print("SWEEP JAMMING");
  }

  display.display();
}