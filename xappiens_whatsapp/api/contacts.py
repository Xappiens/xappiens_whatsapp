#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API para gestión de contactos de WhatsApp.
Sincroniza contactos desde el servidor externo con WhatsApp Contact DocType.
"""

import frappe
from .base import WhatsAppAPIClient
from typing import Dict, Any, List
import requests
import base64


@frappe.whitelist()
def sync_contacts(session_name: str, limit: int = 1000) -> Dict[str, Any]:
    """
    Sincroniza todos los contactos de una sesión desde el servidor externo.

    Args:
        session_name: Nombre del documento WhatsApp Session
        limit: Límite de contactos a sincronizar

    Returns:
        Dict con resultado de la sincronización
    """
    session = frappe.get_doc("WhatsApp Session", session_name)

    if not session.is_connected:
        frappe.throw("La sesión debe estar conectada para sincronizar contactos")

    client = WhatsAppAPIClient(session.session_id)

    try:
        # Obtener contactos del servidor
        response = client.get("/client/getContacts/{sessionId}", params={"limit": limit})

        if not response.get("success"):
            frappe.throw("Error al obtener contactos del servidor")

        contacts_data = response.get("contacts", [])
        total = response.get("total", 0)

        created = 0
        updated = 0
        errors = 0

        for contact_data in contacts_data:
            try:
                contact_id = contact_data.get("id", {}).get("_serialized") or contact_data.get("id")

                if not contact_id:
                    continue

                # Buscar si el contacto ya existe
                existing = frappe.db.exists("WhatsApp Contact", {
                    "session": session.name,
                    "phone_number": contact_id
                })

                if existing:
                    # Actualizar contacto existente
                    contact = frappe.get_doc("WhatsApp Contact", existing)
                    _update_contact_from_data(contact, contact_data, session)
                    updated += 1
                else:
                    # Crear nuevo contacto
                    contact = _create_contact_from_data(contact_data, session)
                    created += 1

                # Sincronizar avatar
                if contact_data.get("profilePicUrl"):
                    try:
                        update_contact_avatar(contact.name, contact_data.get("profilePicUrl"))
                    except:
                        pass  # No fallar si no se puede descargar el avatar

            except Exception as e:
                errors += 1
                frappe.log_error(f"Error al sincronizar contacto {contact_id}: {str(e)}")

        frappe.db.commit()

        # Actualizar estadísticas de la sesión
        session.total_contacts = frappe.db.count("WhatsApp Contact", {"session": session.name})
        session.last_sync = frappe.utils.now()
        session.save(ignore_permissions=True)
        frappe.db.commit()

        # Registrar actividad
        frappe.get_doc({
            "doctype": "WhatsApp Activity Log",
            "session": session.name,
            "event_type": "contacts_sync",
            "status": "Success",
            "timestamp": frappe.utils.now(),
            "user": frappe.session.user,
            "details": f"Sincronizados: {created} nuevos, {updated} actualizados, {errors} errores"
        }).insert(ignore_permissions=True)
        frappe.db.commit()

        return {
            "success": True,
            "total_from_server": total,
            "processed": len(contacts_data),
            "created": created,
            "updated": updated,
            "errors": errors
        }

    except Exception as e:
        frappe.log_error(f"Error en sincronización de contactos: {str(e)}")
        frappe.throw(f"Error al sincronizar contactos: {str(e)}")


@frappe.whitelist()
def get_contact_details(session_name: str, contact_id: str) -> Dict[str, Any]:
    """
    Obtiene detalles completos de un contacto específico.

    Args:
        session_name: Nombre del documento WhatsApp Session
        contact_id: ID del contacto (ej: 34657032985@c.us)

    Returns:
        Dict con detalles del contacto
    """
    session = frappe.get_doc("WhatsApp Session", session_name)
    client = WhatsAppAPIClient(session.session_id)

    try:
        response = client.post("/client/getContactById/{sessionId}", data={"contactId": contact_id})

        if response.get("success"):
            return {
                "success": True,
                "contact": response.get("contact", {})
            }
        else:
            frappe.throw("Error al obtener detalles del contacto")

    except Exception as e:
        frappe.log_error(f"Error al obtener contacto {contact_id}: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def update_contact_avatar(contact_name: str, avatar_url: str = None) -> Dict[str, Any]:
    """
    Actualiza el avatar de un contacto descargándolo del servidor.

    Args:
        contact_name: Nombre del documento WhatsApp Contact
        avatar_url: URL del avatar (opcional, se obtiene del servidor si no se provee)

    Returns:
        Dict con resultado
    """
    contact = frappe.get_doc("WhatsApp Contact", contact_name)
    session = frappe.get_doc("WhatsApp Session", contact.session)

    try:
        # Si no se provee URL, obtenerla del servidor
        if not avatar_url:
            client = WhatsAppAPIClient(session.session_id)
            response = client.post(
                "/client/getProfilePicUrl/{sessionId}",
                data={"contactId": contact.phone_number}
            )

            if response.get("success"):
                avatar_url = response.get("result")
            else:
                return {"success": False, "message": "No se pudo obtener URL del avatar"}

        if not avatar_url or avatar_url == "default":
            return {"success": False, "message": "Contacto sin foto de perfil"}

        # Descargar imagen
        img_response = requests.get(avatar_url, timeout=10)

        if img_response.status_code == 200:
            # Guardar como archivo en Frappe
            file_doc = frappe.get_doc({
                "doctype": "File",
                "file_name": f"avatar_{contact.contact_id}.jpg",
                "attached_to_doctype": "WhatsApp Contact",
                "attached_to_name": contact.name,
                "is_private": 0,
                "content": img_response.content
            })
            file_doc.save(ignore_permissions=True)

            # Actualizar contacto
            contact.profile_pic_url = avatar_url
            contact.avatar = file_doc.file_url
            contact.save(ignore_permissions=True)
            frappe.db.commit()

            return {
                "success": True,
                "avatar_url": file_doc.file_url,
                "message": "Avatar actualizado"
            }
        else:
            return {"success": False, "message": "Error al descargar imagen"}

    except Exception as e:
        frappe.log_error(f"Error al actualizar avatar de contacto {contact.name}: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }


def _create_contact_from_data(contact_data: Dict, session: Any) -> Any:
    """
    Crea un nuevo documento WhatsApp Contact desde datos del servidor.

    Args:
        contact_data: Datos del contacto del servidor
        session: Documento WhatsApp Session

    Returns:
        Documento WhatsApp Contact creado
    """
    contact_id = contact_data.get("id", {}).get("_serialized") or contact_data.get("id")

    contact = frappe.get_doc({
        "doctype": "WhatsApp Contact",
        "session": session.name,
        "contact_id": contact_id,
        "phone_number": contact_id,
        "contact_name": contact_data.get("name") or contact_data.get("pushname") or contact_id,
        "pushname": contact_data.get("pushname"),
        "is_user": contact_data.get("isUser", False),
        "is_wa_contact": contact_data.get("isWAContact", False),
        "is_my_contact": contact_data.get("isMyContact", False),
        "is_blocked": contact_data.get("isBlocked", False),
        "profile_pic_url": contact_data.get("profilePicUrl"),
        "about": contact_data.get("about"),
        "last_sync": frappe.utils.now()
    })

    contact.insert(ignore_permissions=True)
    return contact


def _update_contact_from_data(contact: Any, contact_data: Dict, session: Any):
    """
    Actualiza un documento WhatsApp Contact con datos del servidor.

    Args:
        contact: Documento WhatsApp Contact
        contact_data: Datos del contacto del servidor
        session: Documento WhatsApp Session
    """
    contact.contact_name = contact_data.get("name") or contact_data.get("pushname") or contact.contact_name
    contact.pushname = contact_data.get("pushname")
    contact.is_user = contact_data.get("isUser", False)
    contact.is_wa_contact = contact_data.get("isWAContact", False)
    contact.is_my_contact = contact_data.get("isMyContact", False)
    contact.is_blocked = contact_data.get("isBlocked", False)
    contact.profile_pic_url = contact_data.get("profilePicUrl")
    contact.about = contact_data.get("about")
    contact.last_sync = frappe.utils.now()

    contact.save(ignore_permissions=True)

