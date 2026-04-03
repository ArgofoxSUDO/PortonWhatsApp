import os
from flask import Flask, request
import paho.mqtt.publish as mqtt_publish
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

MQTT_BROKER    = "broker.hivemq.com"
MQTT_TOPIC_CMD = "esp32shield/relay1/cmd"

NUMEROS_AUTORIZADOS = [
    "whatsapp:+521XXXXXXXXXX",
]

COMANDOS = {
    "activar":  "activar",
    "on":       "activar",
    "encender": "activar",
    "1":        "activar",
}

@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    from_number = request.form.get("From", "").strip()
    body        = request.form.get("Body", "").strip().lower()
    resp = MessagingResponse()

    if from_number not in NUMEROS_AUTORIZADOS:
        resp.message("❌ No autorizado.")
        return str(resp)

    if body in COMANDOS:
        try:
            mqtt_publish.single(
                topic    = MQTT_TOPIC_CMD,
                payload  = COMANDOS[body],
                hostname = MQTT_BROKER,
                port     = 1883,
            )
            resp.message("✅ Relevador activado por 2 segundos.")
        except Exception as e:
            resp.message(f"⚠️ Error: {e}")
    elif body in ["ayuda", "help"]:
        resp.message("Comandos: activar, on, encender, 1")
    else:
        resp.message(f"Comando no reconocido: '{body}'. Envía ayuda.")

    return str(resp)

@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok"}, 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
