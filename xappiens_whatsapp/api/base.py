#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cliente base para comunicación con el servidor de WhatsApp con Baileys.
Soporta autenticación JWT + API Key según documentación Inbox Hub.
"""

import frappe
import requests
from typing import Dict, Any, Optional
import json
from datetime import datetime, timedelta


class WhatsAppAPIClient:
    """
    Cliente base para hacer requests al servidor de WhatsApp externo (Baileys/Inbox Hub).
    Lee la configuración de WhatsApp Settings.
    Usa solo API Key según nueva documentación simplificada.
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
        # Ya no se necesitan para autenticación JWT
        # self.email = self.settings.api_email
        # self.password = self.settings.get_password("api_password")
        # self.access_token = None
        # self.token_expiry = None

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

    def _authenticate(self) -> str:
        """
        MÉTODO OBSOLETO - Ya no se necesita JWT según nueva documentación.
        Solo se mantiene para compatibilidad, pero no se usa.

        Returns:
            Empty string (no JWT needed)
        """
        # Ya no se necesita autenticación JWT
        return ""

    def _get_headers(self) -> Dict[str, str]:
        """
        Construye los headers para las peticiones.
        Solo usa API Key según nueva documentación simplificada.

        Returns:
            Dict con headers
        """
        headers = {
            "Content-Type": "application/json"
        }

        if self.api_key:
            headers["X-API-Key"] = self.api_key
        else:
            frappe.throw("API Key no configurada en WhatsApp Settings")

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
        last_response = {
            "success": False,
            "status_code": None,
            "message": "Unknown error",
            "data": None
        }
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

                # Si es exitoso, retornar (Baileys usa 200 y 201)
                if response.status_code in [200, 201]:
                    return response.json()

                # Manejo explícito de respuestas de error
                if response.status_code >= 400:
                    try:
                        error_data = response.json() if response.text else {}
                    except Exception:
                        error_data = {}

                    error_message = error_data.get('message') or error_data.get('error') or response.text
                    # Si no debemos reintentar (4xx excepto 429) devolvemos inmediatamente
                    if 400 <= response.status_code < 500 and response.status_code != 429:
                        return {
                            "success": False,
                            "status_code": response.status_code,
                            "message": error_message,
                            "data": error_data
                        }

                    # Para 5xx seguimos reintentando, pero guardamos el error
                    last_response = {
                        "success": False,
                        "status_code": response.status_code,
                        "message": error_message,
                        "data": error_data
                    }
                    continue

                last_response = {
                    "success": False,
                    "status_code": response.status_code,
                    "message": response.text,
                    "data": None
                }

            except requests.exceptions.Timeout:
                last_response = {
                    "success": False,
                    "status_code": None,
                    "message": f"Timeout después de {self.timeout} segundos",
                    "data": None
                }

            except requests.exceptions.ConnectionError:
                last_response = {
                    "success": False,
                    "status_code": None,
                    "message": f"Error de conexión al servidor {self.base_url}",
                    "data": None
                }

            except requests.exceptions.RequestException as e:
                last_response = {
                    "success": False,
                    "status_code": None,
                    "message": f"Error en la petición: {str(e)}",
                    "data": None
                }

            # Si no es el último intento, esperar un poco
            if attempt < self.retry_attempts - 1:
                import time
                time.sleep(2 ** attempt)  # Backoff exponencial

        # Si llegamos aquí, todos los intentos fallaron
        return last_response

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

    # ========== MÉTODOS ESPECÍFICOS PARA BAILEYS/INBOX HUB ==========

    def get_sessions(self, page: int = 1, limit: int = 100, status: str = None) -> Dict[str, Any]:
        """
        Obtiene lista de sesiones del usuario.

        Args:
            page: Página de resultados
            limit: Límite de resultados
            status: Filtrar por estado (connected, disconnected, etc.)

        Returns:
            Dict con lista de sesiones
        """
        params = {"page": page, "limit": limit}
        if status:
            params["status"] = status

        return self.get("/api/sessions", params=params, use_session_id=False)

    def get_session_status(self, session_db_id: int) -> Dict[str, Any]:
        """
        Obtiene estado de una sesión específica.

        Args:
            session_db_id: ID de la sesión en la BD del servidor

        Returns:
            Dict con estado de la sesión
        """
        return self.get(f"/api/sessions/{session_db_id}/status", use_session_id=False)

    def get_session_contacts(self, page: int = 1, limit: int = 100, search: str = None) -> Dict[str, Any]:
        """
        Obtiene contactos de una sesión.

        Args:
            page: Página de resultados
            limit: Límite de resultados
            search: Término de búsqueda

        Returns:
            Dict con lista de contactos
        """
        if not self.session_id:
            frappe.throw("session_id es requerido para obtener contactos")

        params = {"page": page, "limit": limit}
        if search:
            params["search"] = search

        # Endpoint según documentación: /api/contacts/:sessionId
        return self.get(f"/api/contacts/{self.session_id}", params=params, use_session_id=False)

    def get_contact_info(self, contact_id: str) -> Dict[str, Any]:
        """
        Obtiene información detallada de un contacto.

        Args:
            contact_id: Identificador del contacto (MSISDN o JID)

        Returns:
            Dict con los datos del contacto
        """
        if not self.session_id:
            frappe.throw("session_id es requerido para obtener información del contacto")

        return self.get(f"/api/contacts/{self.session_id}/info/{contact_id}", use_session_id=False)

    def get_session_chats(self, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """
        Obtiene lista de chats/conversaciones de una sesión.

        Args:
            page: Página de resultados
            limit: Límite de resultados

        Returns:
            Dict con lista de chats
        """
        if not self.session_id:
            frappe.throw("session_id es requerido para obtener chats")

        params = {"page": page, "limit": limit}

        # Endpoint según documentación: /api/messages/:sessionId/chats
        return self.get(f"/api/messages/{self.session_id}/chats", params=params, use_session_id=False)

    def get_chat_messages(self, chat_id: str, page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """
        Obtiene mensajes de un chat específico.

        Args:
            chat_id: ID del chat
            page: Página de resultados
            limit: Límite de resultados

        Returns:
            Dict con lista de mensajes
        """
        if not self.session_id:
            frappe.throw("session_id es requerido para obtener mensajes")

        params = {"chatId": chat_id, "page": page, "limit": limit}

        # Endpoint correcto según documentación: /api/messages/:sessionId?chatId=:chatId
        return self.get(f"/api/messages/{self.session_id}", params=params, use_session_id=False)

    def send_message(self, to: str, message: str, message_type: str = "text") -> Dict[str, Any]:
        """
        Envía un mensaje de WhatsApp.

        Args:
            to: Número de teléfono destinatario
            message: Contenido del mensaje
            message_type: Tipo de mensaje (text, image, etc.)

        Returns:
            Dict con resultado del envío
        """
        if not self.session_id:
            frappe.throw("session_id es requerido para enviar mensajes")

        # Endpoint según documentación: /api/messages/{sessionId}/send
        return self.post(
            f"/api/messages/{self.session_id}/send",
            data={
                "to": to,
                "message": message,
                "type": message_type
            },
            use_session_id=False
        )

    def mark_chat_as_read(self, chat_id: str) -> Dict[str, Any]:
        """
        Marca un chat como leído.

        Args:
            chat_id: ID del chat

        Returns:
            Dict con resultado
        """
        if not self.session_id:
            frappe.throw("session_id es requerido para marcar como leído")

        # Endpoint según documentación: /api/messages/:sessionId/:chatId/read
        return self.put(
            f"/api/messages/{self.session_id}/{chat_id}/read",
            data={},
            use_session_id=False
        )
