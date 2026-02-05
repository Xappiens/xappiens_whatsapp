"""
API Portal para WhatsApp - Endpoints expuestos para el frontend del CRM
Wrapper/proxy sobre la API de Baileys con funcionalidades adicionales
"""

import frappe
from frappe import _
from typing import Dict, Any, Optional
from .base import WhatsAppAPIClient
from .session import get_session_status, get_qr_code, disconnect_session, _resolve_session_doc
from .messages import send_message, send_message_with_media
import requests
from xappiens_whatsapp.utils.settings import get_api_credentials, get_api_base_url


# ==================== SESIONES ====================

@frappe.whitelist()
def portal_get_session_status(session_id: Optional[str] = None):
    """
    Obtener estado de sesión para el portal
    Wrapper sobre get_session_status existente
    """
    return get_session_status(session_id)


@frappe.whitelist()
def portal_get_qr_code(session_id: str):
    """
    Obtener QR code de sesión para el portal
    Wrapper sobre get_qr_code existente
    """
    return get_qr_code(session_id)


@frappe.whitelist()
def portal_connect_session(session_id: str):
    """
    Conectar una sesión de WhatsApp
    Llama a POST /api/sessions/{id}/connect en Baileys
    """
    try:
        settings = get_api_credentials()
        api_base_url = get_api_base_url()

        # Resolver session_db_id desde session_id
        session_doc = _resolve_session_doc(session_id)

        if not session_doc:
            return {
                "success": False,
                "error": f"No se encontró la sesión con ID: {session_id}"
            }

        # Usar session_db_id si está disponible, sino intentar con session_id
        session_identifier = session_doc.session_db_id if session_doc.session_db_id else session_doc.session_id

        if not session_identifier:
            return {
                "success": False,
                "error": "No se encontró identificador válido para la sesión"
            }

        # Llamar al endpoint de conexión de Baileys
        response = requests.post(
            f"{api_base_url}/api/sessions/{session_identifier}/connect",
            headers={
                "X-API-Key": settings.get('api_key'),
                "Content-Type": "application/json"
            },
            timeout=30
        )

        if response.status_code in [200, 201]:
            result = response.json()

            # Actualizar estado en Frappe
            if result.get('success'):
                session_doc.status = "Connecting"
                session_doc.save(ignore_permissions=True)
                frappe.db.commit()

            return {
                "success": True,
                "message": "Sesión iniciada, generando QR o reconectando...",
                "data": result.get('data', {})
            }
        else:
            error_data = response.json() if response.text else {}
            return {
                "success": False,
                "error": error_data.get('message') or f"Error del servidor: {response.status_code}"
            }

    except Exception as e:
        frappe.log_error(f"Error conectando sesión {session_id}: {str(e)}", "WhatsApp Portal Connect")
        return {
            "success": False,
            "error": f"Error interno: {str(e)}"
        }


@frappe.whitelist()
def portal_disconnect_session(session_id: str):
    """
    Desconectar una sesión de WhatsApp
    Wrapper sobre disconnect_session existente
    """
    return disconnect_session(session_id)


@frappe.whitelist()
def portal_restart_session(session_id: str):
    """
    Reiniciar una sesión de WhatsApp
    Llama a POST /api/sessions/{id}/restart en Baileys
    """
    try:
        settings = get_api_credentials()
        api_base_url = get_api_base_url()

        # Resolver session_db_id desde session_id
        session_doc = _resolve_session_doc(session_id)

        if not session_doc:
            return {
                "success": False,
                "error": f"No se encontró la sesión con ID: {session_id}"
            }

        # Usar session_db_id si está disponible
        session_identifier = session_doc.session_db_id if session_doc.session_db_id else session_doc.session_id

        if not session_identifier:
            return {
                "success": False,
                "error": "No se encontró identificador válido para la sesión"
            }

        # Llamar al endpoint de reinicio de Baileys
        response = requests.post(
            f"{api_base_url}/api/sessions/{session_identifier}/restart",
            headers={
                "X-API-Key": settings.get('api_key'),
                "Content-Type": "application/json"
            },
            timeout=30
        )

        if response.status_code in [200, 201]:
            result = response.json()

            # Actualizar estado en Frappe
            if result.get('success'):
                session_doc.status = "Connecting"
                session_doc.save(ignore_permissions=True)
                frappe.db.commit()

            return {
                "success": True,
                "message": "Sesión reiniciada correctamente",
                "data": result.get('data', {})
            }
        else:
            error_data = response.json() if response.text else {}
            return {
                "success": False,
                "error": error_data.get('message') or f"Error del servidor: {response.status_code}"
            }

    except Exception as e:
        frappe.log_error(f"Error reiniciando sesión {session_id}: {str(e)}", "WhatsApp Portal Restart")
        return {
            "success": False,
            "error": f"Error interno: {str(e)}"
        }


