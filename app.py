"""
Aplicación Flask que integra la API de Pagos de Khipu.
Simula un comercio que cobra mediante llamadas directas a la API.
"""

import os
import logging
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from dotenv import load_dotenv
from khipu_client import KhipuClient

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-prod")

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Monto máximo permitido en DemoBank (entorno sandbox)
MAX_AMOUNT_CLP = 5000

# Instanciar el cliente de Khipu (lee las vars de entorno automáticamente)
try:
    khipu = KhipuClient()
except ValueError as e:
    logger.error(f"Error al inicializar KhipuClient: {e}")
    khipu = None


@app.route("/")
def index():
    """Página principal con el formulario de pago."""
    return render_template("index.html", max_amount=MAX_AMOUNT_CLP)


@app.route("/crear-pago", methods=["POST"])
def crear_pago():
    """
    Recibe el formulario, llama a la API de Khipu y redirige al usuario
    a la URL de pago generada.
    """
    if khipu is None:
        return render_template(
            "index.html",
            error="El servidor no está configurado. Verifica las credenciales de Khipu en el archivo .env",
            max_amount=MAX_AMOUNT_CLP,
        )

    # Leer y validar datos del formulario
    subject = request.form.get("subject", "").strip()
    payer_email = request.form.get("payer_email", "").strip()

    try:
        amount = float(request.form.get("amount", 0))
    except ValueError:
        return render_template(
            "index.html",
            error="El monto ingresado no es válido.",
            max_amount=MAX_AMOUNT_CLP,
        )

    # Validaciones
    if not subject:
        return render_template(
            "index.html",
            error="La descripción del pago es obligatoria.",
            max_amount=MAX_AMOUNT_CLP,
        )

    if amount <= 0 or amount > MAX_AMOUNT_CLP:
        return render_template(
            "index.html",
            error=f"El monto debe ser entre $1 y ${MAX_AMOUNT_CLP:,.0f} CLP (límite DemoBank).",
            max_amount=MAX_AMOUNT_CLP,
        )

    # URLs de callback
    base_url = os.getenv("APP_BASE_URL", "http://localhost:5000")
    return_url = f"{base_url}/retorno"
    cancel_url = f"{base_url}/cancelado"

    # notify_url solo funciona con URLs públicas (no localhost).
    # En producción setear APP_BASE_URL con la URL pública (ej: ngrok).
    raw_notify = f"{base_url}/notificacion"
    notify_url = raw_notify if not base_url.startswith("http://localhost") else None

    try:
        logger.info(f"Creando pago: subject='{subject}', amount={amount}, email='{payer_email}'")

        payment = khipu.create_payment(
            subject=subject,
            amount=amount,
            currency="CLP",
            return_url=return_url,
            cancel_url=cancel_url,
            notify_url=notify_url,
            payer_email=payer_email if payer_email else None,
        )

        # Guardar el payment_id en sesión para verificarlo al retornar
        session["payment_id"] = payment.get("payment_id")
        session["payment_subject"] = subject
        session["payment_amount"] = amount

        payment_url = payment.get("payment_url")
        logger.info(f"Pago creado exitosamente. payment_id={payment.get('payment_id')}, url={payment_url}")

        # Redirigir al usuario a Khipu para completar el pago
        return redirect(payment_url)

    except Exception as e:
        logger.error(f"Error al crear pago en Khipu: {e}")
        error_msg = str(e)
        if hasattr(e, "response") and e.response is not None:
            try:
                error_detail = e.response.json()
                error_msg = error_detail.get("message", error_msg)
            except Exception:
                pass
        return render_template(
            "index.html",
            error=f"Error al conectar con Khipu: {error_msg}",
            max_amount=MAX_AMOUNT_CLP,
        )


@app.route("/retorno")
def retorno():
    """
    Khipu redirige aquí tras un pago exitoso.
    Se verifica el estado real del pago consultando la API.
    """
    payment_id = request.args.get("payment_id") or session.get("payment_id")

    if not payment_id:
        return render_template("success.html", payment=None)

    try:
        payment = khipu.get_payment(payment_id)
        logger.info(f"Retorno de pago. payment_id={payment_id}, status={payment.get('status')}")
        # Si el status aún no está disponible, marcarlo como pending
        if not payment.get("status"):
            payment["status"] = "pending"
        return render_template("success.html", payment=payment)
    except Exception as e:
        logger.error(f"Error al verificar pago {payment_id}: {e}")
        # Aun así mostramos la página con el payment_id y estado pending
        return render_template(
            "success.html",
            payment={"payment_id": payment_id, "status": "pending"},
        )


@app.route("/cancelado")
def cancelado():
    """Khipu redirige aquí si el usuario cancela el pago."""
    payment_id = request.args.get("payment_id") or session.get("payment_id")
    subject = session.get("payment_subject", "")
    amount = session.get("payment_amount", 0)

    logger.info(f"Pago cancelado. payment_id={payment_id}")

    return render_template(
        "cancel.html",
        payment_id=payment_id,
        subject=subject,
        amount=amount,
    )


@app.route("/notificacion", methods=["POST"])
def notificacion():
    """
    Webhook: Khipu notifica aquí cuando un pago es conciliado.
    En producción, aquí se actualiza la base de datos del comercio.
    """
    notification_token = request.form.get("notification_token")
    api_version = request.form.get("api_version", "")

    logger.info(f"Notificación recibida. token={notification_token}, api_version={api_version}")

    if not notification_token:
        return jsonify({"error": "notification_token requerido"}), 400

    try:
        payment = khipu.confirm_payment_by_token(notification_token)
        logger.info(f"Pago confirmado via notificación. payment_id={payment.get('payment_id')}, status={payment.get('status')}")

        # En producción: actualizar tu BD aquí
        # ejemplo: order_service.mark_as_paid(payment["payment_id"])

        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error(f"Error procesando notificación: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/estado/<payment_id>")
def estado_pago(payment_id: str):
    """Endpoint de utilidad para consultar el estado de un pago por ID (útil para debug)."""
    try:
        payment = khipu.get_payment(payment_id)
        return jsonify(payment)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug, port=5000)
