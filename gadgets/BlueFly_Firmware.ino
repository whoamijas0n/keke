#include "RF24.h"
#include <SPI.h>
#include <ezButton.h>
#include "esp_bt.h"
#include "esp_wifi.h"
#include "esp_task_wdt.h"
// ── OLED ─────────────────────────────────────────────────
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#define SCREEN_WIDTH  128
#define SCREEN_HEIGHT  64
#define OLED_ADDR      0x3C
#define SDA_PIN        4
#define SCL_PIN        5
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);
// ─────────────────────────────────────────────────────────

SPIClass *sp = nullptr;   // VSPI → Core 0
SPIClass *hp = nullptr;   // HSPI → Core 1

RF24 radio (22, 21, 16000000);   // VSPI  — Core 0
RF24 radio1(16, 15, 16000000);   // HSPI  — Core 1

// ── Estado de barrido — VSPI (Core 0) ────────────────────
static volatile byte ch0   = 45;
static volatile byte flag0 = 0;

// ── Estado de barrido — HSPI (Core 1) ────────────────────
static byte ch1   = 60;
static byte flag1 = 0;

// ── Control ───────────────────────────────────────────────
ezButton toggleSwitch(33);

volatile bool jamming_enabled = false; // leído por ambos cores
unsigned long stop_time       = 0;
bool          has_duration    = false;
String        serial_buffer   = "";

TaskHandle_t jammingTaskHandle = NULL;

// ── OLED ──────────────────────────────────────────────────
static bool          oled_blink       = false;
static unsigned long oled_last_blink  = 0;
static unsigned long oled_last_update = 0;


// ═════════════════════════════════════════════════════════
//  OLED
// ═════════════════════════════════════════════════════════
void drawBTIcon(int cx, int cy, int h, int w) {
  int h3 = h / 3;
  display.drawLine(cx,     cy - h,  cx,     cy + h,   WHITE);
  display.drawLine(cx + 1, cy - h,  cx + 1, cy + h,   WHITE);
  display.drawLine(cx,     cy - h,  cx + w, cy - h3,  WHITE);
  display.drawLine(cx + w, cy - h3, cx,     cy,        WHITE);
  display.drawLine(cx,     cy,      cx + w, cy + h3,  WHITE);
  display.drawLine(cx + w, cy + h3, cx,     cy + h,   WHITE);
}

void updateOLED() {
  if (millis() - oled_last_blink > 500) {
    oled_blink = !oled_blink;
    oled_last_blink = millis();
  }
  display.clearDisplay();
  display.drawRoundRect(0, 0, 128, 64, 4, WHITE);
  display.drawCircle(24, 32, 21, WHITE);
  drawBTIcon(24, 32, 15, 10);
  display.drawLine(49, 4, 49, 59, WHITE);
  display.setTextSize(2); display.setTextColor(WHITE);
  display.setCursor(55, 5);  display.print("Blue");
  display.setCursor(55, 22); display.print("-Fly");
  display.drawLine(52, 41, 124, 41, WHITE);
  display.setTextSize(1); display.setTextColor(WHITE);
  if (jamming_enabled) {
    if (oled_blink) display.fillCircle(57, 53, 3, WHITE);
    else            display.drawCircle(57, 53, 3, WHITE);
    display.setCursor(64, 49); display.print("Iniciado");
  } else {
    display.drawCircle(57, 53, 3, WHITE);
    display.setCursor(64, 49); display.print("Detenido");
  }
  display.display();
}


// ═════════════════════════════════════════════════════════
//  CONFIGURACIÓN DE RADIO
// ═════════════════════════════════════════════════════════
void configureRadio(RF24 &r) {
  r.setAutoAck(false);
  r.stopListening();
  r.setRetries(0, 0);
  r.setPayloadSize(5);     
  r.setAddressWidth(3);         
  r.setPALevel(RF24_PA_MAX, true);
  r.setDataRate(RF24_2MBPS);
  r.setCRCLength(RF24_CRC_DISABLED);
}

