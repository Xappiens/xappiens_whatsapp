#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API para gestión de mensajes de WhatsApp.
Sincroniza y envía mensajes con el servidor externo.
"""

import frappe
from .base import WhatsAppAPIClient
from typing import Dict, Any, List, Optional
from datetime import datetime


def _first(data: Dict[str, Any], keys: List[str], default=None):
    """Devuelve el primer valor presente en el diccionario."""
    for key in keys:
        value = data.get(key)
        if value not in (None, "", []):
            return value
    return default


def _parse_timestamp(value: Any) -> Optional[datetime]:
    """Convierte timestamps en segundos, milisegundos o ISO-8601 a datetime."""
    if not value:
        return None

    try:
        if isinstance(value, (int, float)):
            ts = float(value)
            if ts > 1_000_000_000_000:
                ts = ts / 1000
            return datetime.fromtimestamp(ts)
        if isinstance(value, str):
            # Reemplazar Z por +00:00 para compatibilidad
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None

    return None


@frappe.whitelist()
def sync_messages(conversation_name: str, limit: int = 50) -> Dict[str, Any]:
    """
    Sincroniza mensajes de una conversación desde el servidor externo.

    Args:
        conversation_name: Nombre del documento WhatsApp Conversation
        limit: Límite de mensajes a sincronizar

    Returns:
        Dict con resultado de la sincronización
    """
    try:
        conversation = frappe.get_doc("WhatsApp Conversation", conversation_name)
        session = frappe.get_doc("WhatsApp Session", conversation.session)

        frappe.log_error(f"Syncing messages for conversation: {conversation_name}")
        frappe.log_error(f"Conversation chat_id: {conversation.chat_id}")
        frappe.log_error(f"Session: {session.name}, connected: {session.is_connected}")

        if not session.is_connected:
            try:
                from .session_status import get_session_status as refresh_session_status

                status_result = refresh_session_status(session_name=session.name)
                if status_result.get("success"):
                    session.reload()
            except Exception:
                pass

        if not session.is_connected:
            return {
                "success": False,
                "message": "La sesión no está conectada"
            }

        client = WhatsAppAPIClient(session.session_id)

        # Obtener mensajes del servidor
        response = client.get_chat_messages(conversation.chat_id, limit=limit)

        if not response.get("success"):
            return {
                "success": False,
                "message": response.get("message") or "Error al obtener mensajes del servidor"
            }

        payload = response.get("data") or {}
        if isinstance(payload, dict):
            messages_data = payload.get("items") or payload.get("messages") or payload.get("data") or []
        elif isinstance(payload, list):
            messages_data = payload
        else:
            messages_data = response.get("messages", [])

        created = 0
        updated = 0
        errors = 0

        for message_data in messages_data:
            try:
                message_id = message_data.get("id", {}).get("_serialized") or message_data.get("id")

                if not message_id:
                    continue

                # Buscar si el mensaje ya existe
                existing = frappe.db.exists("WhatsApp Message", {
                    "session": session.name,
                    "message_id": message_id
                })

                if existing:
                    # Actualizar mensaje existente
                    message = frappe.get_doc("WhatsApp Message", existing)
                    _update_message_from_data(message, message_data)
                    updated += 1
                else:
                    # Crear nuevo mensaje
                    message = _create_message_from_data(message_data, conversation, session)
                    created += 1

            except Exception as e:
                errors += 1
                # Continuar sin fallar por errores individuales

        frappe.db.commit()

        # Actualizar última sincronización de la conversación
        frappe.db.set_value("WhatsApp Conversation", conversation_name, "modified", frappe.utils.now())
        frappe.db.commit()

        return {
            "success": True,
            "processed": len(messages_data),
            "created": created,
            "updated": updated,
            "errors": errors
        }

    except Exception as e:
        frappe.log_error(f"Error syncing messages: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def get_chat_messages(conversation_name: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    """
    Obtiene mensajes de una conversación desde el servidor.

    Args:
        conversation_name: Nombre del documento WhatsApp Conversation
        limit: Límite de mensajes
        offset: Offset para paginación

    Returns:
        Dict con mensajes
    """
    conversation = frappe.get_doc("WhatsApp Conversation", conversation_name)
    session = frappe.get_doc("WhatsApp Session", conversation.session)

    client = WhatsAppAPIClient(session.session_id)

    try:
        response = client.get_chat_messages(conversation.chat_id, limit=limit, page=(offset // limit) + 1)

        if response.get("success"):
            payload = response.get("data") or {}
            if isinstance(payload, dict):
                messages = payload.get("items") or payload.get("messages") or payload.get("data") or []
            elif isinstance(payload, list):
                messages = payload
            else:
                messages = response.get("messages", [])

            return {
                "success": True,
                "messages": messages
            }
        else:
            frappe.throw(response.get("message") or "Error al obtener mensajes")

    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


def _create_message_from_data(message_data: Dict, conversation: str, session: Any) -> Any:
    """
    Crea un nuevo documento WhatsApp Message desde datos del servidor.

    Args:
        message_data: Datos del mensaje del servidor
        conversation: Nombre del documento WhatsApp Conversation
        session: Documento WhatsApp Session

    Returns:
        Documento WhatsApp Message creado
    """
    message_id = (
        message_data.get("id", {}).get("_serialized")
        if isinstance(message_data.get("id"), dict)
        else message_data.get("id")
    ) or _first(message_data, ["messageId", "message_id"])

    # Procesar timestamp
    message_time = _parse_timestamp(
        _first(message_data, ["timestamp", "messageTimestamp", "sentAt", "createdAt"])
    )

    # Buscar contacto
    from_id = _first(message_data, ["from", "sender", "participant", "author", "remoteJid"])
    if from_id and from_id.endswith("@s.whatsapp.net"):
        from_id = from_id.replace("@s.whatsapp.net", "@c.us")

    contact = None
    if from_id and not message_data.get("fromMe") and message_data.get("direction") != "outgoing":
        contact = frappe.db.exists("WhatsApp Contact", {
            "session": session.name,
            "phone_number": from_id
        })

    # Determinar dirección
    direction_flag = message_data.get("fromMe")
    if direction_flag is None:
        direction_flag = (message_data.get("direction") == "outgoing")
    direction = "Outgoing" if direction_flag else "Incoming"

    # Determinar tipo de mensaje
    message_type = _first(message_data, ["type", "messageType"], "chat")
    type_map = {
        "chat": "text",
        "image": "image",
        "video": "video",
        "audio": "audio",
        "ptt": "voice",
        "document": "document",
        "location": "location",
        "vcard": "contact",
        "multi_vcard": "contact",
        "sticker": "sticker",
        "buttons_response": "buttons",
        "list_response": "list"
    }
    frappe_type = type_map.get(message_type, "text")

    # Determinar estado
    ack = message_data.get("ack")
    if ack is None:
        status_text = _first(message_data, ["status", "ackStatus"])
        status_map_text = {
            "pending": "Pending",
            "sent": "Sent",
            "delivered": "Delivered",
            "read": "Read",
            "played": "Played",
            "failed": "Failed",
            "error": "Failed"
        }
        status = status_map_text.get(str(status_text).lower() if status_text else "", "Pending")
    else:
        status_map = {
            -1: "Failed",
            0: "Pending",
            1: "Sent",
            2: "Delivered",
            3: "Read",
            4: "Played"
        }
        status = status_map.get(ack, "Pending")

    content = _first(
        message_data,
        ["body", "message", "text", "content", "caption", "description"],
        ""
    )

    to_number = _first(message_data, ["to", "recipient", "remoteJid"])
    if to_number and to_number.endswith("@s.whatsapp.net"):
        to_number = to_number.replace("@s.whatsapp.net", "@c.us")

    has_media = bool(
        message_data.get("hasMedia")
        or message_data.get("media")
        or message_data.get("mediaKey")
        or message_data.get("media_url")
    )

    message = frappe.get_doc({
        "doctype": "WhatsApp Message",
        "session": session.name,
        "conversation": conversation,
        "contact": contact if contact else None,
        "message_id": message_id,
        "content": content,
        "direction": direction,
        "message_type": frappe_type,
        "status": status,
        "timestamp": message_time or frappe.utils.now(),
        "from_number": from_id,
        "to_number": to_number,
        "has_media": has_media,
        "is_forwarded": message_data.get("isForwarded", False) or message_data.get("is_forwarded", False),
        "is_starred": message_data.get("isStarred", False),
        "is_status": message_data.get("isStatus", False),
        "quoted_msg_id": _first(message_data, ["quotedMsgId", "quotedMessageId"]),
        "ack": ack
    })

    message.insert(ignore_permissions=True)
    return message


def _update_message_from_data(message: Any, message_data: Dict):
    """
    Actualiza un documento WhatsApp Message con datos del servidor.

    Args:
        message: Documento WhatsApp Message
        message_data: Datos del mensaje del servidor
    """
    # Actualizar solo campos que pueden cambiar
    ack = message_data.get("ack")
    if ack is not None:
        status_map = {
            -1: "Failed",
            0: "Pending",
            1: "Sent",
            2: "Delivered",
            3: "Read",
            4: "Played"
        }
        message.status = status_map.get(ack, message.status)
        message.ack = ack
    else:
        status_text = _first(message_data, ["status", "ackStatus"])
        if status_text:
            status_map_text = {
                "pending": "Pending",
                "sent": "Sent",
                "delivered": "Delivered",
                "read": "Read",
                "played": "Played",
                "failed": "Failed",
                "error": "Failed"
            }
            message.status = status_map_text.get(str(status_text).lower(), message.status)

    content = _first(
        message_data,
        ["body", "message", "text", "content", "caption", "description"],
        message.content
    )
    if content is not None:
        message.content = content

    timestamp = _parse_timestamp(
        _first(message_data, ["timestamp", "messageTimestamp", "sentAt", "createdAt"])
    )
    if timestamp:
        message.timestamp = timestamp

    message.is_starred = message_data.get("isStarred", message.is_starred)
    message.has_media = message_data.get("hasMedia", message.has_media)
    message.save(ignore_permissions=True)


@frappe.whitelist()
def send_message(conversation_id: str, content: str, message_type: str = "text") -> Dict[str, Any]:
    """
    Envía un mensaje a una conversación y lo guarda en el DocType.

    Args:
        conversation_id: ID de la conversación
        content: Contenido del mensaje
        message_type: Tipo de mensaje (text, image, etc.)

    Returns:
        Dict con resultado del envío
    """
    try:
        # Obtener conversación
        conversation = frappe.get_doc("WhatsApp Conversation", conversation_id)
        session = frappe.get_doc("WhatsApp Session", conversation.session)

        if not session.is_connected:
            try:
                from .session_status import get_session_status as refresh_session_status

                status_result = refresh_session_status(session_name=session.name)
                if status_result.get("success"):
                    session.reload()
            except Exception:
                pass

        if not session.is_connected:
            return {
                "success": False,
                "message": "La sesión no está conectada"
            }

        # Preparar datos para envío
        client = WhatsAppAPIClient(session.session_id)

        # Determinar identificador del destinatario
        to_number = conversation.phone_number or conversation.chat_id
        if to_number:
            normalized = to_number.replace("+", "").replace(" ", "")
            if "@" not in normalized:
                to_number = f"{normalized}@s.whatsapp.net"
            else:
                to_number = normalized.replace("@c.us", "@s.whatsapp.net")

        # Enviar mensaje al servidor externo
        response = client.send_message(
            to=to_number,
            message=content,
            message_type=message_type
        )

        if not response.get("success"):
            return {
                "success": False,
                "message": f"Error al enviar mensaje: {response.get('message', 'Error desconocido')}"
            }

        # Guardar mensaje en DocType
        payload = response.get("data") or {}
        message_data = payload.get("message") if isinstance(payload, dict) else response.get("message", {})
        message_id = (
            message_data.get("id", {}).get("_serialized")
            if isinstance(message_data.get("id"), dict)
            else message_data.get("id")
        ) or payload.get("messageId") or response.get("messageId") or frappe.generate_hash(length=20)

        # Crear documento WhatsApp Message
        message_doc = frappe.get_doc({
            "doctype": "WhatsApp Message",
            "session": session.name,
            "conversation": conversation_id,
            "contact": conversation.contact,
            "message_id": message_id,
            "content": content,
            "direction": "Outgoing",
            "message_type": message_type,
            "status": "sent",
            "timestamp": frappe.utils.now_datetime(),
            "from_number": session.phone_number,
            "to_number": to_number,
            "from_me": True,
            "has_media": False,
            "is_forwarded": False,
            "is_starred": False,
            "is_status": False
        })

        message_doc.insert(ignore_permissions=True)

        # Actualizar estadísticas de la sesión
        frappe.db.set_value("WhatsApp Session", session.name, "total_messages_sent",
                           (session.total_messages_sent or 0) + 1)

        # Actualizar última actividad de la conversación
        now_ts = frappe.utils.now_datetime()
        frappe.db.set_value("WhatsApp Conversation", conversation_id, "last_message", content)
        frappe.db.set_value("WhatsApp Conversation", conversation_id, "last_message_time", now_ts)
        frappe.db.set_value("WhatsApp Conversation", conversation_id, "last_message_from_me", True)
        frappe.db.set_value("WhatsApp Conversation", conversation_id, "total_messages",
                           (conversation.total_messages or 0) + 1)

        frappe.db.commit()

        payload = {
            "session": session.name,
            "conversation": conversation_id,
            "conversation_id": conversation_id,
            "message_id": message_doc.name,
            "message": content,
            "content": content,
            "from": session.phone_number,
            "direction": "outgoing",
            "timestamp": now_ts.isoformat() if hasattr(now_ts, "isoformat") else str(now_ts),
        }

        frappe.publish_realtime("whatsapp_message", payload, user="*")
        frappe.publish_realtime("whatsapp_message_sent", payload, user="*")

        return {
            "success": True,
            "message": "Mensaje enviado correctamente",
            "message_id": message_id,
            "whatsapp_message": message_doc.name
        }

    except Exception as e:
        frappe.log_error(f"Error sending message: {str(e)}")
        return {
            "success": False,
            "message": f"Error al enviar mensaje: {str(e)}"
        }


@frappe.whitelist()
def get_profile_pic(contact_id: str, session_id: str = None) -> Dict[str, Any]:
    """
    Obtiene la foto de perfil de un contacto y la actualiza en el DocType.

    Args:
        contact_id: ID del contacto
        session_id: ID de la sesión (opcional, se detecta automáticamente)

    Returns:
        Dict con URL de la foto de perfil
    """
    try:
        # Si no se proporciona session_id, buscar sesión activa
        if not session_id:
            sessions = frappe.get_all("WhatsApp Session",
                                    filters={"is_active": 1, "is_connected": 1},
                                    fields=["name", "session_id"],
                                    limit=1)
            if not sessions:
                return {
                    "success": False,
                    "message": "No hay sesión activa"
                }
            session_id = sessions[0].session_id

        # Obtener sesión
        session = frappe.get_doc("WhatsApp Session", {"session_id": session_id})

        if not session.is_connected:
            return {
                "success": False,
                "message": "La sesión no está conectada"
            }

        # Llamar al servidor externo
        client = WhatsAppAPIClient(session_id)
        response = client.get_contact_info(contact_id)

        if not response.get("success"):
            return {
                "success": False,
                "message": f"Error al obtener foto de perfil: {response.get('message', 'Error desconocido')}"
            }

        payload = response.get("data") or response.get("contact") or {}
        profile_pic_url = _first(payload, ["profilePicUrl", "profilePicURL", "profilePictureUrl"])

        if not profile_pic_url:
            return {
                "success": False,
                "message": "Contacto sin foto de perfil"
            }

        # Actualizar contacto en DocType si existe
        contacts = frappe.get_all("WhatsApp Contact",
                                 filters={"contact_id": contact_id, "session": session.name},
                                 fields=["name"],
                                 limit=1)

        if contacts:
            frappe.db.set_value("WhatsApp Contact", contacts[0].name, "profile_pic_url", profile_pic_url)
            frappe.db.set_value("WhatsApp Contact", contacts[0].name, "last_profile_pic_update", frappe.utils.now())
            frappe.db.commit()

        return {
            "success": True,
            "profile_pic_url": profile_pic_url,
            "contact_id": contact_id
        }

    except Exception as e:
        frappe.log_error(f"Error getting profile pic: {str(e)}")
        return {
            "success": False,
            "message": f"Error al obtener foto de perfil: {str(e)}"
        }


@frappe.whitelist()
def mark_as_read(conversation_id: str, session_id: str = None) -> Dict[str, Any]:
    """
    Marca una conversación como leída y actualiza el DocType.

    Args:
        conversation_id: ID de la conversación
        session_id: ID de la sesión (opcional, se detecta automáticamente)

    Returns:
        Dict con resultado de la operación
    """
    try:
        # Obtener conversación
        conversation = frappe.get_doc("WhatsApp Conversation", conversation_id)

        # Si no se proporciona session_id, usar el de la conversación
        if not session_id:
            session_id = conversation.session

        session = frappe.get_doc("WhatsApp Session", session_id)

        if not session.is_connected:
            return {
                "success": False,
                "message": "La sesión no está conectada"
            }

        # Llamar al servidor externo para marcar como leído
        client = WhatsAppAPIClient(session.session_id)
        response = client.mark_chat_as_read(conversation.chat_id)

        if not response.get("success"):
            return {
                "success": False,
                "message": f"Error al marcar como leído: {response.get('message', 'Error desconocido')}"
            }

        # Actualizar DocType de conversación
        frappe.db.set_value("WhatsApp Conversation", conversation_id, "unread_count", 0)
        frappe.db.commit()

        # Actualizar mensajes no leídos en DocType
        messages = frappe.get_all("WhatsApp Message",
                                filters={"conversation": conversation_id, "status": "delivered"},
                                fields=["name"])

        for msg in messages:
            frappe.db.set_value("WhatsApp Message", msg.name, "status", "read")
            frappe.db.set_value("WhatsApp Message", msg.name, "read_at", frappe.utils.now())

        frappe.db.commit()

        return {
            "success": True,
            "message": "Conversación marcada como leída",
            "conversation_id": conversation_id,
            "unread_count": 0
        }

    except Exception as e:
        frappe.log_error(f"Error marking as read: {str(e)}")
        return {
            "success": False,
            "message": f"Error al marcar como leído: {str(e)}"
        }


@frappe.whitelist()
def get_messages(conversation_id: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    """
    Obtiene mensajes de una conversación desde el DocType.

    Args:
        conversation_id: ID de la conversación
        limit: Límite de mensajes
        offset: Offset para paginación

    Returns:
        Dict con lista de mensajes
    """
    try:
        # Verificar que la conversación existe
        if not frappe.db.exists("WhatsApp Conversation", conversation_id):
            return {
                "success": False,
                "message": "Conversación no encontrada",
                "messages": [],
                "total": 0
            }

        conversation = frappe.get_doc("WhatsApp Conversation", conversation_id)

        # Obtener mensajes desde DocType WhatsApp Message
        messages = frappe.get_all(
            "WhatsApp Message",
            filters={"conversation": conversation_id},
            fields=[
                "name",
                "message_id",
                "content",
                "message_type",
                "direction",
                "timestamp",
                "from_me",
                "status",
                "has_media",
                "quoted_message",
                "quoted_message_content",
                "creation",
            ],
            order_by="timestamp desc",
            limit=limit,
            start=offset,
        )

        # Mostrar en orden cronológico ascendente en el frontend
        messages = list(reversed(messages))

        # Enriquecer mensajes con información adicional
        enriched_messages = []
        for msg in messages:
            # Normalizar direction para el frontend
            direction = msg.direction.lower() if msg.direction else 'incoming'

            # Usar timestamp directamente (ya está en zona horaria correcta)
            timestamp = msg.timestamp
            time_ago = None

            if timestamp:
                try:
                    # Calcular time_ago usando el timestamp original
                    time_ago = frappe.utils.pretty_date(timestamp)

                    # Convertir a string para serialización
                    timestamp = timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)
                except Exception as e:
                    # Si hay error, mantener el timestamp original
                    timestamp = msg.timestamp
                    if timestamp:
                        try:
                            time_ago = frappe.utils.pretty_date(timestamp)
                        except:
                            time_ago = None

            enriched_msg = {
                "name": msg.name,
                "message_id": msg.message_id,
                "content": msg.content,
                "message_type": msg.message_type,
                "direction": direction,
                "timestamp": timestamp,
                "from_me": msg.from_me,
                "status": msg.status,
                "has_media": msg.has_media,
                "quoted_message": msg.quoted_message,
                "quoted_message_content": msg.quoted_message_content,
                "creation": msg.creation,
                "time_ago": time_ago
            }
            enriched_messages.append(enriched_msg)

        return {
            "success": True,
            "messages": enriched_messages,
            "total": len(enriched_messages),
            "conversation_name": conversation.contact_name,
            "conversation_phone": conversation.phone_number
        }

    except Exception as e:
        frappe.log_error(f"Error getting messages: {str(e)}")
        return {
            "success": False,
            "message": str(e),
            "messages": [],
            "total": 0
        }
