#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proxy para peticiones directas a la API de Baileys desde el frontend.
Evita problemas de CORS al hacer las peticiones desde el servidor.
"""

import frappe
from .base import WhatsAppAPIClient


@frappe.whitelist()
def proxy_request(endpoint: str, method: str = "GET", data: dict = None):
    """
    Proxy genérico para hacer peticiones a la API de Baileys.

    Args:
        endpoint: Endpoint de la API (ej: /api/messages/session_id/chats)
        method: Método HTTP (GET, POST, etc.)
        data: Datos para enviar en el body (solo para POST)

    Returns:
        Respuesta de la API de Baileys
    """
    try:
        # Crear cliente de la API
        client = WhatsAppAPIClient()

        # Hacer la petición según el método
        if method.upper() == "GET":
            response = client.get(endpoint, params=data, use_session_id=False)
        elif method.upper() == "POST":
            response = client.post(endpoint, data=data, use_session_id=False)
        else:
            return {
                "success": False,
                "error": f"Método HTTP no soportado: {method}"
            }

        return {
            "success": True,
            "data": response.get("data", response),
            "message": response.get("message", "Petición exitosa")
        }

    except Exception as e:
        # Truncar el mensaje de error para evitar CharacterLengthExceededError
        error_msg = str(e)[:100] + "..." if len(str(e)) > 100 else str(e)
        frappe.log_error(f"Error en proxy_request: {error_msg}", "Baileys Proxy Error")
        return {
            "success": False,
            "error": error_msg
        }


@frappe.whitelist(allow_guest=True)
def get_conversations():
    """
    Obtiene conversaciones directamente desde Baileys API (optimizado).
    """
    try:
        # Usar session_id específico para grupo_atu_mgt6f1zb_jqxglg
        client = WhatsAppAPIClient(session_id="grupo_atu_mgt6f1zb_jqxglg")

        # Optimizar timeouts para conversaciones
        original_timeout = client.timeout
        original_retry = client.retry_attempts

        # Configuración optimizada para conversaciones
        client.timeout = 8  # Reducir de 30 a 8 segundos
        client.retry_attempts = 2  # Reducir de 3 a 2 intentos

        try:
            # Usar el método específico para obtener chats (optimizado: menos conversaciones iniciales)
            response = client.get_session_chats(page=1, limit=20)

            return {
                "success": True,
                "data": response
            }
        finally:
            # Restaurar configuración original
            client.timeout = original_timeout
            client.retry_attempts = original_retry

    except Exception as e:
        # Truncar el mensaje de error para evitar CharacterLengthExceededError
        error_msg = str(e)[:100] + "..." if len(str(e)) > 100 else str(e)
        frappe.log_error(f"Error getting conversations: {error_msg}", "Baileys Proxy Error")
        return {
            "success": False,
            "error": error_msg
        }


@frappe.whitelist()
def send_message(to: str, message: str, message_type: str = "text"):
    """
    Envía mensaje directamente a través de Baileys API.

    Args:
        to: Número de teléfono destino
        message: Contenido del mensaje
        message_type: Tipo de mensaje (text, image, etc.)

    Returns:
        Respuesta del envío
    """
    try:
        # Usar session_id específico para grupo_atu_mgt6f1zb_jqxglg
        client = WhatsAppAPIClient(session_id="grupo_atu_mgt6f1zb_jqxglg")

        # Usar el método de envío de mensajes
        response = client.send_message(to=to, message=message, message_type=message_type)

        return {
            "success": True,
            "data": response
        }

    except Exception as e:
        # Truncar el mensaje de error para evitar CharacterLengthExceededError
        error_msg = str(e)[:100] + "..." if len(str(e)) > 100 else str(e)
        frappe.log_error(f"Error sending message: {error_msg}", "Baileys Proxy Error")
        return {
            "success": False,
            "error": error_msg
        }


@frappe.whitelist(allow_guest=True)
def get_messages(chat_id: str, page: int = 1, limit: int = 50):
    """
    Obtiene mensajes de un chat específico desde Baileys API.

    Args:
        chat_id: ID del chat
        page: Página
        limit: Límite de mensajes

    Returns:
        Lista de mensajes
    """
    try:
        # Usar session_id específico para grupo_atu_mgt6f1zb_jqxglg
        client = WhatsAppAPIClient(session_id="grupo_atu_mgt6f1zb_jqxglg")

        # Usar el método específico para obtener mensajes
        response = client.get_chat_messages(chat_id=chat_id, page=page, limit=limit)

        return {
            "success": True,
            "data": response
        }

    except Exception as e:
        # Truncar el mensaje de error para evitar CharacterLengthExceededError
        error_msg = str(e)[:100] + "..." if len(str(e)) > 100 else str(e)
        frappe.log_error(f"Error getting messages: {error_msg}", "Baileys Proxy Error")
        return {
            "success": False,
            "error": error_msg
        }


@frappe.whitelist()
def get_session_status():
    """
    Obtiene el estado de la sesión directamente desde Baileys API.

    Returns:
        Estado de la sesión
    """
    try:
        # Usar session_id específico para grupo_atu_mgt6f1zb_jqxglg
        client = WhatsAppAPIClient(session_id="grupo_atu_mgt6f1zb_jqxglg")

        # Obtener todas las sesiones y encontrar la activa
        sessions_response = client.get_sessions()

        if sessions_response.get("success") and sessions_response.get("data", {}).get("sessions"):
            sessions = sessions_response["data"]["sessions"]

            # Buscar la sesión grupo_atu_mgt6f1zb_jqxglg
            active_session = None
            for session in sessions:
                if session.get("sessionId") == "grupo_atu_mgt6f1zb_jqxglg":
                    active_session = session
                    break

            if active_session:
                return {
                    "success": True,
                    "data": {
                        "session_status": active_session.get("status", "disconnected").upper(),
                        "is_connected": active_session.get("status") == "connected",
                        "doc_name": "ha0rin9kbi",  # Nombre del documento en Frappe
                        "session_id": active_session.get("sessionId"),
                        "phone_number": active_session.get("phoneNumber"),
                        "last_activity": active_session.get("lastActivity"),
                        "status": active_session.get("status")
                    }
                }
            else:
                return {
                    "success": True,
                    "data": {
                        "session_status": "DISCONNECTED",
                        "is_connected": False,
                        "doc_name": "ha0rin9kbi",
                        "session_id": "grupo_atu_mgt6f1zb_jqxglg",
                        "phone_number": "34674618182",
                        "status": "disconnected"
                    }
                }
        else:
            return {
                "success": False,
                "error": "No se pudieron obtener las sesiones"
            }

    except Exception as e:
        # Truncar el mensaje de error para evitar CharacterLengthExceededError
        error_msg = str(e)[:100] + "..." if len(str(e)) > 100 else str(e)
        frappe.log_error(f"Error getting session status: {error_msg}", "Baileys Proxy Error")
        return {
            "success": False,
            "error": error_msg
        }

@frappe.whitelist(allow_guest=True)
def poll_for_updates(last_check_timestamp: str = None):
    """
    Simula SSE mediante polling inteligente.
    Obtiene nuevos mensajes y cambios de estado desde el último check.
    """
    try:
        client = WhatsAppAPIClient(session_id="grupo_atu_mgt6f1zb_jqxglg")
        events = []

        # Convertir timestamp si se proporciona
        last_check = None
        if last_check_timestamp:
            try:
                from datetime import datetime
                last_check = datetime.fromisoformat(last_check_timestamp.replace('Z', '+00:00'))
            except:
                pass

        # Obtener mensajes recientes de todos los chats activos
        try:
            chats_response = client.get_session_chats(page=1, limit=10)
            if chats_response.get("success") and chats_response.get("data", {}).get("data", {}).get("chats"):
                chats = chats_response["data"]["data"]["chats"]

                for chat in chats[:3]:  # Solo los 3 chats más recientes para eficiencia
                    chat_id = chat.get("jid") or chat.get("chatId")
                    if chat_id:
                        try:
                            messages_response = client.get_chat_messages(chat_id=chat_id, page=1, limit=5)
                            if messages_response.get("success") and messages_response.get("data", {}).get("data", {}).get("messages"):
                                messages = messages_response["data"]["data"]["messages"]

                                for msg in messages:
                                    # Verificar si el mensaje es más reciente que el último check
                                    msg_timestamp = None
                                    try:
                                        if msg.get("timestamp"):
                                            if isinstance(msg["timestamp"], str) and 'T' in msg["timestamp"]:
                                                msg_timestamp = datetime.fromisoformat(msg["timestamp"].replace('Z', '+00:00'))
                                            else:
                                                # Timestamp Unix
                                                ts = int(msg["timestamp"])
                                                if ts < 1e12:  # Segundos
                                                    ts *= 1000
                                                msg_timestamp = datetime.fromtimestamp(ts / 1000)
                                    except:
                                        continue

                                    # Si es más reciente que el último check, agregarlo como evento
                                    if not last_check or (msg_timestamp and msg_timestamp > last_check):
                                        event = {
                                            "event": "message.new",
                                            "sessionId": "grupo_atu_mgt6f1zb_jqxglg",
                                            "timestamp": msg.get("timestamp"),
                                            "data": {
                                                "id": msg.get("id"),
                                                "chatId": chat_id,
                                                "fromMe": msg.get("fromMe", False),
                                                "body": msg.get("body", ""),
                                                "type": msg.get("type", "text"),
                                                "timestamp": msg.get("timestamp"),
                                                "from": msg.get("from"),
                                                "to": msg.get("to"),
                                                "whatsappMessageId": msg.get("id")
                                            }
                                        }
                                        events.append(event)
                        except Exception as msg_error:
                            continue
        except Exception as chats_error:
            pass

        # Verificar cambios en el estado de sesión
        try:
            session_status = get_session_status()
            if session_status.get("success"):
                status_data = session_status["data"]
                # Agregar evento de estado si es necesario
                if status_data.get("session_status") == "CONNECTED":
                    events.append({
                        "event": "session.status",
                        "sessionId": "grupo_atu_mgt6f1zb_jqxglg",
                        "timestamp": datetime.now().isoformat(),
                        "data": {
                            "status": "connected",
                            "sessionId": "grupo_atu_mgt6f1zb_jqxglg"
                        }
                    })
        except Exception as status_error:
            pass

        return {
            "success": True,
            "data": {
                "events": events,
                "timestamp": datetime.now().isoformat(),
                "has_updates": len(events) > 0
            }
        }

    except Exception as e:
        # Truncar el mensaje de error para evitar CharacterLengthExceededError
        error_msg = str(e)[:100] + "..." if len(str(e)) > 100 else str(e)
        frappe.log_error(f"Error polling for updates: {error_msg}", "Baileys Proxy Error")
        return {
            "success": False,
            "error": error_msg
        }