bool reinitRadios() {
  if (!radio.begin(sp)) {
    Serial.println("ERROR: VSPI no inició");
    return false;
  }
  if (!radio1.begin(hp)) {
    Serial.println("ERROR: HSPI no inició");
    return false;
  }
  configureRadio(radio);
  configureRadio(radio1);
  return true;
}


// ═════════════════════════════════════════════════════════
//  FUNCIONES DE JAMMING — VSPI  (ejecutadas en Core 0)
// ═════════════════════════════════════════════════════════
inline void vspi_sweep() {
  if (flag0 == 0) { ch0 += 2; } else { ch0 -= 2; }
  if ((ch0 > 79) && (flag0 == 0)) flag0 = 1;
  else if ((ch0 < 2) && (flag0 == 1)) flag0 = 0;
  radio.setChannel(ch0);
}

inline void vspi_random() {
  for (byte j = 0; j < 15; j++) radio.setChannel(j);
}

// ═════════════════════════════════════════════════════════
//  FUNCIONES DE JAMMING — HSPI  (ejecutadas en Core 1)
//  Barrido complementario con paso +3 para cubrir la
//  banda alta mientras VSPI cubre la baja.
// ═════════════════════════════════════════════════════════
inline void hspi_sweep() {
  if (flag1 == 0) { ch1 += 3; } else { ch1 -= 3; }
  if ((ch1 > 79) && (flag1 == 0)) flag1 = 1;
  else if ((ch1 < 2) && (flag1 == 1)) flag1 = 0;
  radio1.setChannel(ch1);
}

inline void hspi_random() {
  for (byte j = 0; j < 15; j++) radio1.setChannel(j + 40);
}


// ═════════════════════════════════════════════════════════
//  CORE 0 — TAREA EXCLUSIVA DE JAMMING
// ═════════════════════════════════════════════════════════
void jammingCore0(void *param) {
  uint32_t yieldCtr = 0;
  while (true) {
    if (jamming_enabled) {
      if (toggleSwitch.getState() == HIGH) vspi_sweep();
      else                                 vspi_random();

      if (++yieldCtr >= 5000) {
        yieldCtr = 0;
        vTaskDelay(1);  // 1 tick ≈ 1ms → el Idle Task corre y alimenta el WDT
      }
    } else {
      vTaskDelay(pdMS_TO_TICKS(5));
    }
  }
}


// ═════════════════════════════════════════════════════════
//  START / STOP
// ═════════════════════════════════════════════════════════
void start_jamming() {
  if (jamming_enabled) return;

  // reinit completo antes de cada inicio
  if (!reinitRadios()) return;

  // reset canales
  ch0 = 45; flag0 = 0;
  ch1 = 60; flag1 = 0;

  // startConstCarrier() UNA sola vez por radio.
  radio.startConstCarrier(RF24_PA_MAX, ch0);
  radio1.startConstCarrier(RF24_PA_MAX, ch1);

  jamming_enabled = true;   // Core 0 arranca en su próxima iteración
  Serial.println("JAMMING_STARTED");
}

void stop_jamming() {
  if (!jamming_enabled) return;

  jamming_enabled = false;
  // Dar tiempo a Core 0 para salir de su iteración actual.
  // La iteración más larga (vspi_random) toma ~150 µs.
  // 20 ms es más que suficiente.
  delay(20);

  radio.stopConstCarrier();   // CE=LOW + powerDown + limpia CONT_WAVE/PLL_LOCK
  radio1.stopConstCarrier();
  has_duration = false;
  Serial.println("STOPPED");
}

