#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cliente base para comunicación con el servidor de WhatsApp.
"""

import frappe
import requests
from typing import Dict, Any, Optional
import json


class WhatsAppAPIClient:
    """
    Cliente base para hacer requests al servidor de WhatsApp externo.
    Lee la configuración de WhatsApp Settings.
    """

    def __init__(self, session_id: Optional[str] = None):
        """
        Inicializa el cliente con configuración de WhatsApp Settings.

        Args:
            session_id: ID de la sesión (opcional)
        """
        self.session_id = session_id
        self.settings = self._get_settings()
        self.base_url = self.settings.api_base_url
        self.api_key = self.settings.get_password("api_key")
        self.timeout = self.settings.api_timeout or 30
        self.retry_attempts = self.settings.api_retry_attempts or 3

    def _get_settings(self) -> Any:
        """
        Obtiene la configuración de WhatsApp Settings.

        Returns:
            Documento WhatsApp Settings
        """
        if not frappe.db.exists("DocType", "WhatsApp Settings"):
            frappe.throw("WhatsApp Settings DocType no existe")

        settings = frappe.get_single("WhatsApp Settings")

        if not settings.enabled:
            frappe.throw("El módulo de WhatsApp está deshabilitado en Settings")

        if not settings.api_base_url:
            frappe.throw("URL Base de API no configurada en WhatsApp Settings")

        return settings

    def _get_headers(self) -> Dict[str, str]:
        """
        Construye los headers para las peticiones.

        Returns:
            Dict con headers
        """
        headers = {
            "Content-Type": "application/json",
        }

        if self.api_key:
            headers["X-API-Key"] = self.api_key

        return headers

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        use_session_id: bool = True
    ) -> Dict[str, Any]:
        """
        Realiza una petición HTTP al servidor de WhatsApp.

        Args:
            method: Método HTTP (GET, POST, etc.)
            endpoint: Endpoint de la API (sin sessionId)
            data: Datos para el body (POST/PUT)
            params: Parámetros de query string
            use_session_id: Si debe agregar sessionId al endpoint

        Returns:
            Respuesta JSON del servidor
        """
        # Construir URL
        if use_session_id and self.session_id:
            url = f"{self.base_url}{endpoint.format(sessionId=self.session_id)}"
        else:
            url = f"{self.base_url}{endpoint}"

        headers = self._get_headers()

        # Realizar petición con reintentos
        last_error = None
        for attempt in range(self.retry_attempts):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    headers=headers,
                    timeout=self.timeout
                )

                # Si es exitoso, retornar
                if response.status_code == 200:
                    return response.json()

                # Si es error del cliente (4xx), no reintentar
                if 400 <= response.status_code < 500:
                    error_data = response.json() if response.text else {}
                    frappe.throw(
                        f"Error del servidor WhatsApp ({response.status_code}): {error_data.get('message', response.text)}"
                    )

                # Si es error del servidor (5xx), reintentar
                last_error = f"Error {response.status_code}: {response.text}"

            except requests.exceptions.Timeout:
                last_error = f"Timeout después de {self.timeout} segundos"

            except requests.exceptions.ConnectionError:
                last_error = f"Error de conexión al servidor {self.base_url}"

            except requests.exceptions.RequestException as e:
                last_error = f"Error en la petición: {str(e)}"

            # Si no es el último intento, esperar un poco
            if attempt < self.retry_attempts - 1:
                import time
                time.sleep(2 ** attempt)  # Backoff exponencial

        # Si llegamos aquí, todos los intentos fallaron
        frappe.throw(f"Error después de {self.retry_attempts} intentos: {last_error}")

    def get(self, endpoint: str, params: Optional[Dict] = None, use_session_id: bool = True) -> Dict[str, Any]:
        """
        Petición GET al servidor.

        Args:
            endpoint: Endpoint de la API
            params: Parámetros de query string
            use_session_id: Si debe usar sessionId

        Returns:
            Respuesta JSON
        """
        return self._make_request("GET", endpoint, params=params, use_session_id=use_session_id)

    def post(self, endpoint: str, data: Optional[Dict] = None, use_session_id: bool = True) -> Dict[str, Any]:
        """
        Petición POST al servidor.

        Args:
            endpoint: Endpoint de la API
            data: Datos del body
            use_session_id: Si debe usar sessionId

        Returns:
            Respuesta JSON
        """
        return self._make_request("POST", endpoint, data=data, use_session_id=use_session_id)

    def put(self, endpoint: str, data: Optional[Dict] = None, use_session_id: bool = True) -> Dict[str, Any]:
        """
        Petición PUT al servidor.

        Args:
            endpoint: Endpoint de la API
            data: Datos del body
            use_session_id: Si debe usar sessionId

        Returns:
            Respuesta JSON
        """
        return self._make_request("PUT", endpoint, data=data, use_session_id=use_session_id)

    def delete(self, endpoint: str, use_session_id: bool = True) -> Dict[str, Any]:
        """
        Petición DELETE al servidor.

        Args:
            endpoint: Endpoint de la API
            use_session_id: Si debe usar sessionId

        Returns:
            Respuesta JSON
        """
        return self._make_request("DELETE", endpoint, use_session_id=use_session_id)

