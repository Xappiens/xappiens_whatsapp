#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API para gestión de conversaciones de WhatsApp.
Sincroniza chats desde el servidor externo con WhatsApp Conversation DocType.
"""

import frappe
from .base import WhatsAppAPIClient
from typing import Dict, Any, List


@frappe.whitelist()
def sync_conversations(session_name: str, limit: int = 1000) -> Dict[str, Any]:
    """
    Sincroniza todas las conversaciones de una sesión desde el servidor externo.

    Args:
        session_name: Nombre del documento WhatsApp Session
        limit: Límite de chats a sincronizar

    Returns:
        Dict con resultado de la sincronización
    """
    session = frappe.get_doc("WhatsApp Session", session_name)

    if not session.is_connected:
        frappe.throw("La sesión debe estar conectada para sincronizar conversaciones")

    client = WhatsAppAPIClient(session.session_id)

    try:
        # Obtener chats del servidor
        response = client.get("/client/getChats/{sessionId}", params={"limit": limit})

        if not response.get("success"):
            frappe.throw("Error al obtener chats del servidor")

        chats_data = response.get("chats", [])
        total = response.get("total", 0)

        created = 0
        updated = 0
        errors = 0

        for chat_data in chats_data:
            try:
                chat_id = chat_data.get("id", {}).get("_serialized") or chat_data.get("id")

                if not chat_id:
                    continue

                # Buscar si la conversación ya existe
                existing = frappe.db.exists("WhatsApp Conversation", {
                    "session": session.name,
                    "chat_id": chat_id
                })

                if existing:
                    # Actualizar conversación existente
                    conversation = frappe.get_doc("WhatsApp Conversation", existing)
                    _update_conversation_from_data(conversation, chat_data, session)
                    updated += 1
                else:
                    # Crear nueva conversación
                    conversation = _create_conversation_from_data(chat_data, session)
                    created += 1

            except Exception as e:
                errors += 1
                frappe.log_error(f"Error al sincronizar conversación {chat_id}: {str(e)}")

        frappe.db.commit()

        # Actualizar estadísticas de la sesión
        session.total_chats = frappe.db.count("WhatsApp Conversation", {"session": session.name})
        session.last_sync = frappe.utils.now()
        session.save(ignore_permissions=True)
        frappe.db.commit()

        # Registrar actividad
        frappe.get_doc({
            "doctype": "WhatsApp Activity Log",
            "session": session.name,
            "event_type": "conversations_sync",
            "status": "Success",
            "timestamp": frappe.utils.now(),
            "user": frappe.session.user,
            "details": f"Sincronizados: {created} nuevos, {updated} actualizados, {errors} errores"
        }).insert(ignore_permissions=True)
        frappe.db.commit()

        return {
            "success": True,
            "total_from_server": total,
            "processed": len(chats_data),
            "created": created,
            "updated": updated,
            "errors": errors
        }

    except Exception as e:
        frappe.log_error(f"Error en sincronización de conversaciones: {str(e)}")
        frappe.throw(f"Error al sincronizar conversaciones: {str(e)}")


@frappe.whitelist()
def get_conversation_details(session_name: str, chat_id: str) -> Dict[str, Any]:
    """
    Obtiene detalles completos de una conversación.

    Args:
        session_name: Nombre del documento WhatsApp Session
        chat_id: ID del chat

    Returns:
        Dict con detalles de la conversación
    """
    session = frappe.get_doc("WhatsApp Session", session_name)
    client = WhatsAppAPIClient(session.session_id)

    try:
        response = client.post("/client/getChatById/{sessionId}", data={"chatId": chat_id})

        if response.get("success"):
            return {
                "success": True,
                "chat": response.get("chat", {})
            }
        else:
            frappe.throw("Error al obtener detalles de la conversación")

    except Exception as e:
        frappe.log_error(f"Error al obtener conversación {chat_id}: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }


def _create_conversation_from_data(chat_data: Dict, session: Any) -> Any:
    """
    Crea un nuevo documento WhatsApp Conversation desde datos del servidor.

    Args:
        chat_data: Datos del chat del servidor
        session: Documento WhatsApp Session

    Returns:
        Documento WhatsApp Conversation creado
    """
    chat_id = chat_data.get("id", {}).get("_serialized") or chat_data.get("id")
    is_group = chat_data.get("isGroup", False)

    # Buscar contacto si no es grupo
    contact = None
    if not is_group:
        contact = frappe.db.exists("WhatsApp Contact", {
            "session": session.name,
            "phone_number": chat_id
        })

    # Buscar grupo si es grupo
    group = None
    if is_group:
        group = frappe.db.exists("WhatsApp Group", {
            "session": session.name,
            "group_id": chat_id
        })

    # Procesar último mensaje
    last_message = chat_data.get("lastMessage", {})
    last_message_time = None
    last_message_preview = None

    if last_message:
        timestamp = last_message.get("timestamp")
        if timestamp:
            from datetime import datetime
            last_message_time = datetime.fromtimestamp(timestamp)
        last_message_preview = last_message.get("body", "")[:200]

    conversation = frappe.get_doc({
        "doctype": "WhatsApp Conversation",
        "session": session.name,
        "chat_id": chat_id,
        "conversation_name": chat_data.get("name") or chat_id,
        "is_group": is_group,
        "contact": contact if contact else None,
        "group": group if group else None,
        "unread_count": chat_data.get("unreadCount", 0),
        "is_read_only": chat_data.get("isReadOnly", False),
        "is_pinned": chat_data.get("pinned", False),
        "is_archived": chat_data.get("archived", False),
        "is_muted": chat_data.get("isMuted", False),
        "last_message_time": last_message_time,
        "last_message_preview": last_message_preview,
        "status": "Active",
        "last_sync": frappe.utils.now()
    })

    conversation.insert(ignore_permissions=True)
    return conversation


def _update_conversation_from_data(conversation: Any, chat_data: Dict, session: Any):
    """
    Actualiza un documento WhatsApp Conversation con datos del servidor.

    Args:
        conversation: Documento WhatsApp Conversation
        chat_data: Datos del chat del servidor
        session: Documento WhatsApp Session
    """
    # Procesar último mensaje
    last_message = chat_data.get("lastMessage", {})
    last_message_time = None
    last_message_preview = None

    if last_message:
        timestamp = last_message.get("timestamp")
        if timestamp:
            from datetime import datetime
            last_message_time = datetime.fromtimestamp(timestamp)
        last_message_preview = last_message.get("body", "")[:200]

    conversation.conversation_name = chat_data.get("name") or conversation.conversation_name
    conversation.unread_count = chat_data.get("unreadCount", 0)
    conversation.is_read_only = chat_data.get("isReadOnly", False)
    conversation.is_pinned = chat_data.get("pinned", False)
    conversation.is_archived = chat_data.get("archived", False)
    conversation.is_muted = chat_data.get("isMuted", False)

    if last_message_time:
        conversation.last_message_time = last_message_time
    if last_message_preview:
        conversation.last_message_preview = last_message_preview

    conversation.last_sync = frappe.utils.now()
    conversation.save(ignore_permissions=True)

