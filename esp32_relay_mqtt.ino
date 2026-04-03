/**
 * ESP32 Control Shield V1 - Relay via WhatsApp + MQTT
 * -------------------------------------------------------
 * Esquemático: RL1 controlado por GPIO2 (D2) via optoacoplador U2
 * Lógica: ACTIVA en LOW (LOW = relay ON, HIGH = relay OFF)
 * 
 * Librerías necesarias (instalar en Arduino IDE):
 *   - PubSubClient by Nick O'Leary  (Sketch > Include Library > Manage Libraries)
 *   - WiFi (ya incluida en el core ESP32)
 */

#include <WiFi.h>
#include <PubSubClient.h>

// ─── CONFIGURACIÓN ──────────────────────────────────────────────
const char* WIFI_SSID     = "TU_WIFI_SSID";
const char* WIFI_PASSWORD = "TU_WIFI_PASSWORD";

// Broker MQTT público (gratuito). Puedes usar tu propio broker.
const char* MQTT_BROKER   = "broker.hivemq.com";
const int   MQTT_PORT     = 1883;
const char* MQTT_TOPIC    = "esp32shield/relay1/cmd";   // debe coincidir con el servidor
const char* MQTT_STATUS   = "esp32shield/relay1/status"; // topic de estado

// Pines de relevadores según esquemático
//   Out1 → GPIO2  (D2)   ← Este ejemplo usa el RL1
//   Out2 → GPIO4  (D4)
//   Out3 → GPIO32 (D32)
//   Out4 → GPIO33 (D33)
//   Out5 → GPIO27 (D27)
//   Out6 → GPIO15 (D15)
#define RELAY1_PIN  2

// Tiempo de activación en ms
#define ACTIVATION_MS 2000

// Lógica del relevador (optoacoplador con pull-up → activo en LOW)
#define RELAY_ON  LOW
#define RELAY_OFF HIGH
// ────────────────────────────────────────────────────────────────

WiFiClient   espClient;
PubSubClient mqttClient(espClient);

bool relayBusy = false;
unsigned long relayStartTime = 0;

// ─── CALLBACK MQTT ──────────────────────────────────────────────
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String msg = "";
  for (unsigned int i = 0; i < length; i++) {
    msg += (char)payload[i];
  }
  msg.trim();
  msg.toLowerCase();

  Serial.print("[MQTT] Mensaje recibido: ");
  Serial.println(msg);

  if (!relayBusy && (msg == "activar" || msg == "on" || msg == "encender" || msg == "1")) {
    Serial.println(">>> Activando relevador por 2 segundos...");
    relayBusy = true;
    relayStartTime = millis();
    digitalWrite(RELAY1_PIN, RELAY_ON);
    mqttClient.publish(MQTT_STATUS, "ON");
  } else if (relayBusy) {
    Serial.println("! El relevador ya está activo, ignorando comando.");
  }
}

// ─── CONEXIÓN WIFI ──────────────────────────────────────────────
void connectWiFi() {
  Serial.print("[WiFi] Conectando a ");
  Serial.print(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n[WiFi] Conectado! IP: " + WiFi.localIP().toString());
}

// ─── RECONEXIÓN MQTT ────────────────────────────────────────────
void reconnectMQTT() {
  while (!mqttClient.connected()) {
    Serial.print("[MQTT] Conectando al broker...");
    // ID único para evitar conflictos
    String clientId = "ESP32Shield_" + String((uint32_t)ESP.getEfuseMac(), HEX);
    if (mqttClient.connect(clientId.c_str())) {
      Serial.println(" conectado!");
      mqttClient.subscribe(MQTT_TOPIC);
      mqttClient.publish(MQTT_STATUS, "ONLINE");
      Serial.println("[MQTT] Suscrito a: " + String(MQTT_TOPIC));
    } else {
      Serial.print(" falló (rc=");
      Serial.print(mqttClient.state());
      Serial.println("). Reintentando en 5s...");
      delay(5000);
    }
  }
}

// ─── SETUP ──────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(100);

  // Asegurar que el relevador inicie apagado
  pinMode(RELAY1_PIN, OUTPUT);
  digitalWrite(RELAY1_PIN, RELAY_OFF);

  connectWiFi();

  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);
  mqttClient.setKeepAlive(60);
}

// ─── LOOP ───────────────────────────────────────────────────────
void loop() {
  // Reconectar WiFi si se pierde
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WiFi] Conexión perdida, reconectando...");
    connectWiFi();
  }

  // Reconectar MQTT si se pierde
  if (!mqttClient.connected()) {
    reconnectMQTT();
  }
  mqttClient.loop();

  // Apagar relevador después de ACTIVATION_MS sin usar delay() (no bloquea el loop)
  if (relayBusy && (millis() - relayStartTime >= ACTIVATION_MS)) {
    digitalWrite(RELAY1_PIN, RELAY_OFF);
    mqttClient.publish(MQTT_STATUS, "OFF");
    relayBusy = false;
    Serial.println(">>> Relevador apagado.");
  }
}
