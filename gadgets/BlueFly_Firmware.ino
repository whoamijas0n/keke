#include "RF24.h"
#include <SPI.h>
#include <ezButton.h>
#include "esp_bt.h"
#include "esp_wifi.h"

// ========== PANTALLA OLED 0.96" (SDA=4, SCL=5) ==========
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#define SCREEN_WIDTH  128
#define SCREEN_HEIGHT  64
#define OLED_ADDR      0x3C
#define SDA_PIN        4
#define SCL_PIN        5
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);
// =========================================================

SPIClass *sp = nullptr;
SPIClass *hp = nullptr;

RF24 radio(16, 15, 16000000);   // HSPI
RF24 radio1(22, 21, 16000000);  // VSPI

unsigned int flag = 0;   // HSPI
unsigned int flagv = 0;  // VSPI
int ch = 45;
int ch1 = 45;

ezButton toggleSwitch(33);

// ========== VARIABLES DE CONTROL (sin cambios) ==========
bool jamming_enabled = false;
unsigned long stop_time = 0;
bool has_duration = false;

// Buffer para comandos serie
String serial_buffer = "";

// ========== VARIABLES EXCLUSIVAS DE OLED ==========
static bool  oled_blink      = false;
static unsigned long oled_last_blink  = 0;
static unsigned long oled_last_update = 0;
// =====================================================


// ─────────────────────────────────────────────────────────────────────────────
//  DIBUJAR ÍCONO BLUETOOTH (símbolo clásico ᛒ)
//  Parámetros: cx/cy = centro, h = semialtura, w = semianchura
// ─────────────────────────────────────────────────────────────────────────────
void drawBTIcon(int cx, int cy, int h, int w) {
  int h3 = h / 3;          // un tercio de la altura
  // Línea vertical principal (doble para grosor)
  display.drawLine(cx,   cy - h, cx,   cy + h, WHITE);
  display.drawLine(cx+1, cy - h, cx+1, cy + h, WHITE);

  // Brazo superior derecho: cima → vértice derecho
  display.drawLine(cx,   cy - h,  cx + w, cy - h3, WHITE);
  // Regreso al centro
  display.drawLine(cx + w, cy - h3, cx,   cy,      WHITE);

  // Brazo inferior derecho: centro → vértice derecho
  display.drawLine(cx,   cy,       cx + w, cy + h3, WHITE);
  // Regreso al fondo
  display.drawLine(cx + w, cy + h3, cx,   cy + h,   WHITE);
}


// ─────────────────────────────────────────────────────────────────────────────
//  ACTUALIZAR PANTALLA OLED
//  Se llama desde loop() cada ~200 ms. NO toca ninguna variable de radio.
// ─────────────────────────────────────────────────────────────────────────────
void updateOLED() {
  // — Parpadeo del indicador de estado cada 500 ms —
  if (millis() - oled_last_blink > 500) {
    oled_blink = !oled_blink;
    oled_last_blink = millis();
  }

  display.clearDisplay();

  // ── Marco exterior redondeado ──────────────────────────────────────────────
  display.drawRoundRect(0, 0, 128, 64, 4, WHITE);

  // ── Panel izquierdo: ícono Bluetooth ──────────────────────────────────────
  // Círculo de fondo del ícono
  display.drawCircle(24, 32, 21, WHITE);

  // Ícono BT centrado en (24, 32)
  drawBTIcon(24, 32, 15, 10);

  // ── Divisor vertical ──────────────────────────────────────────────────────
  display.drawLine(49, 4, 49, 59, WHITE);

  // ── Panel derecho: título ─────────────────────────────────────────────────
  //   "Blue" en tamaño 2  (48 × 16 px)
  display.setTextSize(2);
  display.setTextColor(WHITE);
  display.setCursor(55, 5);
  display.print("Blue");

  //   "-Fly" en tamaño 2 justo debajo
  display.setCursor(55, 22);
  display.print("-Fly");

  // Línea separadora bajo el título
  display.drawLine(52, 41, 124, 41, WHITE);

  // ── Subtítulo: estado ─────────────────────────────────────────────────────
  display.setTextSize(1);
  display.setTextColor(WHITE);

  if (jamming_enabled) {
    // Indicador circular parpadeante (activo)
    if (oled_blink) {
      display.fillCircle(57, 53, 3, WHITE);
    } else {
      display.drawCircle(57, 53, 3, WHITE);
    }
    display.setCursor(64, 49);
    display.print("Iniciado");
  } else {
    // Indicador circular fijo (inactivo)
    display.drawCircle(57, 53, 3, WHITE);
    display.setCursor(64, 49);
    display.print("Detenido");
  }

  display.display();
}