// ═════════════════════════════════════════════════════════
//  PROCESADO DE COMANDOS SERIE
// ═════════════════════════════════════════════════════════
void process_serial_command(String cmd) {
  cmd.trim();
  if (cmd.length() == 0) return;

  if (cmd.startsWith("SWEEP_JAM")) {
    int sp1 = cmd.indexOf(' ');
    int sp2 = cmd.indexOf(' ', sp1 + 1);
    if (sp2 != -1) {
      unsigned long secs = cmd.substring(sp2 + 1).toInt();
      if (jamming_enabled) stop_jamming();
      if (secs > 0) {
        stop_time    = millis() + secs * 1000UL;
        has_duration = true;
      } else {
        has_duration = false;
      }
      start_jamming();
    } else {
      Serial.println("ERROR: uso -> SWEEP_JAM <modo> <segundos>");
    }
  }
  else if (cmd.startsWith("STOP")) {
    stop_jamming();
  }
  else if (cmd == "STATUS") {
    if (jamming_enabled) {
      Serial.print("JAMMING_ACTIVE MODE=");
      Serial.print(toggleSwitch.getState() == HIGH ? "SWEEP" : "RANDOM");
      if (has_duration) {
        unsigned long rem = (stop_time > millis())
                            ? (stop_time - millis()) / 1000UL : 0;
        Serial.print(" REMAINING="); Serial.print(rem);
      }
      Serial.println();
    } else {
      Serial.println("JAMMING_INACTIVE");
    }
  }
  else {
    Serial.println("ERROR: Unknown command");
  }
}


// ═════════════════════════════════════════════════════════
//  INIT SPI
// ═════════════════════════════════════════════════════════
void initVSPI() {
  sp = new SPIClass(VSPI);
  sp->begin();
  if (radio.begin(sp)) {
    delay(1000);
    Serial.println("VSPI Started !!!");
    configureRadio(radio);
    radio.printPrettyDetails();
  } else {
    Serial.println("VSPI couldn't start !!!");
  }
}

void initHSPI() {
  hp = new SPIClass(HSPI);
  hp->begin();
  if (radio1.begin(hp)) {
    delay(1000);
    Serial.println("HSPI Started !!!");
    configureRadio(radio1);
    radio1.printPrettyDetails();
  } else {
    Serial.println("HSPI couldn't start !!!");
  }
}


// ═════════════════════════════════════════════════════════
//  SETUP
// ═════════════════════════════════════════════════════════
void setup() {
  Serial.begin(115200);
  pinMode(33, INPUT_PULLUP);
  esp_bt_controller_deinit();
  esp_wifi_stop();
  esp_wifi_deinit();
  esp_wifi_disconnect();

  toggleSwitch.setDebounceTime(50);

  Wire.begin(SDA_PIN, SCL_PIN);
  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    Serial.println("ERROR: Fallo al iniciar OLED");
  } else {
    display.clearDisplay();
    display.display();
    updateOLED();
  }

  initVSPI();
  initHSPI();

  // Crear tarea de jamming en Core 0 con prioridad alta
  xTaskCreatePinnedToCore(
    jammingCore0,         // función
    "jam_core0",          // nombre
    2048,                 // stack
    NULL,                 // parámetro
    configMAX_PRIORITIES - 1,  // prioridad máxima
    &jammingTaskHandle,   // handle
    0                     // Core 0
  );
  Serial.println("Gadget listo. Esperando comando SWEEP_JAM...");
}


// ═════════════════════════════════════════════════════════
//  LOOP — Core 1
//  Serial + HSPI jamming + OLED
//  No interfiere en absoluto con el jamming de Core 0.
// ═════════════════════════════════════════════════════════
void loop() {
  // 1. Toggle switch (solo Core 1 llama loop())
  toggleSwitch.loop();

  // 2. Comandos serie
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      process_serial_command(serial_buffer);
      serial_buffer = "";
    } else {
      serial_buffer += c;
    }
  }

  // 3. Auto-stop por duración
  if (jamming_enabled && has_duration && millis() >= stop_time) {
    stop_jamming();
  }

  // 4. HSPI — cobertura complementaria (Core 1)
  if (jamming_enabled) {
    if (toggleSwitch.getState() == HIGH) hspi_sweep();
    else                                 hspi_random();
  }

  // 5. OLED cada 200 ms
  if (millis() - oled_last_update > 200) {
    oled_last_update = millis();
    updateOLED();
  }
}
