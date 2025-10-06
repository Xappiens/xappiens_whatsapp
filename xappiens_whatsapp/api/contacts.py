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

                # Sincronizar avatar - siempre intentar obtenerlo del servidor
                try:
                    update_contact_avatar(contact.name)
                except:
                    pass  # Continuar sin fallar si no se puede descargar el avatar

            except Exception as e:
                errors += 1
                frappe.log_error(f"Error al sincronizar contacto {contact_id}: {str(e)}")

        frappe.db.commit()

        # Actualizar estadísticas de la sesión
        total_contacts = frappe.db.count("WhatsApp Contact", {"session": session.name})
        try:
            frappe.db.set_value("WhatsApp Session", session.name, "total_contacts", total_contacts)
            frappe.db.commit()
        except:
            # Continuar sin fallar por las estadísticas
            pass


        return {
            "success": True,
            "total_from_server": total,
            "processed": len(contacts_data),
            "created": created,
            "updated": updated,
            "errors": errors
        }

    except Exception as e:
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
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def create_whatsapp_contact(phone_number: str, contact_name: str = None, session_name: str = None) -> Dict[str, Any]:
    """
    Crea un nuevo contacto de WhatsApp manualmente.

    Args:
        phone_number: Número de teléfono del contacto
        contact_name: Nombre del contacto (opcional)
        session_name: Nombre de la sesión de WhatsApp (opcional, usa la sesión por defecto)

    Returns:
        Dict con resultado de la creación
    """
    try:
        # Validar entrada
        if not phone_number or not phone_number.strip():
            return {
                "success": False,
                "message": "El número de teléfono no puede estar vacío"
            }

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

        # Normalizar número de teléfono
        clean_phone = phone_number.strip()

        # Remover todos los espacios y caracteres no numéricos excepto el +
        if clean_phone.startswith('+'):
            # Mantener el + y solo dígitos
            clean_phone = '+' + ''.join(c for c in clean_phone[1:] if c.isdigit())
        else:
            # Si no tiene +, agregarlo y solo dígitos
            clean_phone = '+' + ''.join(c for c in clean_phone if c.isdigit())

        # Validar que el número tenga al menos 10 dígitos (incluyendo el +)
        if len(clean_phone) < 11:
            return {
                "success": False,
                "message": f"El número de teléfono debe tener al menos 10 dígitos: {phone_number} -> {clean_phone}"
            }

        # Validar que solo contenga números y el signo + al inicio
        if not clean_phone[1:].isdigit():
            return {
                "success": False,
                "message": f"El número de teléfono solo puede contener números y el signo + al inicio: {phone_number} -> {clean_phone}"
            }

        # Verificar si el contacto ya existe
        existing = frappe.db.exists("WhatsApp Contact", {
            "session": session_name,
            "phone_number": clean_phone
        })

        if existing:
            return {
                "success": False,
                "message": f"El contacto con número {clean_phone} ya existe"
            }

        # Crear nuevo contacto
        contact = frappe.get_doc({
            "doctype": "WhatsApp Contact",
            "session": session_name,
            "contact_id": clean_phone,
            "phone_number": clean_phone,
            "contact_name": contact_name or clean_phone,
            "is_user": False,
            "is_group": False,
            "is_my_contact": False,
            "is_wa_contact": True,
            "is_blocked": False,
            "is_enterprise": False,
            "is_verified": False,
            "verified_level": "Unverified",
            "last_sync": frappe.utils.now(),
            "sync_status": "Synced"
        })

        contact.insert(ignore_permissions=True)
        frappe.db.commit()

        frappe.log_error(f"Contact created successfully: {contact.name} with phone {clean_phone}")

        # Crear conversación automáticamente después de crear el contacto
        try:
            frappe.log_error(f"Creating conversation for contact: {contact.name}")
            from xappiens_whatsapp.api.conversations import create_whatsapp_conversation
            conversation_result = create_whatsapp_conversation(contact.name, session_name)
            frappe.log_error(f"Conversation result: {conversation_result}")

            if conversation_result.get("success"):
                return {
                    "success": True,
                    "message": f"Contacto y conversación creados exitosamente",
                    "contact_name": contact.name,
                    "contact_id": contact.contact_id,
                    "conversation_name": conversation_result.get("conversation_name"),
                    "conversation_created": True
                }
            else:
                # Si falla la creación de conversación, aún retornar éxito para el contacto
                return {
                    "success": True,
                    "message": f"Contacto creado exitosamente, pero no se pudo crear la conversación: {conversation_result.get('message', 'Error desconocido')}",
                    "contact_name": contact.name,
                    "contact_id": contact.contact_id,
                    "conversation_created": False,
                    "conversation_error": conversation_result.get("message")
                }
        except Exception as e:
            # Si falla la creación de conversación, aún retornar éxito para el contacto
            frappe.log_error(f"Error creating conversation for contact {contact.name}: {str(e)}")
            return {
                "success": True,
                "message": f"Contacto creado exitosamente, pero no se pudo crear la conversación: {str(e)}",
                "contact_name": contact.name,
                "contact_id": contact.contact_id,
                "conversation_created": False,
                "conversation_error": str(e)
            }

    except Exception as e:
        frappe.log_error(f"Error creating WhatsApp contact: {str(e)}")
        return {
            "success": False,
            "message": f"Error al crear contacto: {str(e)}"
        }


