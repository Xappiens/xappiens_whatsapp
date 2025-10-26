#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API para sincronización automática de datos de WhatsApp con Baileys.
Orquesta la sincronización completa de sesiones, contactos, conversaciones y mensajes.
"""

import frappe
from .base import WhatsAppAPIClient
from .session import get_session_status
from .contacts import sync_contacts
from .conversations import sync_conversations
from .messages import sync_messages
from typing import Dict, Any, List
from datetime import datetime


@frappe.whitelist()
def sync_session_data(session_name: str, sync_contacts_flag: bool = True, sync_conversations_flag: bool = True, sync_messages_flag: bool = True) -> Dict[str, Any]:
    """
    Sincroniza todos los datos de una sesión desde el servidor externo.

    Args:
        session_name: Nombre del documento WhatsApp Session
        sync_contacts_flag: Si debe sincronizar contactos
        sync_conversations_flag: Si debe sincronizar conversaciones
        sync_messages_flag: Si debe sincronizar mensajes (habilitado por defecto)

    Returns:
        Dict con resultado de la sincronización completa
    """
    session = frappe.get_doc("WhatsApp Session", session_name)

    if not session.is_connected:
        frappe.throw("La sesión debe estar conectada para sincronizar")

    results = {
        "success": True,
        "session": session.session_id,
        "timestamp": frappe.utils.now(),
        "sync_status": {}
    }

    try:
        # 1. Actualizar estado de la sesión
        status_result = get_session_status(session_name)
        results["sync_status"]["session_status"] = status_result

        # 2. Sincronizar contactos
        if sync_contacts_flag:
            frappe.publish_realtime(
                "sync_progress",
                {"step": "Sincronizando contactos..."},
                user=frappe.session.user
            )
            contacts_result = sync_contacts(session_name)
            results["sync_status"]["contacts"] = contacts_result

        # 3. Sincronizar conversaciones
        if sync_conversations_flag:
            frappe.publish_realtime(
                "sync_progress",
                {"step": "Sincronizando conversaciones..."},
                user=frappe.session.user
            )
            conversations_result = sync_conversations(session_name)
            results["sync_status"]["conversations"] = conversations_result

        # 4. Sincronizar mensajes recientes de cada conversación
        if sync_messages_flag:
            frappe.publish_realtime(
                "sync_progress",
                {"step": "Sincronizando mensajes..."},
                user=frappe.session.user
            )

            # Obtener todas las conversaciones activas
            conversations = frappe.get_all(
                "WhatsApp Conversation",
                filters={
                    "session": session.name,
                    "status": "Active"
                },
                limit=20  # Limitar a las 20 conversaciones más recientes
            )

            messages_results = []
            for conv in conversations:
                try:
                    msg_result = sync_messages(conv.name, limit=20)
                    messages_results.append(msg_result)
                except:
                    pass

            results["sync_status"]["messages"] = {
                "conversations_synced": len(messages_results),
                "total_messages": sum(r.get("created", 0) + r.get("updated", 0) for r in messages_results)
            }

        # 5. Actualizar estadísticas de la sesión
        update_session_stats(session_name)


        frappe.publish_realtime(
            "sync_progress",
            {"step": "Sincronización completada", "results": results},
            user=frappe.session.user
        )

        return results

    except Exception as e:
        results["success"] = False
        results["error"] = str(e)

        return results


@frappe.whitelist()
def auto_sync_all_sessions():
    """
    Sincroniza automáticamente todas las sesiones activas.
    Esta función se ejecuta desde un scheduled job.
    """
    settings = frappe.get_single("WhatsApp Settings")

    if not settings.enabled or not settings.auto_sync_enabled:
        return {"success": False, "message": "Auto-sync deshabilitado"}

    # Obtener todas las sesiones activas y conectadas
    sessions = frappe.get_all(
        "WhatsApp Session",
        filters={
            "is_active": 1,
            "is_connected": 1
        },
        pluck="name"
    )

    results = {
        "total_sessions": len(sessions),
        "synced": 0,
        "failed": 0,
        "errors": []
    }

    for session_name in sessions:
        try:
            frappe.set_user("Administrator")  # Ejecutar como administrador en jobs

            # Sincronizar contactos, conversaciones y mensajes
            sync_result = sync_session_data(
                session_name,
                sync_contacts_flag=True,
                sync_conversations_flag=True,
                sync_messages_flag=True
            )

            if sync_result.get("success"):
                results["synced"] += 1
            else:
                results["failed"] += 1
                results["errors"].append({
                    "session": session_name,
                    "error": sync_result.get("error", "Unknown error")
                })

        except Exception as e:
            results["failed"] += 1
            results["errors"].append({
                "session": session_name,
                "error": str(e)
            })
            # Continuar con la siguiente sesión

    # Auto-sync completado

    return results


def _create_message_from_data(message_data: Dict, conversation: str, session: Any) -> Any:
    """
    Crea un nuevo documento WhatsApp Message desde datos del servidor.
    (Importado desde messages.py para evitar circular import)
    """
    from .messages import _create_message_from_data as create_msg
    return create_msg(message_data, conversation, session)


# ========== MÉTODOS PARA BAILEYS/INBOX HUB ==========

@frappe.whitelist()
def sync_session_complete(session_name: str) -> Dict[str, Any]:
    """
    Sincronización completa de una sesión usando la nueva API de Baileys.
    Sincroniza contactos, chats y mensajes desde Inbox Hub.

    Args:
        session_name: Nombre del documento WhatsApp Session

    Returns:
        Dict con resultado de la sincronización
    """
    try:
        session = frappe.get_doc("WhatsApp Session", session_name)

        client = WhatsAppAPIClient(session.session_id)

        # SIEMPRE verificar estado real en el servidor (ignorar estado local de Frappe)
        # porque el estado puede estar desactualizado
        try:
            sessions_response = client.get_sessions(limit=100)
            if sessions_response.get("success"):
                sessions_list = sessions_response.get("data", {}).get("sessions", [])

                # Buscar nuestra sesión
                current_session = None
                for s in sessions_list:
                    if s.get("sessionId") == session.session_id:
                        current_session = s
                        break

                if current_session:
                    api_status = current_session.get("status", "").upper()

                    # Actualizar SIEMPRE el estado local con el estado real del servidor
                    frappe.db.set_value("WhatsApp Session", session.name, {
                        "status": session._map_status(api_status),
                        "is_connected": 1 if api_status == "CONNECTED" else 0,
                        "phone_number": current_session.get("phoneNumber")
                    })
                    frappe.db.commit()

                    # Verificar que la sesión está realmente conectada en la API
                    if api_status != "CONNECTED":
                        return {
                            "success": False,
                            "message": f"La sesión no está conectada en el servidor (Estado: {api_status}). Por favor, reconecta la sesión escaneando el código QR."
                        }
                else:
                    frappe.log_error(
                        message=f"Session {session.session_id} not found in API response",
                        title="WA Session Not Found"
                    )
                    return {
                        "success": False,
                        "message": "La sesión no se encontró en el servidor. Por favor, verifica la configuración."
                    }

        except Exception as status_error:
            error_msg = str(status_error)[:150]
            frappe.log_error(
                message=f"Status verification error: {error_msg}",
                title=f"WA Status Check - {session.name[:20]}"
            )
            # Continuar con la sincronización pero advertir
            frappe.msgprint(
                "Advertencia: No se pudo verificar el estado de la sesión. Intentando sincronizar...",
                indicator="orange"
            )

        results = {
            "success": True,
            "session": session.session_id,
            "timestamp": frappe.utils.now(),
            "contacts": {"processed": 0, "created": 0, "updated": 0},
            "chats": {"processed": 0, "created": 0, "updated": 0},
            "messages": {"processed": 0, "created": 0, "updated": 0}
        }

        # 1. Sincronizar contactos
        frappe.publish_realtime(
            "sync_progress",
            {"step": "Sincronizando contactos...", "progress": 25},
            user=frappe.session.user
        )

        contacts_result = _sync_contacts_baileys(client, session)
        results["contacts"] = contacts_result

        # Rate limiting: esperar 1 segundo entre operaciones principales
        import time
        time.sleep(1)

        # 2. Sincronizar chats/conversaciones
        # DESHABILITADO TEMPORALMENTE: El endpoint de chats tiene un bug en el servidor Baileys
        # que causa que la sesión se desconecte (error: column Message.isDeleted does not exist)
        frappe.publish_realtime(
            "sync_progress",
            {"step": "Omitiendo conversaciones (bug del servidor)...", "progress": 50},
            user=frappe.session.user
        )

        # chats_result = _sync_chats_baileys(client, session)
        # results["chats"] = chats_result
        results["chats"] = {"processed": 0, "created": 0, "updated": 0, "skipped": True, "reason": "Baileys server bug"}

        # Rate limiting: esperar 1 segundo
        time.sleep(1)

        # 3. Sincronizar mensajes de cada chat
        # DESHABILITADO TEMPORALMENTE: Depende de tener chats sincronizados primero
        frappe.publish_realtime(
            "sync_progress",
            {"step": "Omitiendo mensajes (depende de chats)...", "progress": 75},
            user=frappe.session.user
        )

        # messages_result = _sync_messages_baileys(client, session)
        # results["messages"] = messages_result
        results["messages"] = {"processed": 0, "created": 0, "updated": 0, "skipped": True, "reason": "Depends on chats"}

        # 4. Actualizar estadísticas
        _update_session_statistics(session)

        frappe.publish_realtime(
            "sync_progress",
            {"step": "Sincronización completada", "progress": 100, "results": results},
            user=frappe.session.user
        )

        return results

    except Exception as e:
        error_msg = str(e)[:200]  # Limitar longitud
        frappe.log_error(
            message=f"Sync error: {error_msg}",
            title=f"WhatsApp Sync Failed - {session_name[:20]}"
        )
        return {
            "success": False,
            "message": error_msg
        }


def _sync_contacts_baileys(client: WhatsAppAPIClient, session: Any) -> Dict[str, Any]:
    """
    Sincroniza contactos desde Baileys.

    Args:
        client: Cliente API configurado
        session: Documento WhatsApp Session

    Returns:
        Dict con resultado de sincronización
    """
    try:
        # REDUCIDO: Solo 200 contactos por sincronización para evitar sobrecarga
        response = client.get_session_contacts(page=1, limit=200)

        if not response.get("success"):
            return {"processed": 0, "created": 0, "updated": 0, "errors": 1}

        contacts_data = response.get("data", {}).get("contacts", [])
        created = 0
        updated = 0
        errors = 0

        for contact_data in contacts_data:
            try:
                contact_id = contact_data.get("id")
                phone_number = contact_data.get("phone") or contact_id

                if not contact_id:
                    continue

                # Verificar si existe
                existing = frappe.db.exists("WhatsApp Contact", {
                    "session": session.name,
                    "phone_number": phone_number
                })

                if existing:
                    # Actualizar contacto
                    contact = frappe.get_doc("WhatsApp Contact", existing)
                    contact.contact_name = contact_data.get("name") or contact.contact_name
                    contact.pushname = contact_data.get("notify") or contact.pushname  # ✅ CORREGIDO
                    contact.verified_name = contact_data.get("verifiedName") or contact.verified_name  # ✅ AGREGADO
                    contact.profile_pic_url = contact_data.get("imgUrl") or contact.profile_pic_url  # ✅ CORREGIDO
                    contact.is_user = contact_data.get("isUser", contact.is_user)
                    contact.is_group = contact_data.get("isGroup", contact.is_group)
                    contact.is_wa_contact = contact_data.get("isWAContact", contact.is_wa_contact)
                    contact.last_sync = frappe.utils.now()
                    contact.save(ignore_permissions=True)
                    updated += 1
                else:
                    # Crear contacto
                    contact = frappe.get_doc({
                        "doctype": "WhatsApp Contact",
                        "session": session.name,
                        "contact_id": contact_id,
                        "phone_number": phone_number,
                        "contact_name": contact_data.get("name") or phone_number,
                        "pushname": contact_data.get("notify"),  # ✅ CORREGIDO
                        "verified_name": contact_data.get("verifiedName"),  # ✅ AGREGADO
                        "profile_pic_url": contact_data.get("imgUrl"),  # ✅ CORREGIDO
                        "is_user": contact_data.get("isUser", False),
                        "is_group": contact_data.get("isGroup", False),
                        "is_wa_contact": contact_data.get("isWAContact", True),
                        "last_sync": frappe.utils.now(),
                        "sync_status": "Synced"
                    })
                    contact.insert(ignore_permissions=True)
                    created += 1

            except Exception as e:
                errors += 1
                error_short = str(e)[:100]
                frappe.log_error(
                    message=f"Contact error: {error_short}",
                    title=f"WA Contact - {contact_id[:20]}"
                )

        frappe.db.commit()

        return {
            "processed": len(contacts_data),
            "created": created,
            "updated": updated,
            "errors": errors
        }

    except Exception as e:
        error_msg = str(e)[:150]
        frappe.log_error(
            message=f"Contact sync error: {error_msg}",
            title=f"WA Contact Sync - {session.name[:20]}"
        )
        return {"processed": 0, "created": 0, "updated": 0, "errors": 1}


def _sync_chats_baileys(client: WhatsAppAPIClient, session: Any) -> Dict[str, Any]:
    """
    Sincroniza chats/conversaciones desde Baileys.

    Args:
        client: Cliente API configurado
        session: Documento WhatsApp Session

    Returns:
        Dict con resultado de sincronización
    """
    try:
        # REDUCIDO: Solo 50 chats por sincronización para evitar sobrecarga
        response = client.get_session_chats(page=1, limit=50)

        if not response.get("success"):
            error_msg = response.get("error", "Unknown error")
            # Verificar si es el error conocido de isDeleted
            if "isDeleted" in str(error_msg) or "does not exist" in str(error_msg):
                frappe.log_error(
                    message=f"Baileys DB schema error (known issue): {error_msg[:150]}",
                    title="WA Baileys Schema Issue"
                )
                # Retornar resultado vacío pero sin marcar como error
                return {"processed": 0, "created": 0, "updated": 0, "errors": 0, "skipped": True}
            return {"processed": 0, "created": 0, "updated": 0, "errors": 1}

        chats_data = response.get("data", {}).get("chats", [])
        created = 0
        updated = 0
        errors = 0

        for chat_data in chats_data:
            try:
                chat_id = chat_data.get("chatId")

                if not chat_id:
                    continue

                # Verificar si existe
                existing = frappe.db.exists("WhatsApp Conversation", {
                    "session": session.name,
                    "chat_id": chat_id
                })

                # Obtener último mensaje
                last_msg = chat_data.get("lastMessage", {})
                last_msg_content = last_msg.get("content", "")
                last_msg_time = last_msg.get("timestamp")
                last_msg_from_me = last_msg.get("fromMe", False)

                if existing:
                    # Actualizar conversación
                    conversation = frappe.get_doc("WhatsApp Conversation", existing)
                    conversation.contact_name = chat_data.get("name") or conversation.contact_name  # ✅ CORREGIDO
                    conversation.unread_count = chat_data.get("unreadCount", 0)
                    conversation.is_group = chat_data.get("isGroup", False)

                    if last_msg_content:
                        conversation.last_message = last_msg_content
                        conversation.last_message_from_me = last_msg_from_me
                        if last_msg_time:
                            conversation.last_message_time = datetime.fromtimestamp(last_msg_time)

                    conversation.save(ignore_permissions=True)
                    updated += 1
                else:
                    # Extraer número de teléfono del chat_id
                    phone_number = chat_id.split('@')[0] if '@' in chat_id else chat_id

                    # Buscar contacto asociado
                    contact = frappe.db.get_value("WhatsApp Contact", {
                        "session": session.name,
                        "phone_number": phone_number
                    }, "name")

                    # Crear conversación
                    conversation = frappe.get_doc({
                        "doctype": "WhatsApp Conversation",
                        "session": session.name,
                        "chat_id": chat_id,
                        "contact_name": chat_data.get("name") or phone_number,  # ✅ CORREGIDO: Eliminado conversation_name
                        "phone_number": phone_number,
                        "contact": contact if contact else None,
                        "is_group": chat_data.get("isGroup", False),
                        "unread_count": chat_data.get("unreadCount", 0),
                        "status": "Active",
                        "is_archived": False,
                        "is_pinned": False,
                        "is_muted": False,
                        "last_message": last_msg_content,
                        "last_message_from_me": last_msg_from_me,
                        "last_message_time": datetime.fromtimestamp(last_msg_time) if last_msg_time else None
                    })
                    conversation.insert(ignore_permissions=True)
                    created += 1

            except Exception as e:
                errors += 1
                error_short = str(e)[:100]
                frappe.log_error(
                    message=f"Chat error: {error_short}",
                    title=f"WA Chat - {chat_id[:20]}"
                )

        frappe.db.commit()

        return {
            "processed": len(chats_data),
            "created": created,
            "updated": updated,
            "errors": errors
        }

    except Exception as e:
        error_msg = str(e)

        # Verificar si es el error conocido del esquema de Baileys
        if "isDeleted" in error_msg or "does not exist" in error_msg:
            frappe.log_error(
                message=f"Baileys DB schema error (known issue): {error_msg[:150]}\n\n"
                        "Este es un problema conocido del servidor Baileys. "
                        "La columna Message.isDeleted no existe en su base de datos. "
                        "Contacte al administrador del servidor Baileys para resolver este problema.",
                title="WA Baileys Schema Issue"
            )
            # Retornar sin marcar como error crítico
            return {"processed": 0, "created": 0, "updated": 0, "errors": 0, "skipped": True, "reason": "Baileys schema error"}

        # Otros errores sí los marcamos como críticos
        frappe.log_error(
            message=f"Chat sync error: {error_msg[:150]}",
            title=f"WA Chat Sync - {session.name[:20]}"
        )
        return {"processed": 0, "created": 0, "updated": 0, "errors": 1}


def _sync_messages_baileys(client: WhatsAppAPIClient, session: Any) -> Dict[str, Any]:
    """
    Sincroniza mensajes recientes de cada conversación desde Baileys.

    Args:
        client: Cliente API configurado
        session: Documento WhatsApp Session

    Returns:
        Dict con resultado de sincronización
    """
    try:
        # Obtener conversaciones activas
        conversations = frappe.get_all(
            "WhatsApp Conversation",
            filters={
                "session": session.name,
                "status": "Active"
            },
            fields=["name", "chat_id"],
            limit=10,  # REDUCIDO: Solo 10 conversaciones para evitar sobrecarga
            order_by="last_message_time desc"  # Las más recientes primero
        )

        total_processed = 0
        total_created = 0
        total_updated = 0
        total_errors = 0

        for idx, conv in enumerate(conversations):
            try:
                # Rate limiting: delay de 500ms entre peticiones
                if idx > 0:
                    import time
                    time.sleep(0.5)

                response = client.get_chat_messages(conv.chat_id, page=1, limit=50)

                if not response.get("success"):
                    continue

                messages_data = response.get("data", {}).get("messages", [])

                for msg_data in messages_data:
                    try:
                        message_id = msg_data.get("whatsappMessageId") or msg_data.get("id")

                        if not message_id:
                            continue

                        # Verificar si existe
                        existing = frappe.db.exists("WhatsApp Message", {
                            "session": session.name,
                            "message_id": message_id
                        })

                        # Determinar estado
                        status_map = {
                            "sent": "Sent",
                            "delivered": "Delivered",
                            "read": "Read",
                            "failed": "Failed",
                            "received": "Delivered"
                        }
                        status = status_map.get(msg_data.get("status", "").lower(), "Pending")

                        if existing:
                            # Actualizar mensaje
                            message = frappe.get_doc("WhatsApp Message", existing)
                            message.status = status
                            # ✅ CORREGIDO: read_at es Datetime, no Check
                            # La API no devuelve isRead en la respuesta de mensajes,
                            # solo podemos inferirlo del status
                            if status == "Read" and not message.read_at:
                                message.read_at = frappe.utils.now_datetime()
                            message.save(ignore_permissions=True)
                            total_updated += 1
                        else:
                            # Crear mensaje
                            timestamp = msg_data.get("timestamp")
                            if timestamp:
                                try:
                                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                except:
                                    timestamp = frappe.utils.now_datetime()
                            else:
                                timestamp = frappe.utils.now_datetime()

                            message = frappe.get_doc({
                                "doctype": "WhatsApp Message",
                                "session": session.name,
                                "conversation": conv.name,
                                "message_id": message_id,
                                "content": msg_data.get("content") or msg_data.get("text_content", ""),
                                "direction": "Outgoing" if msg_data.get("fromMe") else "Incoming",
                                "message_type": msg_data.get("type", "text"),
                                "status": status,
                                "timestamp": timestamp,
                                "from_number": msg_data.get("from") or msg_data.get("sender"),
                                "to_number": msg_data.get("to") or msg_data.get("recipients"),
                                "from_me": msg_data.get("fromMe", False),
                                "has_media": msg_data.get("has_attachment", False),
                                # ✅ CORREGIDO: Eliminado is_read (no existe)
                                # Usamos read_at solo cuando status es "Read"
                                "read_at": timestamp if status == "Read" else None
                            })
                            message.insert(ignore_permissions=True)
                            total_created += 1

                        total_processed += 1

                    except Exception as e:
                        total_errors += 1
                        error_short = str(e)[:100]
                        frappe.log_error(
                            message=f"Message error: {error_short}",
                            title=f"WA Msg - {message_id[:20]}"
                        )

            except Exception as e:
                error_short = str(e)[:100]
                frappe.log_error(
                    message=f"Chat messages error: {error_short}",
                    title=f"WA Chat Msgs - {conv.chat_id[:20]}"
                )

        frappe.db.commit()

        return {
            "processed": total_processed,
            "created": total_created,
            "updated": total_updated,
            "errors": total_errors
        }

    except Exception as e:
        error_msg = str(e)[:150]
        frappe.log_error(
            message=f"Messages sync error: {error_msg}",
            title=f"WA Msg Sync - {session.name[:20]}"
        )
        return {"processed": 0, "created": 0, "updated": 0, "errors": 1}


def _update_session_statistics(session: Any):
    """
    Actualiza las estadísticas de una sesión.

    Args:
        session: Documento WhatsApp Session
    """
    try:
        # Contar contactos
        total_contacts = frappe.db.count("WhatsApp Contact", {"session": session.name})

        # Contar conversaciones
        total_chats = frappe.db.count("WhatsApp Conversation", {"session": session.name})

        # Contar mensajes
        total_messages = frappe.db.count("WhatsApp Message", {"session": session.name})

        # Actualizar sesión
        frappe.db.set_value("WhatsApp Session", session.name, {
            "total_contacts": total_contacts,
            "total_chats": total_chats,  # Corregido: el campo se llama total_chats
            "total_messages_sent": total_messages
            # last_sync removido - campo no existe en el DocType
        })

        frappe.db.commit()

    except Exception as e:
        error_msg = str(e)[:100]
        frappe.log_error(
            message=f"Stats update error: {error_msg}",
            title=f"WA Stats - {session.name[:20]}"
        )

