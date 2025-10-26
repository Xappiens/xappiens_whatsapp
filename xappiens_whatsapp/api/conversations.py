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
def sync_conversations(session_name: str = None, limit: int = 1000) -> Dict[str, Any]:
    """
    Sincroniza todas las conversaciones de una sesión desde el servidor externo.

    Args:
        session_name: Nombre del documento WhatsApp Session
        limit: Límite de chats a sincronizar

    Returns:
        Dict con resultado de la sincronización
    """
    if not session_name:
        default_session = frappe.db.get_single_value("WhatsApp Settings", "default_session")
        if default_session:
            session_name = default_session
        else:
            # Fallback a la primera sesión activa disponible
            session_name = frappe.db.get_value(
                "WhatsApp Session",
                {"is_active": 1},
                "name"
            )
            if not session_name:
                session_name = frappe.db.get_value("WhatsApp Session", {}, "name")
            if not session_name:
                frappe.throw("No hay sesión de WhatsApp configurada")

    session = frappe.get_doc("WhatsApp Session", session_name)

    if not session.is_connected:
        # Intentar actualizar estado de la sesión antes de abandonar
        try:
            from .session_status import get_session_status as refresh_session_status

            status_result = refresh_session_status(session_name=session.name)
            if status_result.get("success"):
                session.reload()
        except Exception:
            pass

    if not session.is_connected:
        frappe.log_error(f"Sync conversations aborted: session {session.name} not connected")
        return {
            "success": False,
            "message": "La sesión no está conectada"
        }

    client = WhatsAppAPIClient(session.session_id)

    try:
        # Obtener chats del servidor usando la API REST actual
        response = client.get_session_chats(limit=limit)

        if not response.get("success"):
            frappe.log_error(f"Sync conversations error response: {response}")
            return {
                "success": False,
                "message": response.get("message") or "Error al obtener chats del servidor",
                "details": response
            }

        # La respuesta nueva viene en data.items; mantener compatibilidad con el formato anterior
        data = response.get("data") or {}
        if isinstance(data, dict):
            chats_data = data.get("items") or data.get("chats") or data.get("data") or []
            total = data.get("total") if data.get("total") is not None else len(chats_data)
        elif isinstance(data, list):
            chats_data = data
            total = len(chats_data)
        else:
            chats_data = response.get("chats", [])
            total = response.get("total", len(chats_data))

        # Como fallback, si la API devolvió 'messages' (formato antiguo), usarlo
        if not chats_data and response.get("chats"):
            chats_data = response.get("chats", [])
            total = response.get("total", len(chats_data))

        created = 0
        updated = 0
        errors = 0

        frappe.log_error(f"Sync conversations received {len(chats_data)} chats")

        for chat_data in chats_data:
            try:
                chat_id = (
                    chat_data.get("id", {}).get("_serialized")
                    if isinstance(chat_data.get("id"), dict)
                    else chat_data.get("id")
                ) or chat_data.get("chatId") or chat_data.get("jid")

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
                # Continuar sin fallar por errores individuales

        frappe.db.commit()

        # Actualizar estadísticas de la sesión
        total_chats = frappe.db.count("WhatsApp Conversation", {"session": session.name})
        try:
            frappe.db.set_value("WhatsApp Session", session.name, "total_chats", total_chats)
            frappe.db.commit()
        except:
            # Continuar sin fallar por las estadísticas
            pass


        return {
            "success": True,
            "total_from_server": total,
            "processed": len(chats_data),
            "created": created,
            "updated": updated,
            "errors": errors
        }

    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def create_whatsapp_conversation(contact_name: str, session_name: str = None) -> Dict[str, Any]:
    """
    Crea una nueva conversación de WhatsApp con un contacto existente.

    Args:
        contact_name: Nombre del contacto de WhatsApp
        session_name: Nombre de la sesión de WhatsApp (opcional, usa la sesión por defecto)

    Returns:
        Dict con resultado de la creación
    """
    try:
        # Obtener sesión por defecto si no se especifica
        if not session_name:
            session_name = frappe.get_value("WhatsApp Settings", "WhatsApp Settings", "default_session")
            if not session_name:
                return {
                    "success": False,
                    "message": "No hay sesión por defecto configurada"
                }

        # Verificar que la sesión existe y está conectada
        session = frappe.get_doc("WhatsApp Session", session_name)
        if not session.is_connected:
            return {
                "success": False,
                "message": "La sesión de WhatsApp no está conectada"
            }

        # Obtener el contacto
        contact = frappe.get_doc("WhatsApp Contact", contact_name)

        # Verificar si ya existe una conversación con este contacto
        existing_conversation = frappe.db.exists("WhatsApp Conversation", {
            "session": session_name,
            "contact": contact_name,
            "is_group": False
        })

        if existing_conversation:
            return {
                "success": True,
                "message": "La conversación ya existe",
                "conversation_name": existing_conversation,
                "already_exists": True
            }

        # Crear nueva conversación
        # Formatear el chat_id correctamente para WhatsApp (agregar @c.us)
        phone_number = contact.phone_number
        if not phone_number.endswith('@c.us'):
            # Remover el + si existe y agregar @c.us
            clean_phone = phone_number.replace('+', '')
            chat_id = f"{clean_phone}@c.us"
        else:
            chat_id = phone_number

        conversation = frappe.get_doc({
            "doctype": "WhatsApp Conversation",
            "session": session_name,
            "chat_id": chat_id,
            "conversation_name": contact.contact_name or contact.phone_number,
            "is_group": False,
            "contact": contact_name,
            "contact_name": contact.contact_name or contact.phone_number,
            "phone_number": contact.phone_number,
            "status": "Active",
            "is_broadcast": False,
            "is_read_only": False,
            "is_archived": False,
            "is_pinned": False,
            "is_muted": False,
            "unread_count": 0,
            "total_messages": 0,
            "last_message": None,
            "last_message_time": None,
            "last_message_from_me": False,
            "first_message_time": None,
            "mute_expiration": None,
            "notifications_enabled": True,
            "custom_notification_sound": "",
            "priority": "Medium"
        })

        conversation.insert(ignore_permissions=True)
        frappe.db.commit()

        frappe.log_error(f"Conversation created successfully: {conversation.name} for contact {contact_name}")
        frappe.log_error(f"Conversation details: session={session_name}, contact={contact_name}, chat_id={chat_id}")

        return {
            "success": True,
            "message": "Conversación creada exitosamente",
            "conversation_name": conversation.name,
            "conversation_id": conversation.name,
            "chat_id": chat_id
        }

    except Exception as e:
        frappe.log_error(f"Error creating WhatsApp conversation: {str(e)}")
        return {
            "success": False,
            "message": f"Error al crear conversación: {str(e)}"
        }


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
        # No existe un endpoint dedicado a detalles, utilizar la lista de chats y filtrar
        response = client.get_session_chats(limit=200)

        if not response.get("success"):
            frappe.throw(response.get("message") or "Error al obtener detalles de la conversación")

        def _iter_chats(payload):
            if not payload:
                return []
            if isinstance(payload, dict):
                items = payload.get("items") or payload.get("chats") or payload.get("data") or []
                if isinstance(items, list):
                    return items
                return []
            if isinstance(payload, list):
                return payload
            return []

        chats = _iter_chats(response.get("data")) or _iter_chats(response.get("chats"))

        for chat in chats:
            chat_identifier = (
                chat.get("id", {}).get("_serialized")
                if isinstance(chat.get("id"), dict)
                else chat.get("id")
            ) or chat.get("chatId") or chat.get("jid")

            if chat_identifier == chat_id:
                return {
                    "success": True,
                    "chat": chat
                }

        return {
            "success": False,
            "message": "Conversación no encontrada en el servidor"
        }

    except Exception as e:
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
    raw_id = chat_data.get("id")
    if isinstance(raw_id, dict):
        chat_id = raw_id.get("_serialized") or raw_id.get("user")
    else:
        chat_id = raw_id
    chat_id = chat_id or chat_data.get("chatId") or chat_data.get("jid") or chat_data.get("waId")
    if chat_id and "@s.whatsapp.net" in chat_id:
        chat_id = chat_id.replace("@s.whatsapp.net", "@c.us")

    is_group = chat_data.get("isGroup", False)

    # Buscar contacto si no es grupo
    contact = None
    if not is_group:
        contact = frappe.db.get_value(
            "WhatsApp Contact",
            {"session": session.name, "contact_id": chat_id},
            "name"
        )
        if not contact:
            normalized_phone = chat_id.replace("@c.us", "") if chat_id else None
            if normalized_phone:
                formatted_phone = f"+{normalized_phone}" if not normalized_phone.startswith("+") else normalized_phone
                contact = frappe.db.get_value(
                    "WhatsApp Contact",
                    {"session": session.name, "phone_number": formatted_phone},
                    "name"
                )

    # Buscar grupo si es grupo
    group = None
    if is_group:
        group = frappe.db.exists("WhatsApp Group", {
            "session": session.name,
            "group_id": chat_id
        })

    # Procesar último mensaje
    last_message = chat_data.get("lastMessage") or chat_data.get("last_message") or chat_data.get("lastMessageData") or {}
    last_message_time = None
    last_message_preview = None

    if last_message:
        timestamp = (
            last_message.get("timestamp")
            or last_message.get("sentAt")
            or last_message.get("createdAt")
            or chat_data.get("lastMessageAt")
        )
        if timestamp:
            from datetime import datetime
            # Algunas respuestas ya envían timestamps en ms o en ISO-8601
            try:
                if isinstance(timestamp, (int, float)):
                    # Detectar si viene en milisegundos
                    if timestamp > 1_000_000_000_000:
                        timestamp = timestamp / 1000
                    last_message_time = datetime.fromtimestamp(timestamp)
                elif isinstance(timestamp, str):
                    last_message_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except Exception:
                last_message_time = None

        body = (
            last_message.get("body")
            or last_message.get("message")
            or last_message.get("text")
            or chat_data.get("lastMessageText")
            or ""
        )
        last_message_preview = body[:200]

    # Procesar información adicional
    first_message_time = None
    if chat_data.get("firstMessageTime"):
        from datetime import datetime
        first_message_time = datetime.fromtimestamp(chat_data.get("firstMessageTime"))

    mute_expiration = None
    if chat_data.get("muteExpiration"):
        from datetime import datetime
        mute_expiration = datetime.fromtimestamp(chat_data.get("muteExpiration"))

    title = (chat_data.get("name") or chat_data.get("contactName") or chat_id or "")[:140]
    contact_name = (chat_data.get("contactName") or chat_data.get("name") or "")[:140]

    conversation = frappe.get_doc({
        "doctype": "WhatsApp Conversation",
        "session": session.name,
        "chat_id": chat_id,
        "conversation_name": title,
        "is_group": is_group,
        "contact": contact if contact else None,
        "contact_name": contact_name,
        "phone_number": chat_id if not is_group else None,
        "group": group if group else None,
        "status": "Active",
        "is_broadcast": chat_data.get("isBroadcast", False),
        "is_read_only": chat_data.get("isReadOnly", False),
        "is_archived": chat_data.get("archived", False),
        "is_pinned": chat_data.get("pinned", False),
        "is_muted": chat_data.get("isMuted", False),
        "unread_count": chat_data.get("unreadCount", 0),
        "total_messages": chat_data.get("totalMessages", 0) or chat_data.get("messageCount", 0),
        "last_message": last_message_preview,
        "last_message_time": last_message_time,
        "last_message_from_me": last_message.get("fromMe", False) if isinstance(last_message, dict) else False,
        "first_message_time": first_message_time,
        "mute_expiration": mute_expiration,
        "notifications_enabled": not chat_data.get("isMuted", False),
        "custom_notification_sound": chat_data.get("customNotificationSound", ""),
        "priority": "Medium"
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
    last_message = chat_data.get("lastMessage") or chat_data.get("last_message") or {}
    last_message_time = None
    last_message_preview = None

    if last_message:
        timestamp = (
            last_message.get("timestamp")
            or last_message.get("sentAt")
            or last_message.get("createdAt")
            or chat_data.get("lastMessageAt")
        )
        if timestamp:
            from datetime import datetime
            try:
                if isinstance(timestamp, (int, float)):
                    if timestamp > 1_000_000_000_000:
                        timestamp = timestamp / 1000
                    last_message_time = datetime.fromtimestamp(timestamp)
                elif isinstance(timestamp, str):
                    last_message_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except Exception:
                last_message_time = None
        body = (
            last_message.get("body")
            or last_message.get("message")
            or last_message.get("text")
            or chat_data.get("lastMessageText")
            or ""
        )
        last_message_preview = body[:200]

    # Actualizar campos usando frappe.db.set_value para evitar conflictos de concurrencia
    try:
        title = (chat_data.get("name") or chat_data.get("contactName") or conversation.conversation_name or "")[:140]
        contact_name = (chat_data.get("contactName") or chat_data.get("name") or conversation.contact_name or "")[:140]

        frappe.db.set_value("WhatsApp Conversation", conversation.name, "conversation_name", title)
        frappe.db.set_value("WhatsApp Conversation", conversation.name, "unread_count", chat_data.get("unreadCount", 0))
        frappe.db.set_value("WhatsApp Conversation", conversation.name, "is_read_only", chat_data.get("isReadOnly", False))
        frappe.db.set_value("WhatsApp Conversation", conversation.name, "is_pinned", chat_data.get("pinned", False))
        frappe.db.set_value("WhatsApp Conversation", conversation.name, "is_archived", chat_data.get("archived", False))
        frappe.db.set_value("WhatsApp Conversation", conversation.name, "is_muted", chat_data.get("isMuted", False))
        frappe.db.set_value("WhatsApp Conversation", conversation.name, "contact_name", contact_name)

        if last_message_time:
            frappe.db.set_value("WhatsApp Conversation", conversation.name, "last_message_time", last_message_time)
        if last_message_preview is not None:
            frappe.db.set_value("WhatsApp Conversation", conversation.name, "last_message", last_message_preview)
        if isinstance(last_message, dict) and "fromMe" in last_message:
            frappe.db.set_value("WhatsApp Conversation", conversation.name, "last_message_from_me", last_message.get("fromMe"))

        # Totales
        total_messages = chat_data.get("totalMessages")
        if total_messages is None:
            total_messages = chat_data.get("messageCount")
        if total_messages is not None:
            frappe.db.set_value("WhatsApp Conversation", conversation.name, "total_messages", total_messages)

        frappe.db.commit()
    except:
        # Continuar sin fallar por la actualización
        pass


@frappe.whitelist()
def get_conversations(session_id: str = None, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    """
    Obtiene todas las conversaciones desde el DocType (no desde servidor externo).

    Args:
        session_id: ID de la sesión (opcional, se detecta automáticamente)
        limit: Límite de conversaciones
        offset: Offset para paginación

    Returns:
        Dict con lista de conversaciones
    """
    try:
        # Si no se proporciona session_id, buscar sesión activa
        if not session_id:
            sessions = frappe.get_all("WhatsApp Session",
                                    filters={"is_active": 1, "is_connected": 1},
                                    fields=["name", "session_id"],
                                    limit=1)
            if not sessions:
                frappe.log_error("No active session found")
                return {
                    "success": False,
                    "message": "No hay sesión activa",
                    "conversations": [],
                    "total": 0
                }
            session_id = sessions[0].name
            frappe.log_error(f"Using session: {session_id}")

        # Sincronizar antes de devolver resultados para asegurar datos frescos
        try:
            sync_result = sync_conversations(session_name=session_id)
            if isinstance(sync_result, dict) and not sync_result.get("success", True):
                frappe.log_error(f"Auto sync from get_conversations returned error: {sync_result}")
        except Exception as sync_error:
            frappe.log_error(f"Auto sync from get_conversations failed: {sync_error}")

        # Obtener conversaciones desde DocType
        conversations = frappe.get_all("WhatsApp Conversation",
                                     filters={"session": session_id, "is_archived": 0},
                                     fields=["name", "contact_name", "phone_number", "last_message",
                                           "last_message_time", "last_message_from_me", "unread_count",
                                           "is_muted", "is_pinned", "is_archived", "linked_lead",
                                           "linked_customer", "total_messages", "session", "contact",
                                           "chat_id", "is_group"],
                                     order_by="last_message_time desc",
                                     limit=limit,
                                     start=offset)

        frappe.log_error(f"Found {len(conversations)} conversations for session {session_id}")
        # Log conversation names in chunks to avoid character limit
        conv_names = [c.name for c in conversations]
        if conv_names:
            # Log first few names only to stay within character limit
            sample_names = conv_names[:5]  # Show first 5 names
            frappe.log_error(f"Sample conversation names: {sample_names}")
            if len(conv_names) > 5:
                frappe.log_error(f"Total conversations: {len(conv_names)}")

        # Enriquecer con información adicional
        enriched_conversations = []
        for conv in conversations:
            frappe.log_error(f"Processing conversation: {conv.name}")
            # Obtener información del contacto
            contact_info = None
            if conv.contact:
                contact = frappe.get_all("WhatsApp Contact",
                                       filters={"name": conv.contact},
                                       fields=["name", "contact_name", "profile_pic_thumb", "is_verified", "is_group", "pushname"],
                                       limit=1)
                if contact:
                    contact_info = contact[0]
                    frappe.log_error(f"Found contact info for {conv.name}: {contact_info.contact_name}")

            # Obtener último mensaje
            last_message_info = None
            last_message = frappe.get_all("WhatsApp Message",
                                       filters={"conversation": conv.name},
                                       fields=["content", "timestamp", "from_me", "message_type", "status"],
                                       order_by="timestamp desc",
                                       limit=1)
            if last_message:
                last_message_info = last_message[0]

            # Construir objeto enriquecido
            enriched_conv = {
                "name": conv.name,
                "phone_number": conv.phone_number,
                "unread_count": conv.unread_count or 0,
                "is_muted": conv.is_muted,
                "is_pinned": conv.is_pinned,
                "is_archived": conv.is_archived,
                "total_messages": conv.total_messages or 0,
                "is_group": conv.is_group or False,
                "chat_id": conv.chat_id
            }

            # Información del contacto
            if contact_info:
                enriched_conv["contact_name"] = contact_info.contact_name or contact_info.pushname or conv.contact_name
                enriched_conv["profile_pic"] = contact_info.profile_pic_thumb
                enriched_conv["is_verified"] = contact_info.is_verified
            else:
                enriched_conv["contact_name"] = conv.contact_name
                enriched_conv["profile_pic"] = None
                enriched_conv["is_verified"] = False

            # Información del último mensaje
            if last_message_info:
                # Usar timestamp directamente (ya está en zona horaria correcta)
                timestamp = last_message_info.timestamp
                if timestamp:
                    try:
                        # Convertir a string para serialización
                        timestamp = timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)
                    except Exception:
                        timestamp = last_message_info.timestamp

                enriched_conv["last_message"] = last_message_info.content
                enriched_conv["last_message_time"] = timestamp
                enriched_conv["last_message_from_me"] = last_message_info.from_me
                enriched_conv["last_message_type"] = last_message_info.message_type
                enriched_conv["last_message_status"] = last_message_info.status
            else:
                # Usar timestamp directamente (ya está en zona horaria correcta)
                timestamp = conv.last_message_time
                if timestamp:
                    try:
                        # Convertir a string para serialización
                        timestamp = timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)
                    except Exception:
                        timestamp = conv.last_message_time

                enriched_conv["last_message"] = conv.last_message
                enriched_conv["last_message_time"] = timestamp
                enriched_conv["last_message_from_me"] = conv.last_message_from_me
                enriched_conv["last_message_type"] = "text"
                enriched_conv["last_message_status"] = "sent"

            # Información del lead si está vinculado
            if conv.linked_lead:
                lead_info = frappe.get_all("CRM Lead",
                                         filters={"name": conv.linked_lead},
                                         fields=["name", "lead_name", "status"],
                                         limit=1)
                if lead_info:
                    enriched_conv["lead"] = lead_info[0]

            enriched_conversations.append(enriched_conv)

        frappe.log_error(f"Returning {len(enriched_conversations)} conversations")
        # Log enriched conversation names in chunks to avoid character limit
        enriched_names = [c['name'] for c in enriched_conversations]
        if enriched_names:
            # Log first few names only to stay within character limit
            sample_enriched_names = enriched_names[:5]  # Show first 5 names
            frappe.log_error(f"Sample enriched conversation names: {sample_enriched_names}")
            if len(enriched_names) > 5:
                frappe.log_error(f"Total enriched conversations: {len(enriched_names)}")

        return {
            "success": True,
            "conversations": enriched_conversations,
            "total": len(enriched_conversations)
        }

    except Exception as e:
        # Truncate error message to avoid character limit issues
        error_msg = str(e)
        if len(error_msg) > 100:  # Leave some room for the prefix
            error_msg = error_msg[:100] + "..."
        frappe.log_error(f"Error getting conversations: {error_msg}")
        return {
            "success": False,
            "message": str(e),
            "conversations": [],
            "total": 0
        }
