#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API para manejar webhooks de Baileys/Inbox Hub.
Procesa eventos entrantes en tiempo real: mensajes, estados, etc.

Requisitos actuales del proveedor:
- Firma HMAC-SHA256 en `X-Webhook-Signature` (prefijo `sha256=`) calculada sobre JSON.stringify(payload).
- Cabeceras adicionales `X-Webhook-Event` y `X-Webhook-Session`.
- El tráfico se origina desde las IPs 170.83.242.18 / 170.83.242.19 (gestionado via WAF/allowlist).
"""

import frappe
import hmac
import hashlib
import json
from typing import Dict, Any
from datetime import datetime


@frappe.whitelist(allow_guest=True)
def handle_webhook():
    """
    Endpoint principal para recibir webhooks de Inbox Hub.
    Este método debe estar configurado en Inbox Hub como webhook URL.

    URL: https://tu-dominio.com/api/method/xappiens_whatsapp.api.webhook.handle_webhook
    """
    try:
        # Obtener payload crudo para validar firma (JSON.stringify original)
        raw_payload = frappe.request.get_data(as_text=True) or ""

        if not raw_payload:
            frappe.log_error("Empty webhook payload received")
            return {"success": False, "error": "Empty payload"}

        try:
            data = json.loads(raw_payload)
        except json.JSONDecodeError:
            frappe.log_error(f"Invalid JSON payload: {raw_payload}")
            return {"success": False, "error": "Invalid JSON"}

        # Validar firma del webhook (seguridad)
        signature = (
            frappe.request.headers.get("X-Webhook-Signature")
            or frappe.request.headers.get("X-Signature")
        )

        if not _verify_webhook_signature(raw_payload, signature):
            frappe.log_error("Webhook signature verification failed")
            return {"success": False, "error": "Invalid signature"}

        header_event = frappe.request.headers.get("X-Webhook-Event")
        header_session = frappe.request.headers.get("X-Webhook-Session")

        # Procesar evento
        event = header_event or data.get("event")
        event_data = data.get("data")

        # Compatibilidad: algunos emisores envían el payload directamente sin 'data'
        if not event_data and isinstance(data, dict):
            event_data = data.get("message") or data.get("payload")

        if not isinstance(event_data, dict):
            event_data = {}

        # Asegurar sessionId disponible para handlers
        resolved_session = (
            header_session
            or data.get("sessionId")
            or event_data.get("sessionId")
        )

        if resolved_session:
            event_data.setdefault("sessionId", resolved_session)
            # Mantener top-level también para trazabilidad
            data["sessionId"] = resolved_session

        if not event or not event_data:
            frappe.log_error(f"Invalid webhook data: {data}")
            return {"success": False, "error": "Invalid data"}

        # Enrutar según tipo de evento
        result = _route_webhook_event(event, event_data)

        frappe.db.commit()

        return {
            "success": True,
            "received": True,
            "processed": result,
            "event": event,
        }

    except Exception as e:
        frappe.log_error(f"Error processing webhook: {str(e)}")
        return {"success": False, "error": str(e)}


def _verify_webhook_signature(raw_payload: str, signature: str) -> bool:
    """
    Verifica la firma HMAC del webhook para seguridad.

    Args:
        raw_payload: Payload original en formato JSON (string)
        signature: Firma HMAC del header

    Returns:
        bool: True si la firma es válida
    """
    try:
        if not signature:
            return False

        settings = frappe.get_single("WhatsApp Settings")
        webhook_secret = settings.get_password("webhook_secret")

        if not webhook_secret:
            # Si no hay secret configurado, aceptar el webhook (desarrollo)
            frappe.log_error("Warning: Webhook secret not configured")
            return True

        # Calcular firma esperada
        expected_signature = hmac.new(
            webhook_secret.encode(),
            raw_payload.encode(),
            hashlib.sha256
        ).hexdigest()

        provided_signature = signature
        if "=" in signature:
            provided_signature = signature.split("=", 1)[1]

        # Comparar firmas
        return hmac.compare_digest(provided_signature, expected_signature)

    except Exception as e:
        frappe.log_error(f"Error verifying webhook signature: {str(e)}")
        return False


def _route_webhook_event(event: str, data: Dict) -> Dict[str, Any]:
    """
    Enruta el evento del webhook al handler apropiado.

    Args:
        event: Tipo de evento
        data: Datos del evento

    Returns:
        Dict con resultado del procesamiento
    """
    event_handlers = {
        "message.received": _handle_message_received,
        "message.sent": _handle_message_sent,
        "message.delivered": _handle_message_status,
        "message.read": _handle_message_status,
        "message.failed": _handle_message_status,
        "session.connected": _handle_session_status,
        "session.disconnected": _handle_session_status,
        "session.qr": _handle_session_qr,
        "contact.updated": _handle_contact_update,
        "chat.archived": _handle_chat_update,
        "chat.unarchived": _handle_chat_update
    }

    handler = event_handlers.get(event)

    if handler:
        return handler(data)
    else:
        frappe.log_error(f"Unknown webhook event: {event}")
        return {"processed": False, "error": "Unknown event"}


def _handle_message_received(data: Dict) -> Dict[str, Any]:
    """
    Procesa un mensaje recibido.

    Args:
        data: Datos del mensaje

    Returns:
        Dict con resultado
    """
    try:
        session_id = data.get("sessionId")

        message_data = data.get("message") or data.get("payload") or data

        # Buscar sesión
        session = frappe.db.get_value("WhatsApp Session", {"session_id": session_id}, "name")

        if not session:
            return {"processed": False, "error": "Session not found"}

        # Extraer datos del mensaje
        message_id = (
            message_data.get("whatsappMessageId")
            or message_data.get("messageId")
            or message_data.get("id")
        )
        chat_id = (
            message_data.get("chatId")
            or message_data.get("remoteJid")
            or message_data.get("jid")
        )
        if not chat_id:
            return {"processed": False, "error": "Chat ID missing"}

        content = (
            message_data.get("content")
            or message_data.get("body")
            or message_data.get("text")
            or message_data.get("text_content")
            or message_data.get("caption")
            or ""
        )
        from_number = (
            message_data.get("from")
            or message_data.get("sender")
            or message_data.get("participant")
            or message_data.get("author")
        )
        timestamp = message_data.get("timestamp") or data.get("timestamp")
        from_me = bool(message_data.get("fromMe"))

        # Verificar si el mensaje ya existe
        if message_id and frappe.db.exists("WhatsApp Message", {"session": session, "message_id": message_id}):
            return {"processed": True, "action": "duplicate"}

        # Buscar o crear conversación
        conversation = frappe.db.get_value("WhatsApp Conversation", {
            "session": session,
            "chat_id": chat_id
        }, "name")

        if not conversation:
            phone_number = chat_id.split('@')[0] if '@' in chat_id else chat_id

            conv_doc = frappe.get_doc({
                "doctype": "WhatsApp Conversation",
                "session": session,
                "chat_id": chat_id,
                "conversation_name": from_number or phone_number,
                "contact_name": from_number or phone_number,
                "phone_number": phone_number,
                "is_group": message_data.get("isGroup", False),
                "status": "Active"
            })
            conv_doc.insert(ignore_permissions=True)
            conversation = conv_doc.name

        # Normalizar timestamp a datetime
        if timestamp:
            try:
                if isinstance(timestamp, (int, float)):
                    ts_value = int(timestamp)
                    if ts_value > 1e12:  # milisegundos
                        timestamp = datetime.fromtimestamp(ts_value / 1000)
                    else:
                        timestamp = datetime.fromtimestamp(ts_value)
                else:
                    timestamp = datetime.fromisoformat(str(timestamp).replace('Z', '+00:00'))
            except Exception:
                timestamp = frappe.utils.now_datetime()
        else:
            timestamp = frappe.utils.now_datetime()

        if not message_id:
            message_id = frappe.generate_hash(length=20)

        if not from_number and not from_me and chat_id:
            from_number = chat_id.split('@')[0]

        message_doc = frappe.get_doc({
            "doctype": "WhatsApp Message",
            "session": session,
            "conversation": conversation,
            "message_id": message_id,
            "content": content,
            "direction": "Outgoing" if from_me else "Incoming",
            "message_type": message_data.get("type", "text"),
            "status": "Sent" if from_me else "Delivered",
            "timestamp": timestamp,
            "from_number": from_number,
            "from_me": from_me,
            "has_media": message_data.get("has_attachment", False),
            "is_read": False
        })
        message_doc.insert(ignore_permissions=True)

        # Actualizar conversación
        current_unread = frappe.db.get_value("WhatsApp Conversation", conversation, "unread_count") or 0
        new_unread_count = current_unread if from_me else current_unread + 1

        frappe.db.set_value("WhatsApp Conversation", conversation, {
            "last_message": content[:140] if content else "",
            "last_message_time": timestamp,
            "last_message_from_me": from_me,
            "unread_count": new_unread_count
        })

        payload = {
            "session": session,
            "conversation": conversation,
            "conversation_id": conversation,
            "message_id": message_doc.name,
            "message": content,
            "content": content,
            "from": from_number,
            "direction": "outgoing" if from_me else "incoming",
            "timestamp": timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp),
        }

        frappe.publish_realtime("whatsapp_message", payload, user="*")
        frappe.publish_realtime("whatsapp_message_received", payload, user="*")

        return {"processed": True, "action": "created", "message_id": message_doc.name}

    except Exception as e:
        frappe.log_error(f"Error handling message received: {str(e)}")
        return {"processed": False, "error": str(e)}


def _handle_message_sent(data: Dict) -> Dict[str, Any]:
    """
    Procesa confirmación de mensaje enviado.

    Args:
        data: Datos del mensaje

    Returns:
        Dict con resultado
    """
    try:
        message_payload = data.get("message") or data
        message_id = (
            message_payload.get("messageId")
            or message_payload.get("id")
            or data.get("messageId")
        )

        if not message_id:
            return {"processed": False, "error": "Message ID not provided"}

        # Buscar mensaje
        message = frappe.db.get_value("WhatsApp Message", {"message_id": message_id}, "name")

        if message:
            frappe.db.set_value("WhatsApp Message", message, {
                "status": "Sent",
                "sent_at": frappe.utils.now()
            })
            return {"processed": True, "action": "updated"}

        return {"processed": False, "error": "Message not found"}

    except Exception as e:
        frappe.log_error(f"Error handling message sent: {str(e)}")
        return {"processed": False, "error": str(e)}


def _handle_message_status(data: Dict) -> Dict[str, Any]:
    """
    Procesa cambio de estado de mensaje (delivered, read, failed).

    Args:
        data: Datos del estado

    Returns:
        Dict con resultado
    """
    try:
        message_id = (
            data.get("messageId")
            or data.get("id")
            or (data.get("message", {}) if isinstance(data.get("message"), dict) else {}).get("messageId")
        )
        new_status = (
            data.get("status")
            or (data.get("message", {}) if isinstance(data.get("message"), dict) else {}).get("status")
        )

        if not message_id or not new_status:
            return {"processed": False, "error": "Invalid data"}

        # Mapear estado
        status_map = {
            "delivered": "Delivered",
            "read": "Read",
            "failed": "Failed"
        }

        frappe_status = status_map.get(new_status.lower(), "Pending")

        # Buscar mensaje
        message = frappe.db.get_value("WhatsApp Message", {"message_id": message_id}, "name")

        if message:
            update_data = {"status": frappe_status}

            if frappe_status == "Read":
                update_data["is_read"] = True
                update_data["read_at"] = frappe.utils.now()

            frappe.db.set_value("WhatsApp Message", message, update_data)
            return {"processed": True, "action": "status_updated"}

        return {"processed": False, "error": "Message not found"}

    except Exception as e:
        frappe.log_error(f"Error handling message status: {str(e)}")
        return {"processed": False, "error": str(e)}


def _handle_session_status(data: Dict) -> Dict[str, Any]:
    """
    Procesa cambio de estado de sesión.
    Cuando la sesión se conecta, dispara sincronización automática.

    Args:
        data: Datos de la sesión

    Returns:
        Dict con resultado
    """
    try:
        session_id = data.get("sessionId")
        new_status = data.get("status")
        phone_number = data.get("phoneNumber")

        if not session_id:
            return {"processed": False, "error": "Session ID not provided"}

        # Buscar sesión
        session = frappe.db.get_value("WhatsApp Session", {"session_id": session_id}, "name")

        if session:
            # Mapear estado
            status_map = {
                "connected": "Connected",
                "disconnected": "Disconnected",
                "connecting": "Connecting",
                "qr_code": "QR Code Required",
                "error": "Error"
            }

            frappe_status = status_map.get(new_status.lower(), "Disconnected")
            is_connected = 1 if frappe_status == "Connected" else 0

            update_data = {
                "status": frappe_status,
                "is_connected": is_connected
            }

            if phone_number:
                update_data["phone_number"] = phone_number

            frappe.db.set_value("WhatsApp Session", session, update_data)

            # Publicar evento
            frappe.publish_realtime(
                "whatsapp_session_status",
                {
                    "session": session,
                    "status": frappe_status,
                    "connected": is_connected
                },
                user=frappe.session.user
            )

            # 🔥 SINCRONIZACIÓN AUTOMÁTICA AL CONECTAR - DESHABILITADA
            # RAZÓN: Causa conflictos de conexión múltiple con WhatsApp
            # WhatsApp detecta múltiples peticiones simultáneas como "conflict"
            # y desconecta la sesión automáticamente
            if frappe_status == "Connected":
                frappe.log_error(f"Sesión {session_id} conectada - Sincronización automática DESHABILITADA")

                # DESHABILITADO: Dispara conflictos con sincronización manual
                # frappe.enqueue(
                #     "xappiens_whatsapp.api.sync.sync_session_complete",
                #     queue="default",
                #     timeout=600,
                #     session_name=session
                # )

                frappe.publish_realtime(
                    "whatsapp_session_connected",
                    {
                        "session": session,
                        "message": "Sesión conectada - Usar botón 'Sincronizar Ahora' para importar datos"
                    },
                    user=frappe.session.user
                )

            return {"processed": True, "action": "status_updated", "auto_sync": frappe_status == "Connected"}

        return {"processed": False, "error": "Session not found"}

    except Exception as e:
        frappe.log_error(f"Error handling session status: {str(e)}")
        return {"processed": False, "error": str(e)}


def _handle_session_qr(data: Dict) -> Dict[str, Any]:
    """
    Procesa nuevo código QR de sesión.

    Args:
        data: Datos del QR

    Returns:
        Dict con resultado
    """
    try:
        session_id = data.get("sessionId")
        qr_code = data.get("qrCode")

        if not session_id or not qr_code:
            return {"processed": False, "error": "Invalid data"}

        # Buscar sesión
        session = frappe.db.get_value("WhatsApp Session", {"session_id": session_id}, "name")

        if session:
            # Publicar QR en tiempo real
            frappe.publish_realtime(
                "whatsapp_qr_code",
                {
                    "session": session,
                    "qr_code": qr_code
                },
                user=frappe.session.user
            )

            return {"processed": True, "action": "qr_published"}

        return {"processed": False, "error": "Session not found"}

    except Exception as e:
        frappe.log_error(f"Error handling session QR: {str(e)}")
        return {"processed": False, "error": str(e)}


def _handle_contact_update(data: Dict) -> Dict[str, Any]:
    """
    Procesa actualización de contacto.

    Args:
        data: Datos del contacto

    Returns:
        Dict con resultado
    """
    try:
        session_id = data.get("sessionId")
        contact_data = data.get("contact", {})

        # Buscar sesión
        session = frappe.db.get_value("WhatsApp Session", {"session_id": session_id}, "name")

        if not session:
            return {"processed": False, "error": "Session not found"}

        contact_id = contact_data.get("id")
        phone_number = contact_data.get("phone") or contact_id

        # Buscar contacto
        contact = frappe.db.get_value("WhatsApp Contact", {
            "session": session,
            "phone_number": phone_number
        }, "name")

        if contact:
            # Actualizar
            frappe.db.set_value("WhatsApp Contact", contact, {
                "contact_name": contact_data.get("name") or frappe.db.get_value("WhatsApp Contact", contact, "contact_name"),
                "img_url": contact_data.get("imgUrl"),
                "last_sync": frappe.utils.now()
            })
            return {"processed": True, "action": "updated"}

        return {"processed": True, "action": "contact_not_found"}

    except Exception as e:
        frappe.log_error(f"Error handling contact update: {str(e)}")
        return {"processed": False, "error": str(e)}


def _handle_chat_update(data: Dict) -> Dict[str, Any]:
    """
    Procesa actualización de chat (archived, unarchived, etc.).

    Args:
        data: Datos del chat

    Returns:
        Dict con resultado
    """
    try:
        session_id = data.get("sessionId")
        chat_id = data.get("chatId")
        is_archived = data.get("isArchived", False)

        # Buscar sesión
        session = frappe.db.get_value("WhatsApp Session", {"session_id": session_id}, "name")

        if not session:
            return {"processed": False, "error": "Session not found"}

        # Buscar conversación
        conversation = frappe.db.get_value("WhatsApp Conversation", {
            "session": session,
            "chat_id": chat_id
        }, "name")

        if conversation:
            frappe.db.set_value("WhatsApp Conversation", conversation, {
                "is_archived": is_archived
            })
            return {"processed": True, "action": "updated"}

        return {"processed": True, "action": "conversation_not_found"}

    except Exception as e:
        frappe.log_error(f"Error handling chat update: {str(e)}")
        return {"processed": False, "error": str(e)}