# ==================== MENSAJES ====================

@frappe.whitelist()
def portal_send_message(
    conversation_id: str,
    message: str,
    message_type: str = "text",
    file_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Enviar mensaje (wrapper sobre funciones existentes)
    Soporta: text, image (con file_path)
    """
    if file_path:
        return send_message_with_media(conversation_id, message, file_path)
    else:
        return send_message(conversation_id, message, message_type)


@frappe.whitelist()
def portal_send_video(
    conversation_id: str,
    video_url: str,
    caption: Optional[str] = None
) -> Dict[str, Any]:
    """
    Enviar video usando la API de Baileys
    POST /api/messages/{sessionId}/send con type=video
    """
    try:
        conversation = frappe.get_doc("WhatsApp Conversation", conversation_id)
        session = frappe.get_doc("WhatsApp Session", conversation.session)

        if not session.is_connected:
            return {
                "success": False,
                "message": "La sesión no está conectada"
            }

        client = WhatsAppAPIClient(session.session_id)

        # Normalizar número de teléfono
        to_number = conversation.phone_number or conversation.chat_id
        if to_number:
            normalized = to_number.replace("+", "").replace(" ", "")
            if "@" not in normalized:
                to_number = f"{normalized}@s.whatsapp.net"
            else:
                to_number = normalized.replace("@c.us", "@s.whatsapp.net")

        # Enviar video según documentación de Baileys
        response = client.post(
            f"/api/messages/{session.session_id}/send",
            data={
                "to": to_number,
                "message": {
                    "video": {
                        "url": video_url
                    },
                    "caption": caption or ""
                },
                "type": "video"
            },
            use_session_id=False
        )

        if response.get("success"):
            # Guardar mensaje en DocType (similar a send_message)
            payload = response.get("data") or {}
            message_data = payload.get("message", {})
            message_id = (
                message_data.get("id", {}).get("_serialized")
                if isinstance(message_data.get("id"), dict)
                else message_data.get("id")
            ) or payload.get("messageId") or frappe.generate_hash(length=20)

            message_doc = frappe.get_doc({
                "doctype": "WhatsApp Message",
                "session": session.name,
                "conversation": conversation_id,
                "contact": conversation.contact,
                "message_id": message_id,
                "content": caption or "[Video]",
                "direction": "Outgoing",
                "message_type": "video",
                "status": "sent",
                "timestamp": frappe.utils.now_datetime(),
                "from_number": session.phone_number,
                "to_number": to_number,
                "from_me": True,
                "has_media": True,
                "media_url": video_url
            })
            message_doc.insert(ignore_permissions=True)

            # Actualizar estadísticas
            frappe.db.set_value("WhatsApp Session", session.name, "total_messages_sent",
                               (session.total_messages_sent or 0) + 1)
            frappe.db.set_value("WhatsApp Conversation", conversation_id, "last_message", caption or "[Video]")
            frappe.db.set_value("WhatsApp Conversation", conversation_id, "last_message_time", frappe.utils.now_datetime())
            frappe.db.commit()

            return {
                "success": True,
                "message": "Video enviado correctamente",
                "message_id": message_id
            }
        else:
            return {
                "success": False,
                "message": response.get('message', 'Error enviando video')
            }

    except Exception as e:
        frappe.log_error(f"Error enviando video: {str(e)}", "WhatsApp Portal Send Video")
        return {
            "success": False,
            "message": f"Error al enviar video: {str(e)}"
        }


@frappe.whitelist()
def portal_send_audio(
    conversation_id: str,
    audio_url: str,
    ptt: bool = False
) -> Dict[str, Any]:
    """
    Enviar audio usando la API de Baileys
    POST /api/messages/{sessionId}/send con type=audio
    """
    try:
        conversation = frappe.get_doc("WhatsApp Conversation", conversation_id)
        session = frappe.get_doc("WhatsApp Session", conversation.session)

        if not session.is_connected:
            return {
                "success": False,
                "message": "La sesión no está conectada"
            }

        client = WhatsAppAPIClient(session.session_id)

        # Normalizar número de teléfono
        to_number = conversation.phone_number or conversation.chat_id
        if to_number:
            normalized = to_number.replace("+", "").replace(" ", "")
            if "@" not in normalized:
                to_number = f"{normalized}@s.whatsapp.net"
            else:
                to_number = normalized.replace("@c.us", "@s.whatsapp.net")

        # Enviar audio según documentación de Baileys
        response = client.post(
            f"/api/messages/{session.session_id}/send",
            data={
                "to": to_number,
                "message": {
                    "audio": {
                        "url": audio_url
                    },
                    "ptt": ptt
                },
                "type": "audio"
            },
            use_session_id=False
        )

        if response.get("success"):
            # Guardar mensaje en DocType
            payload = response.get("data") or {}
            message_data = payload.get("message", {})
            message_id = (
                message_data.get("id", {}).get("_serialized")
                if isinstance(message_data.get("id"), dict)
                else message_data.get("id")
            ) or payload.get("messageId") or frappe.generate_hash(length=20)

            message_doc = frappe.get_doc({
                "doctype": "WhatsApp Message",
                "session": session.name,
                "conversation": conversation_id,
                "contact": conversation.contact,
                "message_id": message_id,
                "content": "[Audio]",
                "direction": "Outgoing",
                "message_type": "audio",
                "status": "sent",
                "timestamp": frappe.utils.now_datetime(),
                "from_number": session.phone_number,
                "to_number": to_number,
                "from_me": True,
                "has_media": True,
                "media_url": audio_url
            })
            message_doc.insert(ignore_permissions=True)

            # Actualizar estadísticas
            frappe.db.set_value("WhatsApp Session", session.name, "total_messages_sent",
                               (session.total_messages_sent or 0) + 1)
            frappe.db.set_value("WhatsApp Conversation", conversation_id, "last_message", "[Audio]")
            frappe.db.set_value("WhatsApp Conversation", conversation_id, "last_message_time", frappe.utils.now_datetime())
            frappe.db.commit()

            return {
                "success": True,
                "message": "Audio enviado correctamente",
                "message_id": message_id
            }
        else:
            return {
                "success": False,
                "message": response.get('message', 'Error enviando audio')
            }

    except Exception as e:
        frappe.log_error(f"Error enviando audio: {str(e)}", "WhatsApp Portal Send Audio")
        return {
            "success": False,
            "message": f"Error al enviar audio: {str(e)}"
        }


@frappe.whitelist()
def portal_send_document(
    conversation_id: str,
    document_url: str,
    filename: str,
    caption: Optional[str] = None
) -> Dict[str, Any]:
    """
    Enviar documento usando la API de Baileys
    POST /api/messages/{sessionId}/send con type=document
    """
    try:
        conversation = frappe.get_doc("WhatsApp Conversation", conversation_id)
        session = frappe.get_doc("WhatsApp Session", conversation.session)

        if not session.is_connected:
            return {
                "success": False,
                "message": "La sesión no está conectada"
            }

        client = WhatsAppAPIClient(session.session_id)

        # Normalizar número de teléfono
        to_number = conversation.phone_number or conversation.chat_id
        if to_number:
            normalized = to_number.replace("+", "").replace(" ", "")
            if "@" not in normalized:
                to_number = f"{normalized}@s.whatsapp.net"
            else:
                to_number = normalized.replace("@c.us", "@s.whatsapp.net")

        # Detectar mimetype básico
        mimetype = "application/pdf"
        if filename.lower().endswith(('.doc', '.docx')):
            mimetype = "application/msword"
        elif filename.lower().endswith(('.xls', '.xlsx')):
            mimetype = "application/vnd.ms-excel"

        # Enviar documento según documentación de Baileys
        response = client.post(
            f"/api/messages/{session.session_id}/send",
            data={
                "to": to_number,
                "message": {
                    "document": {
                        "url": document_url,
                        "fileName": filename,
                        "mimetype": mimetype
                    },
                    "caption": caption or ""
                },
                "type": "document"
            },
            use_session_id=False
        )

        if response.get("success"):
            # Guardar mensaje en DocType
            payload = response.get("data") or {}
            message_data = payload.get("message", {})
            message_id = (
                message_data.get("id", {}).get("_serialized")
                if isinstance(message_data.get("id"), dict)
                else message_data.get("id")
            ) or payload.get("messageId") or frappe.generate_hash(length=20)

            message_doc = frappe.get_doc({
                "doctype": "WhatsApp Message",
                "session": session.name,
                "conversation": conversation_id,
                "contact": conversation.contact,
                "message_id": message_id,
                "content": caption or filename,
                "direction": "Outgoing",
                "message_type": "document",
                "status": "sent",
                "timestamp": frappe.utils.now_datetime(),
                "from_number": session.phone_number,
                "to_number": to_number,
                "from_me": True,
                "has_media": True,
                "media_url": document_url
            })
            message_doc.insert(ignore_permissions=True)

            # Actualizar estadísticas
            frappe.db.set_value("WhatsApp Session", session.name, "total_messages_sent",
                               (session.total_messages_sent or 0) + 1)
            frappe.db.set_value("WhatsApp Conversation", conversation_id, "last_message", caption or filename)
            frappe.db.set_value("WhatsApp Conversation", conversation_id, "last_message_time", frappe.utils.now_datetime())
            frappe.db.commit()

            return {
                "success": True,
                "message": "Documento enviado correctamente",
                "message_id": message_id
            }
        else:
            return {
                "success": False,
                "message": response.get('message', 'Error enviando documento')
            }

    except Exception as e:
        frappe.log_error(f"Error enviando documento: {str(e)}", "WhatsApp Portal Send Document")
        return {
            "success": False,
            "message": f"Error al enviar documento: {str(e)}"
        }


@frappe.whitelist()
def portal_send_location(
    conversation_id: str,
    latitude: float,
    longitude: float,
    name: Optional[str] = None,
    address: Optional[str] = None
) -> Dict[str, Any]:
    """
    Enviar ubicación usando la API de Baileys
    POST /api/messages/{sessionId}/send con type=location
    """
    try:
        conversation = frappe.get_doc("WhatsApp Conversation", conversation_id)
        session = frappe.get_doc("WhatsApp Session", conversation.session)

        if not session.is_connected:
            return {
                "success": False,
                "message": "La sesión no está conectada"
            }

        client = WhatsAppAPIClient(session.session_id)

        # Normalizar número de teléfono
        to_number = conversation.phone_number or conversation.chat_id
        if to_number:
            normalized = to_number.replace("+", "").replace(" ", "")
            if "@" not in normalized:
                to_number = f"{normalized}@s.whatsapp.net"
            else:
                to_number = normalized.replace("@c.us", "@s.whatsapp.net")

        # Enviar ubicación según documentación de Baileys
        location_data = {
            "degreesLatitude": latitude,
            "degreesLongitude": longitude
        }
        if name:
            location_data["name"] = name
        if address:
            location_data["address"] = address

        response = client.post(
            f"/api/messages/{session.session_id}/send",
            data={
                "to": to_number,
                "message": {
                    "location": location_data
                },
                "type": "location"
            },
            use_session_id=False
        )

        if response.get("success"):
            # Guardar mensaje en DocType
            payload = response.get("data") or {}
            message_data = payload.get("message", {})
            message_id = (
                message_data.get("id", {}).get("_serialized")
                if isinstance(message_data.get("id"), dict)
                else message_data.get("id")
            ) or payload.get("messageId") or frappe.generate_hash(length=20)

            message_doc = frappe.get_doc({
                "doctype": "WhatsApp Message",
                "session": session.name,
                "conversation": conversation_id,
                "contact": conversation.contact,
                "message_id": message_id,
                "content": f"📍 {name or 'Ubicación'}",
                "direction": "Outgoing",
                "message_type": "location",
                "status": "sent",
                "timestamp": frappe.utils.now_datetime(),
                "from_number": session.phone_number,
                "to_number": to_number,
                "from_me": True,
                "has_media": False
            })
            message_doc.insert(ignore_permissions=True)

            # Actualizar estadísticas
            frappe.db.set_value("WhatsApp Session", session.name, "total_messages_sent",
                               (session.total_messages_sent or 0) + 1)
            frappe.db.set_value("WhatsApp Conversation", conversation_id, "last_message", f"📍 {name or 'Ubicación'}")
            frappe.db.set_value("WhatsApp Conversation", conversation_id, "last_message_time", frappe.utils.now_datetime())
            frappe.db.commit()

            return {
                "success": True,
                "message": "Ubicación enviada correctamente",
                "message_id": message_id
            }
        else:
            return {
                "success": False,
                "message": response.get('message', 'Error enviando ubicación')
            }

    except Exception as e:
        frappe.log_error(f"Error enviando ubicación: {str(e)}", "WhatsApp Portal Send Location")
        return {
            "success": False,
            "message": f"Error al enviar ubicación: {str(e)}"
        }


@frappe.whitelist()
def portal_send_contact(
    conversation_id: str,
    contact_name: str,
    phone_number: str,
    vcard: Optional[str] = None
) -> Dict[str, Any]:
    """
    Enviar contacto usando la API de Baileys
    POST /api/messages/{sessionId}/send con type=contact
    """
    try:
        conversation = frappe.get_doc("WhatsApp Conversation", conversation_id)
        session = frappe.get_doc("WhatsApp Session", conversation.session)

        if not session.is_connected:
            return {
                "success": False,
                "message": "La sesión no está conectada"
            }

        client = WhatsAppAPIClient(session.session_id)

        # Normalizar número de teléfono
        to_number = conversation.phone_number or conversation.chat_id
        if to_number:
            normalized = to_number.replace("+", "").replace(" ", "")
            if "@" not in normalized:
                to_number = f"{normalized}@s.whatsapp.net"
            else:
                to_number = normalized.replace("@c.us", "@s.whatsapp.net")

        # Generar vCard si no se proporciona
        if not vcard:
            vcard = f"""BEGIN:VCARD
VERSION:3.0
FN:{contact_name}
TEL;TYPE=CELL:{phone_number}
END:VCARD"""

        # Enviar contacto según documentación de Baileys
        response = client.post(
            f"/api/messages/{session.session_id}/send",
            data={
                "to": to_number,
                "message": {
                    "contacts": {
                        "displayName": contact_name,
                        "contacts": [
                            {
                                "vcard": vcard
                            }
                        ]
                    }
                },
                "type": "contact"
            },
            use_session_id=False
        )

        if response.get("success"):
            # Guardar mensaje en DocType
            payload = response.get("data") or {}
            message_data = payload.get("message", {})
            message_id = (
                message_data.get("id", {}).get("_serialized")
                if isinstance(message_data.get("id"), dict)
                else message_data.get("id")
            ) or payload.get("messageId") or frappe.generate_hash(length=20)

            message_doc = frappe.get_doc({
                "doctype": "WhatsApp Message",
                "session": session.name,
                "conversation": conversation_id,
                "contact": conversation.contact,
                "message_id": message_id,
                "content": f"👤 {contact_name}",
                "direction": "Outgoing",
                "message_type": "contact",
                "status": "sent",
                "timestamp": frappe.utils.now_datetime(),
                "from_number": session.phone_number,
                "to_number": to_number,
                "from_me": True,
                "has_media": False
            })
            message_doc.insert(ignore_permissions=True)

            # Actualizar estadísticas
            frappe.db.set_value("WhatsApp Session", session.name, "total_messages_sent",
                               (session.total_messages_sent or 0) + 1)
            frappe.db.set_value("WhatsApp Conversation", conversation_id, "last_message", f"👤 {contact_name}")
            frappe.db.set_value("WhatsApp Conversation", conversation_id, "last_message_time", frappe.utils.now_datetime())
            frappe.db.commit()

            return {
                "success": True,
                "message": "Contacto enviado correctamente",
                "message_id": message_id
            }
        else:
            return {
                "success": False,
                "message": response.get('message', 'Error enviando contacto')
            }

    except Exception as e:
        frappe.log_error(f"Error enviando contacto: {str(e)}", "WhatsApp Portal Send Contact")
        return {
            "success": False,
            "message": f"Error al enviar contacto: {str(e)}"
        }


@frappe.whitelist()
def portal_mark_chat_as_read(conversation_id: str) -> Dict[str, Any]:
    """
    Marcar mensajes de un chat como leídos
    PUT /api/messages/{sessionId}/{chatId}/read
    """
    try:
        conversation = frappe.get_doc("WhatsApp Conversation", conversation_id)
        session = frappe.get_doc("WhatsApp Session", conversation.session)

        if not session.is_connected:
            return {
                "success": False,
                "message": "La sesión no está conectada"
            }

        client = WhatsAppAPIClient(session.session_id)

        # Normalizar chat_id
        chat_id = conversation.chat_id or conversation.phone_number
        if chat_id:
            normalized = chat_id.replace("+", "").replace(" ", "")
            if "@" not in normalized:
                chat_id = f"{normalized}@s.whatsapp.net"
            else:
                chat_id = normalized.replace("@c.us", "@s.whatsapp.net")

        # Marcar como leído usando el método del cliente base
        response = client.mark_chat_as_read(chat_id)

        if response.get("success"):
            # Actualizar contador de no leídos en Frappe
            frappe.db.set_value("WhatsApp Conversation", conversation_id, "unread_count", 0)

            # Marcar mensajes como leídos en Frappe
            frappe.db.sql("""
                UPDATE `tabWhatsApp Message`
                SET is_read = 1
                WHERE conversation = %s AND direction = 'Incoming' AND is_read = 0
            """, (conversation_id,))

            frappe.db.commit()

            return {
                "success": True,
                "message": "Mensajes marcados como leídos"
            }
        else:
            return {
                "success": False,
                "message": response.get('message', 'Error marcando como leído')
            }

    except Exception as e:
        frappe.log_error(f"Error marcando chat como leído: {str(e)}", "WhatsApp Portal Mark Read")
        return {
            "success": False,
            "message": f"Error al marcar como leído: {str(e)}"
        }

