"""
Servidor Webhook: Twilio WhatsApp → MQTT → ESP32
=================================================
Este servidor recibe mensajes de WhatsApp via Twilio y
los publica en el broker MQTT para que el ESP32 los reciba.

Deploy gratuito recomendado: Railway.app o Render.com
"""

import os
from flask import Flask, request
import paho.mqtt.publish as mqtt_publish
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# ─── CONFIGURACIÓN ──────────────────────────────────────────────
MQTT_BROKER    = "broker.hivemq.com"
MQTT_TOPIC_CMD = "esp32shield/relay1/cmd"    # debe coincidir con el ESP32

# Número(s) de WhatsApp autorizados para enviar comandos
# Formato: "whatsapp:+521XXXXXXXXXX"  (incluye código de país)
NUMEROS_AUTORIZADOS = [
    "whatsapp:+521XXXXXXXXXX",   # ← Cambia por tu número
]

# Comandos válidos y respuestas
COMANDOS = {
    "activar":  "activar",
    "on":       "activar",
    "encender": "activar",
    "1":        "activar",
}
# ────────────────────────────────────────────────────────────────

@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    from_number = request.form.get("From", "").strip()
    body        = request.form.get("Body", "").strip().lower()

    resp = MessagingResponse()

    # Verificar autorización
    if from_number not in NUMEROS_AUTORIZADOS:
        print(f"[AUTH] Número no autorizado: {from_number}")
        resp.message("❌ No autorizado.")
        return str(resp)

    print(f"[MSG] De: {from_number} | Mensaje: '{body}'")

    if body in COMANDOS:
        cmd = COMANDOS[body]
        try:
            mqtt_publish.single(
                topic    = MQTT_TOPIC_CMD,
                payload  = cmd,
                hostname = MQTT_BROKER,
                port     = 1883,
            )
            resp.message("✅ *Relevador activado* por 2 segundos.")
            print(f"[MQTT] Publicado '{cmd}' en {MQTT_TOPIC_CMD}")
        except Exception as e:
            resp.message(f"⚠️ Error al comunicar con el dispositivo: {e}")
            print(f"[ERROR] MQTT: {e}")

    elif body in ["ayuda", "help", "?"]:
        resp.message(
            "📋 *Comandos disponibles:*\n"
            "• activar / on / encender / 1 → Activa el relevador 2 seg\n"
            "• ayuda → Muestra esta ayuda"
        )
    else:
        resp.message(
            f"❓ Comando no reconocido: '{body}'\n"
            "Envía *ayuda* para ver los comandos disponibles."
        )
        

    return str(resp)


@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "broker": MQTT_BROKER, "topic": MQTT_TOPIC_CMD}, 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Servidor iniciado en puerto {port}")
    app.run(host="0.0.0.0", port=port)
