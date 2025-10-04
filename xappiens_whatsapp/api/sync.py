#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API para sincronización automática de datos de WhatsApp.
Orquesta la sincronización completa de sesiones, contactos, conversaciones y mensajes.
"""

import frappe
from .session import get_session_status, update_session_stats
from .contacts import sync_contacts
from .conversations import sync_conversations
from .messages import sync_messages
from typing import Dict, Any, List


@frappe.whitelist()
def sync_session_data(session_name: str, sync_contacts_flag: bool = True, sync_conversations_flag: bool = True, sync_messages_flag: bool = False) -> Dict[str, Any]:
    """
    Sincroniza todos los datos de una sesión desde el servidor externo.

    Args:
        session_name: Nombre del documento WhatsApp Session
        sync_contacts_flag: Si debe sincronizar contactos
        sync_conversations_flag: Si debe sincronizar conversaciones
        sync_messages_flag: Si debe sincronizar mensajes (lento, recomendado hacer por conversación)

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

        # Registrar actividad
        frappe.get_doc({
            "doctype": "WhatsApp Activity Log",
            "session": session.name,
            "event_type": "full_sync",
            "status": "Success",
            "timestamp": frappe.utils.now(),
            "user": frappe.session.user,
            "details": f"Sincronización completa: {results['sync_status']}"
        }).insert(ignore_permissions=True)
        frappe.db.commit()

        frappe.publish_realtime(
            "sync_progress",
            {"step": "Sincronización completada", "results": results},
            user=frappe.session.user
        )

        return results

    except Exception as e:
        frappe.log_error(f"Error en sincronización completa: {str(e)}")

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

            # Sincronizar solo contactos y conversaciones (no mensajes para ser más rápido)
            sync_result = sync_session_data(
                session_name,
                sync_contacts_flag=True,
                sync_conversations_flag=True,
                sync_messages_flag=False
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
            frappe.log_error(f"Error en auto-sync de sesión {session_name}: {str(e)}")

    # Registrar resultado de auto-sync
    frappe.log_error(
        f"Auto-sync completado: {results['synced']} exitosos, {results['failed']} fallidos",
        "WhatsApp Auto Sync"
    )

    return results


def _create_message_from_data(message_data: Dict, conversation: str, session: Any) -> Any:
    """
    Crea un nuevo documento WhatsApp Message desde datos del servidor.
    (Importado desde messages.py para evitar circular import)
    """
    from .messages import _create_message_from_data as create_msg
    return create_msg(message_data, conversation, session)