@frappe.whitelist()
def create_conversation_from_lead(lead_name: str, phone_number: str) -> Dict[str, Any]:
    """
    Crea una conversación de WhatsApp desde un CRM Lead existente.

    Args:
        lead_name: Nombre del documento CRM Lead
        phone_number: Número de teléfono del lead

    Returns:
        Dict con resultado de la creación
    """
    try:
        # Obtener el lead
        lead = frappe.get_doc("CRM Lead", lead_name)

        # Validar que el lead existe
        if not lead:
            return {
                "success": False,
                "message": "Lead no encontrado"
            }

        # Normalizar el número de teléfono
        clean_phone = phone_number.strip()

        # Remover todos los espacios y caracteres no numéricos excepto el +
        if clean_phone.startswith('+'):
            # Mantener el + y solo dígitos
            clean_phone = '+' + ''.join(c for c in clean_phone[1:] if c.isdigit())
        else:
            # Si no tiene +, agregarlo y solo dígitos
            clean_phone = '+' + ''.join(c for c in clean_phone if c.isdigit())

        # Validar número de teléfono
        if not clean_phone or len(clean_phone) < 10 or not clean_phone[1:].isdigit():
            return {
                "success": False,
                "message": f"Número de teléfono inválido: {phone_number} -> {clean_phone}"
            }

        frappe.log_error(f"Phone validation passed: {clean_phone}")

        # Obtener sesión por defecto
        session_name = frappe.get_value("WhatsApp Settings", "WhatsApp Settings", "default_session")
        if not session_name:
            return {
                "success": False,
                "message": "No hay sesión por defecto configurada"
            }

        # Verificar que la sesión está conectada
        session = frappe.get_doc("WhatsApp Session", session_name)
        if not session.is_connected:
            return {
                "success": False,
                "message": "La sesión de WhatsApp no está conectada"
            }

        # Buscar si ya existe un contacto con este número
        existing_contact = frappe.db.exists("WhatsApp Contact", {
            "phone_number": clean_phone,
            "session": session_name
        })

        if existing_contact:
            # El contacto ya existe, usar ese
            contact_name = existing_contact
            contact = frappe.get_doc("WhatsApp Contact", contact_name)
        else:
            # Crear nuevo contacto
            contact_id = clean_phone
            contact_name = (lead.lead_name or clean_phone)[:140]

            frappe.log_error(f"Creating contact - contact_id: {contact_id}, contact_name: {contact_name}, phone: {clean_phone}")

            try:
                contact = frappe.get_doc({
                    "doctype": "WhatsApp Contact",
                    "session": session_name,
                    "contact_id": contact_id,
                    "phone_number": clean_phone,
                    "contact_name": contact_name,
                    "is_user": False,
                    "is_group": False,
                    "is_my_contact": False,
                    "is_wa_contact": True,
                    "is_blocked": False,
                    "is_enterprise": False,
                    "is_verified": False,
                    "verified_level": "Unverified",
                    "last_sync": frappe.utils.now(),
                    "sync_status": "Synced"
                })

                frappe.log_error(f"Contact doc created successfully, about to insert")
                contact.insert(ignore_permissions=True)
                frappe.log_error(f"Contact inserted successfully: {contact.name}")

            except Exception as e:
                frappe.log_error(f"Error creating contact: {str(e)}")
                raise
            frappe.db.commit()
            contact_name = contact.name

        # Buscar si ya existe una conversación con este contacto
        existing_conversation = frappe.db.exists("WhatsApp Conversation", {
            "session": session_name,
            "contact": contact_name,
            "is_group": False
        })

        if existing_conversation:
            # La conversación ya existe, vincular con el lead si no está vinculada
            frappe.log_error(f"Existing conversation found: {existing_conversation}")
            conversation = frappe.get_doc("WhatsApp Conversation", existing_conversation)
            frappe.log_error(f"Conversation object: {conversation.name}, linked_lead: {conversation.linked_lead}")
            if not conversation.linked_lead:
                conversation.linked_lead = lead_name
                conversation.save()
                frappe.db.commit()
                frappe.log_error(f"Conversation updated with linked_lead: {lead_name}")

            return {
                "success": True,
                "message": "Conversación ya existía, vinculada con el lead",
                "conversation_name": existing_conversation,
                "contact_name": contact_name,
                "already_exists": True
            }

        # Crear nueva conversación
        chat_id = f"{clean_phone.replace('+', '')}@c.us"
        frappe.log_error(f"Creating new conversation with chat_id: {chat_id}")

        conversation = frappe.get_doc({
            "doctype": "WhatsApp Conversation",
            "session": session_name,
            "chat_id": chat_id,
            "conversation_name": lead.lead_name,
            "is_group": False,
            "contact": contact_name,
            "contact_name": lead.lead_name,
            "phone_number": clean_phone,
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
            "priority": "Medium",
            "linked_lead": lead_name
        })

        conversation.insert(ignore_permissions=True)
        frappe.db.commit()

        return {
            "success": True,
            "message": "Conversación creada exitosamente desde lead",
            "conversation_name": conversation.name,
            "contact_name": contact_name,
            "lead_name": lead_name
        }

    except Exception as e:
        frappe.log_error(f"Error creating conversation from lead: {str(e)}")
        return {
            "success": False,
            "message": f"Error al crear conversación desde lead: {str(e)}"
        }


