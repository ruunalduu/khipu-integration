# Khipu Payment Integration

Integración de la API de Pagos Instantáneos de Khipu, desarrollada como desafío técnico para el cargo de Customer Success Manager.

## Stack

- **Backend**: Python 3.11+ con Flask
- **API**: Khipu Payments API v3
- **Entorno de pruebas**: DemoBank (mercado chileno, CLP)

## Estructura del proyecto

```
khipu-integration/
├── app.py                  # Servidor Flask principal
├── khipu_client.py         # Cliente de la API de Khipu
├── templates/
│   ├── index.html          # Formulario de pago
│   ├── success.html        # Confirmación de pago exitoso
│   └── cancel.html         # Página de cancelación
├── static/
│   └── style.css           # Estilos
├── .env.example            # Variables de entorno de ejemplo
├── requirements.txt        # Dependencias Python
└── README.md
```

## Configuración

### 1. Crear cuenta en Khipu

1. Registrarse en [khipu.com](https://khipu.com) como desarrollador
2. Crear una cuenta de cobro en el portal
3. Obtener el `receiver_id` y el `secret` desde la sección "Herramientas para desarrolladores"

### 2. Variables de entorno

Copia `.env.example` a `.env` y completa tus credenciales:

```bash
cp .env.example .env
```

```env
KHIPU_RECEIVER_ID=tu_receiver_id
KHIPU_SECRET=tu_secret
FLASK_SECRET_KEY=una_clave_secreta_aleatoria
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Ejecutar

```bash
python app.py
```

La aplicación estará disponible en `http://localhost:5000`

## Flujo de integración

```
1. Usuario abre el formulario de pago (GET /)
2. Envía monto y descripción (POST /crear-pago)
3. Backend llama a POST https://payment-api.khipu.com/v3/payments
4. Khipu devuelve payment_url
5. Usuario es redirigido a Khipu para pagar con DemoBank
6. Khipu redirige a /return (éxito) o /cancel (cancelación)
7. Se verifica el estado del pago via GET /v3/payments/{payment_id}
```

## Endpoints de la API Khipu usados

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/v3/payments` | Crear un cobro |
| GET | `/v3/payments/{id}` | Consultar estado de un pago |

## Autenticación

La API usa el header `Authorization: {receiver_id}:{secret}` (Basic-like, sin base64, directo en el header).

## Pruebas con DemoBank

Al ser redirigido a Khipu, seleccionar **DemoBank** como banco, el cual permite simular pagos en entorno sandbox hasta $5.000 CLP.
