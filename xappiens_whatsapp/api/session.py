#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API para gestión de sesiones de WhatsApp.
Conecta con el servidor externo y sincroniza con WhatsApp Session DocType.
"""

import frappe
from .base import WhatsAppAPIClient
from typing import Dict, Any, Optional
import base64


@frappe.whitelist()
def start_session(session_name: str) -> Dict[str, Any]:
    """
    Inicia una sesión de WhatsApp en el servidor externo.

    Args:
        session_name: Nombre del documento WhatsApp Session

    Returns:
        Dict con resultado de la operación
    """
    # Obtener el documento de la sesión
    session = frappe.get_doc("WhatsApp Session", session_name)

    # Crear cliente API
    client = WhatsAppAPIClient(session.session_id)

    try:
        # Llamar al endpoint de inicio de sesión
        response = client.get("/session/start/{sessionId}")

        if response.get("success"):
            # Actualizar estado en Frappe
            session.status = "Connecting"
            session.is_connected = 0
            session.last_activity = frappe.utils.now()
            session.save(ignore_permissions=True)

            frappe.db.commit()

            return {
                "success": True,
                "message": "Sesión iniciada. Escanea el código QR.",
                "session_id": session.session_id
            }
        else:
            frappe.throw(f"Error al iniciar sesión: {response.get('message', 'Error desconocido')}")

    except Exception as e:
        # Registrar error en Activity Log
        _log_activity(
            session=session.name,
            event_type="session_start_failed",
            status="Failed",
            error_message=str(e)
        )

        session.status = "Failed"
        session.error_message = str(e)
        session.save(ignore_permissions=True)
        frappe.db.commit()

        frappe.throw(f"Error al iniciar sesión: {str(e)}")


@frappe.whitelist()
def get_session_status(session_name: str) -> Dict[str, Any]:
    """
    Obtiene el estado actual de una sesión desde el servidor.

    Args:
        session_name: Nombre del documento WhatsApp Session

    Returns:
        Dict con estado de la sesión
    """
    session = frappe.get_doc("WhatsApp Session", session_name)
    client = WhatsAppAPIClient(session.session_id)

    try:
        # Obtener estado desde el servidor
        response = client.get("/session/status/{sessionId}")

        if response.get("success"):
            state = response.get("state", "DISCONNECTED")

            # Mapear estado del servidor a estado de Frappe
            status_map = {
                "CONNECTED": "Connected",
                "CONNECTING": "Connecting",
                "DISCONNECTED": "Disconnected",
                "CONFLICT": "Conflict",
                "TIMEOUT": "Timeout"
            }

            frappe_status = status_map.get(state, "Disconnected")
            is_connected = state == "CONNECTED"

            # Actualizar en Frappe
            session.status = frappe_status
            session.is_connected = 1 if is_connected else 0
            session.last_activity = frappe.utils.now()

            # Si está conectado, obtener el número de teléfono
            if is_connected and not session.phone_number:
                try:
                    phone_response = client.get("/session/phone/{sessionId}")
                    if phone_response.get("success"):
                        session.phone_number = phone_response.get("phoneNumber")
                except:
                    pass

            session.save(ignore_permissions=True)
            frappe.db.commit()

            return {
                "success": True,
                "status": frappe_status,
                "is_connected": is_connected,
                "state": state,
                "phone_number": session.phone_number
            }
        else:
            return {
                "success": False,
                "message": response.get("message", "Error al obtener estado")
            }

    except Exception as e:
        _log_activity(
            session=session.name,
            event_type="status_check_failed",
            status="Failed",
            error_message=str(e)
        )

        frappe.log_error(f"Error al obtener estado de sesión {session.session_id}: {str(e)}")

        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def get_qr_code(session_name: str, as_image: bool = True) -> Dict[str, Any]:
    """
    Obtiene el código QR para conectar la sesión.

    Args:
        session_name: Nombre del documento WhatsApp Session
        as_image: Si True, devuelve imagen PNG en base64

    Returns:
        Dict con código QR
    """
    session = frappe.get_doc("WhatsApp Session", session_name)
    client = WhatsAppAPIClient(session.session_id)

    try:
        if as_image:
            # Obtener QR como imagen PNG
            response = requests.get(
                f"{client.base_url}/session/qr/{session.session_id}/image",
                headers=client._get_headers(),
                timeout=client.timeout
            )

            if response.status_code == 200:
                # Convertir a base64
                qr_base64 = base64.b64encode(response.content).decode('utf-8')

                # Guardar en el documento
                session.qr_code = f"data:image/png;base64,{qr_base64}"
                session.qr_generated_at = frappe.utils.now()
                session.save(ignore_permissions=True)
                frappe.db.commit()

                return {
                    "success": True,
                    "qr_code": session.qr_code,
                    "message": "Código QR obtenido exitosamente"
                }
            else:
                frappe.throw(f"Error al obtener QR: {response.status_code}")
        else:
            # Obtener QR como texto
            response = client.get("/session/qr/{sessionId}")

            if response.get("success"):
                qr_text = response.get("qr")

                session.qr_code = qr_text
                session.qr_generated_at = frappe.utils.now()
                session.save(ignore_permissions=True)
                frappe.db.commit()

                return {
                    "success": True,
                    "qr_code": qr_text,
                    "message": "Código QR obtenido exitosamente"
                }
            else:
                frappe.throw("Error al obtener código QR")

    except Exception as e:
        _log_activity(
            session=session.name,
            event_type="qr_generation_failed",
            status="Failed",
            error_message=str(e)
        )

        frappe.log_error(f"Error al obtener QR para sesión {session.session_id}: {str(e)}")
        frappe.throw(f"Error al obtener código QR: {str(e)}")


@frappe.whitelist()
def disconnect_session(session_name: str) -> Dict[str, Any]:
    """
    Desconecta una sesión de WhatsApp.

    Args:
        session_name: Nombre del documento WhatsApp Session

    Returns:
        Dict con resultado
    """
    session = frappe.get_doc("WhatsApp Session", session_name)
    client = WhatsAppAPIClient(session.session_id)

    try:
        response = client.post("/session/disconnect/{sessionId}")

        if response.get("success"):
            # Actualizar en Frappe
            session.status = "Disconnected"
            session.is_connected = 0
            session.last_activity = frappe.utils.now()
            session.save(ignore_permissions=True)
            frappe.db.commit()

            _log_activity(
                session=session.name,
                event_type="session_disconnected",
                status="Success"
            )

            return {
                "success": True,
                "message": "Sesión desconectada exitosamente"
            }
        else:
            frappe.throw("Error al desconectar sesión")

    except Exception as e:
        _log_activity(
            session=session.name,
            event_type="disconnect_failed",
            status="Failed",
            error_message=str(e)
        )

        frappe.throw(f"Error al desconectar sesión: {str(e)}")


@frappe.whitelist()
def reconnect_session(session_name: str) -> Dict[str, Any]:
    """
    Reconecta una sesión de WhatsApp.

    Args:
        session_name: Nombre del documento WhatsApp Session

    Returns:
        Dict con resultado
    """
    session = frappe.get_doc("WhatsApp Session", session_name)
    client = WhatsAppAPIClient(session.session_id)

    try:
        response = client.post("/session/reconnect/{sessionId}")

        if response.get("success"):
            session.status = "Connecting"
            session.last_activity = frappe.utils.now()
            session.save(ignore_permissions=True)
            frappe.db.commit()

            _log_activity(
                session=session.name,
                event_type="session_reconnect",
                status="Success"
            )

            return {
                "success": True,
                "message": "Sesión reconectándose..."
            }
        else:
            frappe.throw("Error al reconectar sesión")

    except Exception as e:
        _log_activity(
            session=session.name,
            event_type="reconnect_failed",
            status="Failed",
            error_message=str(e)
        )

        frappe.throw(f"Error al reconectar sesión: {str(e)}")


@frappe.whitelist()
def update_session_stats(session_name: str) -> Dict[str, Any]:
    """
    Actualiza las estadísticas de una sesión desde el servidor.

    Args:
        session_name: Nombre del documento WhatsApp Session

    Returns:
        Dict con estadísticas actualizadas
    """
    session = frappe.get_doc("WhatsApp Session", session_name)
    client = WhatsAppAPIClient(session.session_id)

    try:
        # Obtener chats y contactos
        chats_response = client.get("/client/getChats/{sessionId}", params={"limit": 9999})
        contacts_response = client.get("/client/getContacts/{sessionId}", params={"limit": 9999})

        if chats_response.get("success") and contacts_response.get("success"):
            chats = chats_response.get("chats", [])
            contacts = contacts_response.get("contacts", [])

            # Contar mensajes no leídos
            total_unread = sum(chat.get("unreadCount", 0) for chat in chats)

            # Actualizar estadísticas
            session.total_chats = len(chats)
            session.total_contacts = len(contacts)
            session.unread_messages = total_unread
            session.last_sync = frappe.utils.now()
            session.save(ignore_permissions=True)
            frappe.db.commit()

            return {
                "success": True,
                "stats": {
                    "total_chats": len(chats),
                    "total_contacts": len(contacts),
                    "unread_messages": total_unread
                }
            }
        else:
            frappe.throw("Error al obtener estadísticas")

    except Exception as e:
        frappe.log_error(f"Error al actualizar estadísticas de sesión {session.session_id}: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }


def _log_activity(session: str, event_type: str, status: str, error_message: str = None):
    """
    Registra una actividad en WhatsApp Activity Log.

    Args:
        session: Nombre del documento WhatsApp Session
        event_type: Tipo de evento
        status: Estado (Success/Failed)
        error_message: Mensaje de error (opcional)
    """
    try:
        activity_log = frappe.get_doc({
            "doctype": "WhatsApp Activity Log",
            "session": session,
            "event_type": event_type,
            "status": status,
            "timestamp": frappe.utils.now(),
            "error_message": error_message,
            "user": frappe.session.user
        })
        activity_log.insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(f"Error al registrar actividad: {str(e)}")