@frappe.whitelist()
def get_leads_count_by_phone(phone_number: str) -> Dict[str, Any]:
    """
    Obtiene la cantidad de leads de CRM que tienen el número de teléfono especificado.

    Args:
        phone_number: Número de teléfono a buscar

    Returns:
        Dict con el conteo de leads encontrados
    """
    try:
        # Validar entrada
        if not phone_number or not phone_number.strip():
            return {
                "success": False,
                "message": "El número de teléfono no puede estar vacío",
                "count": 0
            }

        # Normalizar número de teléfono
        clean_phone = phone_number.strip()
        if not clean_phone.startswith('+'):
            clean_phone = f"+{clean_phone}"

        # Validar que el número tenga al menos 10 dígitos (incluyendo el +)
        if len(clean_phone) < 11:
            return {
                "success": False,
                "message": "El número de teléfono debe tener al menos 10 dígitos",
                "count": 0
            }

        # Validar que solo contenga números y el signo + al inicio
        if not clean_phone[1:].isdigit():
            return {
                "success": False,
                "message": "El número de teléfono solo puede contener números y el signo + al inicio",
                "count": 0
            }

        # Buscar leads con diferentes formatos del número
        search_terms = [
            clean_phone,  # +34657032985
            clean_phone[1:],  # 34657032985 (sin +)
        ]

        # Agregar variaciones adicionales si el número no empieza con +
        if not phone_number.strip().startswith('+'):
            search_terms.append(f"+{phone_number.strip()}")  # +34657032985 (agregar + al original)

        total_count = 0
        leads_found = []

        for term in search_terms:
            leads = frappe.get_all("CRM Lead",
                filters={"mobile_no": term},
                fields=["name", "lead_name", "mobile_no", "status"],
                limit=10  # Limitar para evitar demasiados resultados
            )

            for lead in leads:
                # Evitar duplicados
                if not any(l["name"] == lead["name"] for l in leads_found):
                    leads_found.append(lead)
                    total_count += 1

        return {
            "success": True,
            "count": total_count,
            "leads": leads_found,
            "phone_searched": clean_phone
        }

    except Exception as e:
        frappe.log_error(f"Error getting leads count for phone {phone_number}: {str(e)}")
        return {
            "success": False,
            "message": f"Error al buscar leads: {str(e)}",
            "count": 0
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
        try:
            img_response = requests.get(avatar_url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })

            if img_response.status_code == 200:
                # Verificar que sea una imagen válida
                content_type = img_response.headers.get('content-type', '')
                if not content_type.startswith('image/'):
                    return {"success": False, "message": "URL no es una imagen válida"}

                # Determinar extensión del archivo
                file_extension = 'jpg'
                if 'png' in content_type:
                    file_extension = 'png'
                elif 'gif' in content_type:
                    file_extension = 'gif'
                elif 'webp' in content_type:
                    file_extension = 'webp'

                # Guardar como archivo en Frappe
                file_doc = frappe.get_doc({
                    "doctype": "File",
                    "file_name": f"avatar_{contact.contact_id}.{file_extension}",
                    "attached_to_doctype": "WhatsApp Contact",
                    "attached_to_name": contact.name,
                    "is_private": 0,
                    "content": img_response.content
                })
                file_doc.save(ignore_permissions=True)

                # Actualizar contacto
                contact.profile_pic_url = avatar_url
                contact.profile_pic_thumb = file_doc.file_url
                contact.last_profile_pic_update = frappe.utils.now()
                contact.save(ignore_permissions=True)
                frappe.db.commit()

                return {
                    "success": True,
                    "avatar_url": file_doc.file_url,
                    "message": "Avatar actualizado correctamente"
                }
            else:
                return {"success": False, "message": f"Error HTTP {img_response.status_code} al descargar imagen"}
        except requests.exceptions.RequestException as e:
            return {"success": False, "message": f"Error de conexión: {str(e)}"}
        except Exception as e:
            return {"success": False, "message": f"Error inesperado: {str(e)}"}

    except Exception as e:
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

    # Truncar campos largos para evitar errores de longitud
    # Usar el número de teléfono como nombre si no hay otros datos
    contact_name = (contact_data.get("name") or contact_data.get("pushname") or contact_data.get("number") or contact_id)[:140]
    pushname = (contact_data.get("pushname") or "")[:140]
    short_name = (contact_data.get("shortName") or "")[:140]
    about = (contact_data.get("about") or "")[:140]
    verified_name = (contact_data.get("verifiedName") or "")[:140]

    # Procesar fechas
    first_seen = None
    last_seen = None
    if contact_data.get("firstSeen"):
        from datetime import datetime
        first_seen = datetime.fromtimestamp(contact_data.get("firstSeen"))
    if contact_data.get("lastSeen"):
        from datetime import datetime
        last_seen = datetime.fromtimestamp(contact_data.get("lastSeen"))

    contact = frappe.get_doc({
        "doctype": "WhatsApp Contact",
        "session": session.name,
        "contact_id": contact_id,
        "phone_number": contact_id,
        "contact_name": contact_name,
        "pushname": pushname,
        "short_name": short_name,
        "profile_pic_url": contact_data.get("profilePicUrl"),
        "about": about,
        "last_profile_pic_update": frappe.utils.now() if contact_data.get("profilePicUrl") else None,
        "is_user": contact_data.get("isUser", False),
        "is_group": contact_data.get("isGroup", False),
        "is_my_contact": contact_data.get("isMyContact", False),
        "is_wa_contact": contact_data.get("isWAContact", False),
        "is_blocked": contact_data.get("isBlocked", False),
        "is_enterprise": contact_data.get("isEnterprise", False),
        "is_verified": contact_data.get("isVerified", False),
        "verified_name": verified_name,
        "verified_level": contact_data.get("verifiedLevel"),
        "verification_date": frappe.utils.now() if contact_data.get("isVerified") else None,
        "first_seen": first_seen,
        "last_seen": last_seen,
        "last_sync": frappe.utils.now(),
        "sync_status": "Synced"
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
    # Truncar campos largos para evitar errores de longitud
    contact_name = (contact_data.get("name") or contact_data.get("pushname") or contact_data.get("number") or contact.contact_name)[:140]
    pushname = (contact_data.get("pushname") or "")[:140]
    short_name = (contact_data.get("shortName") or "")[:140]
    about = (contact_data.get("about") or "")[:140]
    verified_name = (contact_data.get("verifiedName") or "")[:140]

    # Procesar fechas
    first_seen = None
    last_seen = None
    if contact_data.get("firstSeen"):
        from datetime import datetime
        first_seen = datetime.fromtimestamp(contact_data.get("firstSeen"))
    if contact_data.get("lastSeen"):
        from datetime import datetime
        last_seen = datetime.fromtimestamp(contact_data.get("lastSeen"))

    contact.contact_name = contact_name
    contact.pushname = pushname
    contact.short_name = short_name
    contact.about = about
    contact.verified_name = verified_name
    contact.is_user = contact_data.get("isUser", False)
    contact.is_group = contact_data.get("isGroup", False)
    contact.is_wa_contact = contact_data.get("isWAContact", False)
    contact.is_my_contact = contact_data.get("isMyContact", False)
    contact.is_blocked = contact_data.get("isBlocked", False)
    contact.is_enterprise = contact_data.get("isEnterprise", False)
    contact.is_verified = contact_data.get("isVerified", False)
    contact.verified_level = contact_data.get("verifiedLevel")
    contact.profile_pic_url = contact_data.get("profilePicUrl")

    # Actualizar fechas si están disponibles
    if first_seen:
        contact.first_seen = first_seen
    if last_seen:
        contact.last_seen = last_seen
    if contact_data.get("profilePicUrl"):
        contact.last_profile_pic_update = frappe.utils.now()
    if contact_data.get("isVerified"):
        contact.verification_date = frappe.utils.now()

    contact.last_sync = frappe.utils.now()
    contact.sync_status = "Synced"

    contact.save(ignore_permissions=True)