// ─────────────────────────────────────────────────────────────────────────────
//  FUNCIONES ORIGINALES — SIN MODIFICACIONES
// ─────────────────────────────────────────────────────────────────────────────
void two() {
  if (flagv == 0) {
    ch1 += 4;
  } else {
    ch1 -= 4;
  }
  if (flag == 0) {
    ch += 2;
  } else {
    ch -= 2;
  }
  if ((ch1 > 79) && (flagv == 0)) {
    flagv = 1;
  } else if ((ch1 < 2) && (flagv == 1)) {
    flagv = 0;
  }
  if ((ch > 79) && (flag == 0)) {
    flag = 1;
  } else if ((ch < 2) && (flag == 1)) {
    flag = 0;
  }
  radio.setChannel(ch);
  radio1.setChannel(ch1);
}

void one() {
  radio1.setChannel(random(80));
  radio.setChannel(random(80));
  delayMicroseconds(random(60));
}

void start_jamming() {
  if (!jamming_enabled) {
    radio.startConstCarrier(RF24_PA_MAX, ch);
    radio1.startConstCarrier(RF24_PA_MAX, ch1);
    jamming_enabled = true;
    Serial.println("JAMMING_STARTED");
  }
}

void stop_jamming() {
  if (jamming_enabled) {
    radio.stopConstCarrier();
    radio1.stopConstCarrier();
    jamming_enabled = false;
    has_duration = false;
    Serial.println("STOPPED");
  }
}

void process_serial_command(String cmd) {
  cmd.trim();
  if (cmd.length() == 0) return;

  if (cmd.startsWith("SWEEP_JAM")) {
    int firstSpace = cmd.indexOf(' ');
    int secondSpace = cmd.indexOf(' ', firstSpace + 1);
    if (secondSpace != -1) {
      String dur_str = cmd.substring(secondSpace + 1);
      unsigned long duration_sec = dur_str.toInt();

      if (jamming_enabled) stop_jamming();

      flag = 0;
      flagv = 0;
      ch = 45;
      ch1 = 45;
      radio.setChannel(ch);
      radio1.setChannel(ch1);

      if (duration_sec > 0) {
        stop_time = millis() + duration_sec * 1000;
        has_duration = true;
      } else {
        has_duration = false;
      }

      start_jamming();
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
        unsigned long remaining = (stop_time > millis()) ? (stop_time - millis()) / 1000 : 0;
        Serial.print(" REMAINING=");
        Serial.print(remaining);
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


// ─────────────────────────────────────────────────────────────────────────────
//  INICIALIZACIÓN
// ─────────────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  esp_bt_controller_deinit();
  esp_wifi_stop();
  esp_wifi_deinit();
  esp_wifi_disconnect();

  toggleSwitch.setDebounceTime(50);

  // Inicializar OLED
  Wire.begin(SDA_PIN, SCL_PIN);
  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    Serial.println("ERROR: Fallo al iniciar OLED");
    // El firmware continúa funcionando aunque la pantalla falle
  } else {
    display.clearDisplay();
    display.display();
    updateOLED();   // Muestra estado inicial (Detenido)
  }

  initHP();
  initSP();

  Serial.println("Gadget listo. Esperando comando SWEEP_JAM...");
}

void initSP() {
  sp = new SPIClass(VSPI);
  sp->begin();
  if (radio1.begin(sp)) {
    Serial.println("SP Started !!!");
    radio1.setAutoAck(false);
    radio1.stopListening();
    radio1.setRetries(0, 0);
    radio1.setPALevel(RF24_PA_MAX, true);
    radio1.setDataRate(RF24_2MBPS);
    radio1.setCRCLength(RF24_CRC_DISABLED);
    radio1.printPrettyDetails();
  } else {
    Serial.println("SP couldn't start !!!");
  }
}

void initHP() {
  hp = new SPIClass(HSPI);
  hp->begin();
  if (radio.begin(hp)) {
    Serial.println("HP Started !!!");
    radio.setAutoAck(false);
    radio.stopListening();
    radio.setRetries(0, 0);
    radio.setPALevel(RF24_PA_MAX, true);
    radio.setDataRate(RF24_2MBPS);
    radio.setCRCLength(RF24_CRC_DISABLED);
    radio.printPrettyDetails();
  } else {
    Serial.println("HP couldn't start !!!");
  }
}


// ─────────────────────────────────────────────────────────────────────────────
//  BUCLE PRINCIPAL — lógica original intacta + refresco de OLED no bloqueante
// ─────────────────────────────────────────────────────────────────────────────
void loop() {
  // 1. Leer comandos serie (original)
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      process_serial_command(serial_buffer);
      serial_buffer = "";
    } else {
      serial_buffer += c;
    }
  }

  // 2. Control de tiempo — apagado automático (original)
  if (jamming_enabled && has_duration && millis() >= stop_time) {
    stop_jamming();
  }

  // 3. Actualizar canales según botón (original)
  if (jamming_enabled) {
    toggleSwitch.loop();
    int state = toggleSwitch.getState();
    if (state == HIGH) {
      two();   // barrido
    } else {
      one();   // aleatorio
    }
  }

  // 4. Refresco de OLED — no bloqueante, cada 200 ms
  if (millis() - oled_last_update > 200) {
    oled_last_update = millis();
    updateOLED();
  }
}
