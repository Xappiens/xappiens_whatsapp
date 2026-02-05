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

        # Verificar si es una reacción ANTES de enrutar
        # Las reacciones pueden venir en data.message.reactionMessage o event_data.reactionMessage
        reaction_message = (
            event_data.get("reactionMessage") or
            (data.get("message") or {}).get("reactionMessage") or
            data.get("reactionMessage")
        )

        if reaction_message:
            # Si es una reacción, procesarla directamente
            resolved_session = (
                header_session
                or data.get("sessionId")
                or event_data.get("sessionId")
            )
            if resolved_session:
                event_data.setdefault("sessionId", resolved_session)
                data["sessionId"] = resolved_session
            return _handle_reaction_received(event_data if event_data.get("sessionId") else data, resolved_session or data.get("sessionId"))

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

    Formato esperado de Baileys:
    {
        "event": "message.received",
        "data": {
            "sessionId": "grupo_atu_mhomrgbz_4wk5bw",
            "session_db_id": 123,
            "message": {
                "whatsappMessageId": "3A1FAB304FEA0BE9EC18",
                "content": "Hola61",
                "chatId": "34657032985@s.whatsapp.net",
                "from": "34657032985@s.whatsapp.net",
                "to": "34671499087",
                "timestamp": 1762518118,
                "type": "text"
            }
        }
    }

    Args:
        data: Datos del mensaje (ya es data.data del webhook original)

    Returns:
        Dict con resultado
    """
    try:
        # Log del payload recibido para debugging
        frappe.log_error(f"📨 Webhook recibido - data completo: {frappe.as_json(data)}", "WhatsApp Webhook Debug")

        session_id = data.get("sessionId")

        # Verificar si es una reacción antes de procesar como mensaje normal
        # Las reacciones pueden venir en diferentes formatos según el ejemplo del usuario:
        # Formato real: data.message.reactionMessage (dentro del objeto message)
        # También puede venir como: data.reactionMessage
        reaction_message = None

        # Primero buscar en data.message.reactionMessage (formato más común)
        message_obj = data.get("message")
        if isinstance(message_obj, dict):
            reaction_message = message_obj.get("reactionMessage")

        # Si no está ahí, buscar directamente en data
        if not reaction_message:
            reaction_message = data.get("reactionMessage")

        # Si aún no lo encontramos, buscar en message_data extraído
        if not reaction_message:
            message_data_temp = data.get("message") or data.get("payload") or data
            if isinstance(message_data_temp, dict):
                reaction_message = message_data_temp.get("reactionMessage")

        if reaction_message:
            frappe.log_error(f"🎯 Reacción detectada en _handle_message_received: {frappe.as_json(reaction_message)}", "WhatsApp Webhook Reaction Detection")
            return _handle_reaction_received(data, session_id)

        # Extraer message_data - el formato nuevo tiene data.message
        message_data = data.get("message") or data.get("payload") or data

        if not message_data:
            frappe.log_error(f"⚠️ No se encontró message_data en el payload: {frappe.as_json(data)}", "WhatsApp Webhook Error")
            return {"processed": False, "error": "Message data missing"}

        # Buscar sesión por session_id
        session = frappe.db.get_value("WhatsApp Session", {"session_id": session_id}, "name")

        if not session:
            frappe.log_error(f"⚠️ Sesión no encontrada para session_id: {session_id}", "WhatsApp Webhook Error")
            return {"processed": False, "error": f"Session not found: {session_id}"}

        # Extraer datos del mensaje según formato de Baileys
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
            frappe.log_error(f"⚠️ Chat ID faltante en mensaje: {frappe.as_json(message_data)}", "WhatsApp Webhook Error")
            return {"processed": False, "error": "Chat ID missing"}

        content = (
            message_data.get("content")
            or message_data.get("body")
            or message_data.get("text")
            or message_data.get("text_content")
            or message_data.get("caption")
            or ""
        )

        # Extraer número del remitente (from)
        from_number_raw = (
            message_data.get("from")
            or message_data.get("sender")
            or message_data.get("participant")
            or message_data.get("author")
        )

        # Normalizar from_number: extraer solo el número sin @s.whatsapp.net
        if from_number_raw:
            from_number = from_number_raw.replace("@s.whatsapp.net", "").replace("@c.us", "").replace("+", "").strip()
        else:
            # Si no hay from, usar chatId
            from_number = chat_id.replace("@s.whatsapp.net", "").replace("@c.us", "").replace("+", "").strip()

        # Extraer número de destino (to) - este es el número de la sesión que recibe
        to_number_raw = message_data.get("to")
        to_number = None
        if to_number_raw:
            to_number = to_number_raw.replace("+", "").replace(" ", "").strip()

        timestamp = message_data.get("timestamp") or data.get("timestamp")

        # Detectar from_me: comparar con número de sesión
        # Si el mensaje viene de la sesión misma, es saliente (from_me = True)
        # Si viene de otro número, es entrante (from_me = False)
        from_me = bool(message_data.get("fromMe"))
        if not from_me and to_number:
            # Comparar el número de destino (to) con el número de la sesión
            session_doc = frappe.get_doc("WhatsApp Session", session)
            session_phone = session_doc.phone_number or ""
            # Normalizar números para comparar
            session_phone_normalized = session_phone.replace("+", "").replace(" ", "").strip()
            # Si el mensaje va "to" la sesión, entonces from != session, así que from_me = False
            # Si el mensaje viene "from" la sesión, entonces from == session, así que from_me = True
            if session_phone_normalized and from_number:
                # Si el remitente es la sesión misma, es saliente
                from_me = session_phone_normalized == from_number

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

        # Procesar archivos multimedia si los hay
        if message_data.get("has_attachment") or message_data.get("hasMedia"):
            try:
                from .messages import process_media_items

                # Extraer información de medios del webhook
                media_list = []

                # Buscar datos de media en diferentes formatos
                media_info = (
                    message_data.get("media") or
                    message_data.get("attachment") or
                    message_data.get("mediaData") or
                    {}
                )

                if media_info:
                    media_item = {
                        "media_type": _get_media_type_from_message_type(message_data.get("type", "document")),
                        "filename": media_info.get("filename") or f"media_{message_id}",
                        "filesize": media_info.get("filesize") or media_info.get("size"),
                        "mimetype": media_info.get("mimetype") or media_info.get("mimeType"),
                        "url": media_info.get("url") or media_info.get("media_url"),
                        "remote_media_id": media_info.get("mediaKey") or media_info.get("id"),
                        "media_hash": media_info.get("fileSha256") or media_info.get("hash")
                    }
                    media_list.append(media_item)

                if media_list:
                    process_media_items(message_doc, media_list)

                    # Programar descarga automática en background
                    frappe.enqueue(
                        "xappiens_whatsapp.api.media.download_media_from_message",
                        session=session,
                        message=message_doc.name,
                        queue="default",
                        timeout=300
                    )

            except Exception as e:
                frappe.log_error(f"Error processing media in webhook: {str(e)}", "WhatsApp Webhook Media")

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

        # Obtener número de teléfono normalizado para el frontend
        # Para mensajes entrantes, el phone_number es el remitente (from)
        # Para mensajes salientes, el phone_number es el destinatario (to)
        conversation_doc = frappe.get_doc("WhatsApp Conversation", conversation)
        phone_number_normalized = conversation_doc.phone_number or from_number

        # El to_number ya lo tenemos del message_data
        # Si no está disponible, usar el número de la sesión para mensajes entrantes
        if not to_number:
            if from_me:
                # Mensaje saliente: el destino es el chat_id (remitente del mensaje entrante)
                to_number = chat_id.split('@')[0] if '@' in chat_id else chat_id
            else:
                # Mensaje entrante: el destino es el número de la sesión
                session_doc = frappe.get_doc("WhatsApp Session", session)
                to_number = session_doc.phone_number or ""
                if to_number:
                    to_number = to_number.replace("+", "").replace(" ", "").strip()

        # Preparar información de media para el payload
        media_payload = None
        if message_data.get("has_attachment") or message_data.get("hasMedia"):
            media_info = (
                message_data.get("media") or
                message_data.get("attachment") or
                message_data.get("mediaData") or
                {}
            )
            if media_info:
                media_payload = {
                    "filename": media_info.get("filename"),
                    "filesize": media_info.get("filesize") or media_info.get("size"),
                    "mimetype": media_info.get("mimetype") or media_info.get("mimeType"),
                    "url": media_info.get("url") or media_info.get("media_url"),
                    "media_type": _get_media_type_from_message_type(message_data.get("type", "document"))
                }

        # Preparar payload para tiempo real - formato optimizado para el frontend
        payload = {
            "session": session,
            "session_id": session_id,  # session_id string de Baileys
            "conversation": conversation,
            "conversation_id": conversation,
            "message_id": message_doc.name,  # ID del documento en Frappe
            "whatsapp_message_id": message_id,  # ID de WhatsApp (whatsappMessageId)
            "message": content,
            "content": content,
            "from": from_number,  # Número del remitente normalizado
            "from_number": from_number,  # Alias para compatibilidad
            "to": to_number,  # Número de destino (sesión para entrantes)
            "phone_number": phone_number_normalized,  # Número normalizado para identificar contacto en frontend
            "chat_id": chat_id,  # Chat ID completo con @s.whatsapp.net
            "direction": "outgoing" if from_me else "incoming",  # Dirección del mensaje
            "timestamp": timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp),
            "message_type": message_data.get("type", "text"),
            "has_media": message_data.get("has_attachment", False) or message_data.get("hasMedia", False),
            "status": "Sent" if from_me else "Delivered",
            "media": media_payload  # Información de media si existe
        }

        # Log del payload que se va a publicar
        frappe.log_error(f"📤 Publicando evento realtime - payload: {frappe.as_json(payload)}", "WhatsApp Webhook Realtime")

        # Publicar eventos realtime para que el frontend los reciba
        # Cuando no se especifica user ni room, Frappe usa get_site_room() que es "all"
        # Los System Users se unen automáticamente al room "all" al conectarse
        try:
            # Publicar sin user ni room para que vaya a todos los usuarios del sitio
            frappe.publish_realtime("whatsapp_message", payload)
            frappe.publish_realtime("whatsapp_message_received", payload)

            frappe.log_error(f"✅ Eventos publicados correctamente", "WhatsApp Webhook Realtime")
        except Exception as e:
            frappe.log_error(f"Error publicando eventos realtime: {str(e)}", "WhatsApp Webhook Realtime Error")
            import traceback
            frappe.log_error(f"Traceback: {traceback.format_exc()}", "WhatsApp Webhook Realtime Error")

        frappe.log_error(f"✅ Mensaje procesado y publicado en tiempo real - Message ID: {message_doc.name}, From: {from_number}, To: {to_number}", "WhatsApp Webhook Success")

        return {"processed": True, "action": "created", "message_id": message_doc.name}

    except Exception as e:
        frappe.log_error(f"Error handling message received: {str(e)}")
        return {"processed": False, "error": str(e)}


def _handle_reaction_received(data: Dict, session_id: str) -> Dict[str, Any]:
    """
    Procesa una reacción recibida a un mensaje existente.

    Formato esperado de Baileys:
    {
        "event": "message.received",
        "data": {
            "sessionId": "grupo_atu_mhomrgbz_4wk5bw",
            "reactionMessage": {
                "key": {
                    "remoteJid": "34657032985@s.whatsapp.net",
                    "fromMe": false,
                    "id": "3AA45481DBB4FC7B4CFC"  // ID del mensaje original
                },
                "text": "👍",  // Emoji de la reacción
                "senderTimestampMs": "1762518864027"
            }
        }
    }

    Args:
        data: Datos del webhook completo
        session_id: ID de la sesión

    Returns:
        Dict con resultado
    """
    try:
        frappe.log_error(f"🎯 Reacción recibida - data completo: {frappe.as_json(data)}", "WhatsApp Webhook Reaction")

        # Extraer reactionMessage del payload
        # Puede venir en diferentes ubicaciones:
        # 1. data.reactionMessage
        # 2. data.message.reactionMessage (formato más común según el ejemplo del usuario)
        reaction_message = (
            data.get("reactionMessage") or
            (data.get("message") or {}).get("reactionMessage")
        )

        # Si aún no lo encontramos, intentar extraer message_data y buscar ahí
        if not reaction_message:
            message_data = data.get("message") or data.get("payload") or data
            if isinstance(message_data, dict):
                reaction_message = message_data.get("reactionMessage")

        if not reaction_message:
            frappe.log_error(f"⚠️ No se encontró reactionMessage en el payload: {frappe.as_json(data)}", "WhatsApp Webhook Reaction Error")
            return {"processed": False, "error": "Reaction message data missing"}

        # Extraer datos de la reacción
        reaction_key = reaction_message.get("key", {})
        original_message_id = reaction_key.get("id")
        reaction_emoji = reaction_message.get("text") or reaction_message.get("reaction")
        sender_timestamp_ms = reaction_message.get("senderTimestampMs")
        from_me = bool(reaction_key.get("fromMe", False))
        remote_jid = reaction_key.get("remoteJid", "")

        if not original_message_id:
            frappe.log_error(f"⚠️ ID del mensaje original faltante en reacción: {frappe.as_json(reaction_message)}", "WhatsApp Webhook Reaction Error")
            return {"processed": False, "error": "Original message ID missing"}

        if not reaction_emoji:
            frappe.log_error(f"⚠️ Emoji de reacción faltante: {frappe.as_json(reaction_message)}", "WhatsApp Webhook Reaction Error")
            return {"processed": False, "error": "Reaction emoji missing"}

        # Buscar sesión
        session = frappe.db.get_value("WhatsApp Session", {"session_id": session_id}, "name")
        if not session:
            frappe.log_error(f"⚠️ Sesión no encontrada para session_id: {session_id}", "WhatsApp Webhook Reaction Error")
            return {"processed": False, "error": f"Session not found: {session_id}"}

        # Buscar el mensaje original por message_id
        original_message = frappe.db.get_value("WhatsApp Message", {
            "session": session,
            "message_id": original_message_id
        }, "name")

        if not original_message:
            frappe.log_error(f"⚠️ Mensaje original no encontrado para message_id: {original_message_id}", "WhatsApp Webhook Reaction Error")
            return {"processed": False, "error": f"Original message not found: {original_message_id}"}

        # Obtener el documento del mensaje original
        message_doc = frappe.get_doc("WhatsApp Message", original_message)

        # Normalizar número del remitente de la reacción
        reacted_by_number = remote_jid.replace("@s.whatsapp.net", "").replace("@c.us", "").replace("+", "").strip()

        # Si from_me es True, obtener el número de la sesión
        if from_me:
            session_doc = frappe.get_doc("WhatsApp Session", session)
            reacted_by_number = session_doc.phone_number or ""
            if reacted_by_number:
                reacted_by_number = reacted_by_number.replace("+", "").replace(" ", "").strip()

        # Normalizar timestamp
        if sender_timestamp_ms:
            try:
                ts_value = int(sender_timestamp_ms)
                if ts_value > 1e12:  # milisegundos
                    reacted_at = datetime.fromtimestamp(ts_value / 1000)
                else:
                    reacted_at = datetime.fromtimestamp(ts_value)
            except Exception:
                reacted_at = frappe.utils.now_datetime()
        else:
            reacted_at = frappe.utils.now_datetime()

        # Buscar si ya existe una reacción de este usuario para este mensaje
        existing_reaction = None
        if message_doc.reactions:
            for reaction in message_doc.reactions:
                if reaction.reacted_by_number == reacted_by_number:
                    existing_reaction = reaction
                    break

        # Si existe, actualizar; si no, crear nueva
        if existing_reaction:
            # Si el emoji está vacío o es null, eliminar la reacción
            if not reaction_emoji or reaction_emoji.strip() == "":
                message_doc.remove(existing_reaction)
                frappe.log_error(f"🗑️ Reacción eliminada por usuario {reacted_by_number} del mensaje {original_message}", "WhatsApp Webhook Reaction")
            else:
                existing_reaction.reaction_emoji = reaction_emoji
                existing_reaction.reacted_at = reacted_at
                existing_reaction.is_from_me = from_me
                frappe.log_error(f"🔄 Reacción actualizada por usuario {reacted_by_number}: {reaction_emoji}", "WhatsApp Webhook Reaction")
        else:
            # Solo crear si hay emoji
            if reaction_emoji and reaction_emoji.strip() != "":
                # Buscar nombre del contacto si existe
                reacted_by_name = None
                if reacted_by_number:
                    contact = frappe.db.get_value("WhatsApp Contact", {
                        "session": session,
                        "phone_number": reacted_by_number
                    }, "contact_name")
                    reacted_by_name = contact

                message_doc.append("reactions", {
                    "reaction_emoji": reaction_emoji,
                    "reacted_by_number": reacted_by_number,
                    "reacted_by_name": reacted_by_name,
                    "reacted_at": reacted_at,
                    "is_from_me": from_me
                })
                frappe.log_error(f"➕ Nueva reacción agregada por usuario {reacted_by_number}: {reaction_emoji}", "WhatsApp Webhook Reaction")

        # Actualizar has_reaction si hay reacciones
        message_doc.has_reaction = 1 if message_doc.reactions else 0
        if message_doc.reactions and len(message_doc.reactions) > 0:
            # Mantener compatibilidad con campos antiguos (última reacción)
            last_reaction = message_doc.reactions[-1]
            message_doc.reaction = last_reaction.reaction_emoji
            message_doc.reacted_at = last_reaction.reacted_at

        message_doc.save(ignore_permissions=True)

        # Obtener conversación para el payload
        conversation = message_doc.conversation

        # Preparar payload para tiempo real
        reactions_list = []
        if message_doc.reactions:
            for reaction in message_doc.reactions:
                reactions_list.append({
                    "emoji": reaction.reaction_emoji,
                    "reacted_by_number": reaction.reacted_by_number,
                    "reacted_by_name": reaction.reacted_by_name,
                    "reacted_at": reaction.reacted_at.isoformat() if hasattr(reaction.reacted_at, "isoformat") else str(reaction.reacted_at),
                    "is_from_me": reaction.is_from_me
                })

        payload = {
            "session": session,
            "session_id": session_id,
            "conversation": conversation,
            "conversation_id": conversation,
            "message_id": original_message,  # ID del mensaje original en Frappe
            "whatsapp_message_id": original_message_id,  # ID de WhatsApp del mensaje original
            "reaction_emoji": reaction_emoji,
            "reacted_by_number": reacted_by_number,
            "reacted_by_name": reacted_by_name if not existing_reaction else existing_reaction.reacted_by_name,
            "reacted_at": reacted_at.isoformat() if hasattr(reacted_at, "isoformat") else str(reacted_at),
            "is_from_me": from_me,
            "reactions": reactions_list,  # Lista completa de reacciones
            "reaction_count": len(reactions_list) if reactions_list else 0
        }

        frappe.log_error(f"📤 Publicando evento realtime de reacción - payload: {frappe.as_json(payload)}", "WhatsApp Webhook Reaction Realtime")

        # Publicar eventos realtime
        try:
            frappe.publish_realtime("whatsapp_reaction", payload)
            frappe.publish_realtime("whatsapp_message_updated", payload)

            frappe.log_error(f"✅ Eventos de reacción publicados correctamente", "WhatsApp Webhook Reaction Realtime")
        except Exception as e:
            frappe.log_error(f"Error publicando eventos realtime de reacción: {str(e)}", "WhatsApp Webhook Reaction Realtime Error")
            import traceback
            frappe.log_error(f"Traceback: {traceback.format_exc()}", "WhatsApp Webhook Reaction Realtime Error")

        frappe.log_error(f"✅ Reacción procesada exitosamente - Message ID: {original_message}, Reaction: {reaction_emoji}, By: {reacted_by_number}", "WhatsApp Webhook Reaction Success")

        return {"processed": True, "action": "reaction_added" if not existing_reaction else "reaction_updated", "message_id": original_message}

    except Exception as e:
        frappe.log_error(f"Error handling reaction received: {str(e)}", "WhatsApp Webhook Reaction Error")
        import traceback
        frappe.log_error(f"Traceback: {traceback.format_exc()}", "WhatsApp Webhook Reaction Error")
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


def _get_media_type_from_message_type(message_type: str) -> str:
    """
    Mapea el tipo de mensaje de WhatsApp al tipo de media de Frappe.

    Args:
        message_type: Tipo de mensaje de WhatsApp

    Returns:
        Tipo de media para Frappe
    """
    type_map = {
        "image": "image",
        "video": "video",
        "audio": "audio",
        "ptt": "voice",
        "document": "document",
        "sticker": "sticker"
    }

    return type_map.get(message_type, "document")
