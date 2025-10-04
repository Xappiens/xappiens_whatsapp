#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API para gestión de mensajes de WhatsApp.
Sincroniza y envía mensajes con el servidor externo.
"""

import frappe
from .base import WhatsAppAPIClient
from typing import Dict, Any, List
from datetime import datetime


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
    conversation = frappe.get_doc("WhatsApp Conversation", conversation_name)
    session = frappe.get_doc("WhatsApp Session", conversation.session)

    if not session.is_connected:
        frappe.throw("La sesión debe estar conectada para sincronizar mensajes")

    client = WhatsAppAPIClient(session.session_id)

    try:
        # Obtener mensajes del servidor
        response = client.post(
            "/chat/fetchMessages/{sessionId}",
            data={
                "chatId": conversation.chat_id,
                "limit": limit
            }
        )

        if not response.get("success"):
            frappe.throw("Error al obtener mensajes del servidor")

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
                frappe.log_error(f"Error al sincronizar mensaje {message_id}: {str(e)}")

        frappe.db.commit()

        # Actualizar última sincronización de la conversación
        conversation.last_sync = frappe.utils.now()
        conversation.save(ignore_permissions=True)
        frappe.db.commit()

        return {
            "success": True,
            "processed": len(messages_data),
            "created": created,
            "updated": updated,
            "errors": errors
        }

    except Exception as e:
        frappe.log_error(f"Error en sincronización de mensajes: {str(e)}")
        frappe.throw(f"Error al sincronizar mensajes: {str(e)}")


@frappe.whitelist()
def send_message(
    session_name: str,
    chat_id: str,
    content: str,
    content_type: str = "string",
    options: Dict = None
) -> Dict[str, Any]:
    """
    Envía un mensaje a través del servidor de WhatsApp.

    Args:
        session_name: Nombre del documento WhatsApp Session
        chat_id: ID del chat destinatario
        content: Contenido del mensaje
        content_type: Tipo de contenido (string, MessageMedia, Location, etc.)
        options: Opciones adicionales

    Returns:
        Dict con resultado del envío
    """
    session = frappe.get_doc("WhatsApp Session", session_name)

    if not session.is_connected:
        frappe.throw("La sesión debe estar conectada para enviar mensajes")

    client = WhatsAppAPIClient(session.session_id)

    try:
        # Enviar mensaje al servidor
        response = client.post(
            "/client/sendMessage/{sessionId}",
            data={
                "chatId": chat_id,
                "contentType": content_type,
                "content": content,
                "options": options or {}
            }
        )

        if response.get("success"):
            message_data = response.get("message", {})

            # Buscar o crear la conversación
            conversation = frappe.db.exists("WhatsApp Conversation", {
                "session": session.name,
                "chat_id": chat_id
            })

            if not conversation:
                # Crear conversación si no existe
                conversation_doc = frappe.get_doc({
                    "doctype": "WhatsApp Conversation",
                    "session": session.name,
                    "chat_id": chat_id,
                    "conversation_name": chat_id,
                    "is_group": "@g.us" in chat_id,
                    "status": "Active"
                })
                conversation_doc.insert(ignore_permissions=True)
                conversation = conversation_doc.name

            # Guardar mensaje en Frappe
            message = _create_message_from_data(message_data, conversation, session)

            frappe.db.commit()

            return {
                "success": True,
                "message_id": message.name,
                "message": "Mensaje enviado exitosamente"
            }
        else:
            frappe.throw("Error al enviar mensaje")

    except Exception as e:
        frappe.log_error(f"Error al enviar mensaje: {str(e)}")
        frappe.throw(f"Error al enviar mensaje: {str(e)}")


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
        response = client.post(
            "/chat/fetchMessages/{sessionId}",
            data={
                "chatId": conversation.chat_id,
                "limit": limit,
                "offset": offset
            }
        )

        if response.get("success"):
            return {
                "success": True,
                "messages": response.get("messages", [])
            }
        else:
            frappe.throw("Error al obtener mensajes")

    except Exception as e:
        frappe.log_error(f"Error al obtener mensajes: {str(e)}")
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
    message_id = message_data.get("id", {}).get("_serialized") or message_data.get("id")

    # Procesar timestamp
    timestamp = message_data.get("timestamp")
    message_time = None
    if timestamp:
        message_time = datetime.fromtimestamp(timestamp)

    # Buscar contacto
    from_id = message_data.get("from")
    contact = None
    if from_id and not message_data.get("fromMe"):
        contact = frappe.db.exists("WhatsApp Contact", {
            "session": session.name,
            "phone_number": from_id
        })

    # Determinar dirección
    direction = "Outgoing" if message_data.get("fromMe") else "Incoming"

    # Determinar tipo de mensaje
    message_type = message_data.get("type", "chat")
    type_map = {
        "chat": "Text",
        "image": "Image",
        "video": "Video",
        "audio": "Audio",
        "ptt": "Voice",
        "document": "Document",
        "location": "Location",
        "vcard": "Contact",
        "multi_vcard": "Contact",
        "sticker": "Sticker"
    }
    frappe_type = type_map.get(message_type, "Text")

    # Determinar estado
    ack = message_data.get("ack")
    status_map = {
        -1: "Failed",
        0: "Pending",
        1: "Sent",
        2: "Delivered",
        3: "Read",
        4: "Played"
    }
    status = status_map.get(ack, "Pending")

    message = frappe.get_doc({
        "doctype": "WhatsApp Message",
        "session": session.name,
        "conversation": conversation,
        "contact": contact if contact else None,
        "message_id": message_id,
        "content": message_data.get("body", ""),
        "direction": direction,
        "message_type": frappe_type,
        "status": status,
        "timestamp": message_time or frappe.utils.now(),
        "from_number": from_id,
        "to_number": message_data.get("to"),
        "has_media": message_data.get("hasMedia", False),
        "is_forwarded": message_data.get("isForwarded", False),
        "is_starred": message_data.get("isStarred", False),
        "is_status": message_data.get("isStatus", False),
        "quoted_msg_id": message_data.get("quotedMsgId"),
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

    message.is_starred = message_data.get("isStarred", message.is_starred)
    message.save(ignore_permissions=True)

