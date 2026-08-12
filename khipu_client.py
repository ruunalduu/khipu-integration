"""
Cliente para la API de Pagos Instantáneos de Khipu v3.
Documentación: https://docs.khipu.com/apis/v3/instant-payments/openapi

Autenticación API v3:
  - Header requerido: x-api-key con la API Key generada desde el portal de Khipu
  - Las API Keys se generan en: Opciones de cuenta → Para integrar Khipu → API Keys
  - Ref: https://docs.khipu.com/payment-solutions/instant-payments/payment-auth
"""

import os
import requests
from typing import Optional


KHIPU_API_BASE = "https://payment-api.khipu.com/v3"


class KhipuClient:
    """
    Wrapper para la API REST de Khipu v3.
    Autenticación: header x-api-key con la API Key de la cuenta de cobro.
    """

    def __init__(self, api_key: Optional[str] = None, receiver_id: Optional[str] = None):
        # La API v3 autentica con x-api-key (generada desde el portal de Khipu)
        self.api_key = api_key or os.getenv("KHIPU_API_KEY")
        # receiver_id es opcional en v3, útil para soporte/logs
        self.receiver_id = receiver_id or os.getenv("KHIPU_RECEIVER_ID")

        if not self.api_key:
            raise ValueError(
                "Se requiere KHIPU_API_KEY. "
                "Generala en: Portal Khipu → Opciones de cuenta → Para integrar Khipu → API Keys"
            )

    def _get_headers(self) -> dict:
        """Construye los headers de autenticación requeridos por la API v3."""
        return {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    def create_payment(
        self,
        subject: str,
        amount: float,
        currency: str = "CLP",
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        notify_url: Optional[str] = None,
        payer_email: Optional[str] = None,
        notify_api_version: str = "3.0",
        expires_date: Optional[str] = None,
    ) -> dict:
        """
        Crea un cobro en Khipu.

        Args:
            subject: Descripción del cobro (obligatorio)
            amount: Monto a cobrar (obligatorio)
            currency: Moneda ISO 4217, default "CLP"
            return_url: URL de redirección al completar el pago
            cancel_url: URL de redirección al cancelar el pago
            notify_url: URL donde Khipu notifica el pago (webhook)
            payer_email: Email del pagador (opcional, pre-llena el form)
            notify_api_version: Versión de la API para notificaciones
            expires_date: Fecha de expiración ISO 8601 (ej: "2024-12-31T23:59:59Z")

        Returns:
            dict con los datos del cobro creado, incluyendo payment_url y payment_id
        """
        payload = {
            "subject": subject,
            "amount": amount,
            "currency": currency,
            "notify_api_version": notify_api_version,
        }

        # Campos opcionales: solo los incluimos si tienen valor
        if return_url:
            payload["return_url"] = return_url
        if cancel_url:
            payload["cancel_url"] = cancel_url
        if notify_url:
            payload["notify_url"] = notify_url
        if payer_email:
            payload["payer_email"] = payer_email
        if expires_date:
            payload["expires_date"] = expires_date

        response = requests.post(
            f"{KHIPU_API_BASE}/payments",
            headers=self._get_headers(),
            json=payload,
            timeout=15,
        )

        if not response.ok:
            # Loguear el detalle del error que devuelve Khipu
            import logging
            logging.getLogger(__name__).error(
                f"Khipu API error {response.status_code}: {response.text}"
            )

        response.raise_for_status()
        return response.json()

    def get_payment(self, payment_id: str) -> dict:
        """
        Consulta el estado de un pago por su ID.

        Args:
            payment_id: ID del pago retornado al crear el cobro

        Returns:
            dict con el estado y detalle del pago
        """
        response = requests.get(
            f"{KHIPU_API_BASE}/payments/{payment_id}",
            headers=self._get_headers(),
            timeout=15,
        )

        response.raise_for_status()
        return response.json()

    def confirm_payment_by_token(self, notification_token: str) -> dict:
        """
        Confirma un pago usando el token de notificación recibido via webhook.

        Args:
            notification_token: Token recibido en el webhook de Khipu

        Returns:
            dict con los datos del pago confirmado
        """
        response = requests.get(
            f"{KHIPU_API_BASE}/payments",
            headers=self._get_headers(),
            params={"notification_token": notification_token},
            timeout=15,
        )

        response.raise_for_status()
        return response.json()
