import os
from datetime import datetime
import pytz
from flask import Flask, request
import paho.mqtt.publish as mqtt_publish
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

MQTT_BROKER = "broker.hivemq.com"
ZONA_HORARIA = pytz.timezone("America/Mexico_City")
COOLDOWN_SEGUNDOS = 5
HORA_INICIO = 2
HORA_FIN = 23

NUMEROS_AUTORIZADOS = [
    "whatsapp:+5215638711451",  # ← tu número
]

COMANDOS = {
    "abrir":  {"topic": "esp32shield/relay1/cmd", "nombre": "Porton"},
    "puerta": {"topic": "esp32shield/relay2/cmd", "nombre": "Peatonal"},
}

ultimo_comando = None

def hora_permitida():
    ahora = datetime.now(ZONA_HORARIA)
    return HORA_INICIO <= ahora.hour < HORA_FIN

def en_cooldown():
    global ultimo_comando
    if ultimo_comando is None:
        return False
    diferencia = (datetime.now(ZONA_HORARIA) - ultimo_comando).total_seconds()
    return diferencia < COOLDOWN_SEGUNDOS

def segundos_restantes():
    if ultimo_comando is None:
        return 0
    diferencia = (datetime.now(ZONA_HORARIA) - ultimo_comando).total_seconds()
    return max(0, int(COOLDOWN_SEGUNDOS - diferencia))

@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    global ultimo_comando
    from_number = request.form.get("From", "").strip()
    author      = request.form.get("Author", "").strip()
    body        = request.form.get("Body", "").strip().lower()
    resp = MessagingResponse()

    # En grupos usar Author, en chat individual usar From
    numero_real = author if author else from_number

    if numero_real not in NUMEROS_AUTORIZADOS:
        resp.message("❌ No autorizado.")
        return str(resp)

    if not hora_permitida():
        resp.message("🕐 Sistema inactivo. Horario: 9:00 a 23:00.")
        return str(resp)

    if en_cooldown():
        resp.message(f"⏳ Comando en ejecución. Espera {segundos_restantes()} segundos.")
        return str(resp)

    if body in COMANDOS:
        cmd = COMANDOS[body]
        try:
            mqtt_publish.single(
                topic    = cmd["topic"],
                payload  = "activar",
                hostname = MQTT_BROKER,
                port     = 1883,
            )
            ultimo_comando = datetime.now(ZONA_HORARIA)
            resp.message(f"✅ {cmd['nombre']} activado por 2 segundos.")
        except Exception as e:
            resp.message(f"⚠️ Error: {e}")
    elif body in ["Ayuda", "help"]:
        resp.message(
            "📋 Comandos disponibles:\n"
            "• abrir → Activa Relay 1\n"
            "• puerta → Activa Relay 2\n"
            "Horario: 9:00 a 23:00"
        )
    else:
        resp.message("❓ Comando no reconocido. Envía *ayuda*.")

    return str(resp)

@app.route("/health", methods=["GET"])
def health():
    ahora = datetime.now(ZONA_HORARIA)
    return {
        "status": "ok",
        "hora_actual": ahora.strftime("%H:%M"),
        "sistema_activo": hora_permitida(),
        "en_cooldown": en_cooldown(),
    }, 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
