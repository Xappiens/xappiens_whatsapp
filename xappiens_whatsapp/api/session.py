"""
API para gestión de sesiones de WhatsApp
"""

import frappe
import requests
import json
import base64
from io import BytesIO
from PIL import Image
import qrcode
from typing import Optional
from xappiens_whatsapp.utils.settings import get_api_credentials, get_api_base_url
from .base import WhatsAppAPIClient



@frappe.whitelist()
def test_connection():
    """
    Probar la conexión con el servidor de WhatsApp
    """
    try:
        settings = get_api_credentials()
        api_base_url = get_api_base_url()

        if not settings or not api_base_url:
            return {
                "success": False,
                "error": "Configuración de WhatsApp no encontrada"
            }

        # Probar autenticación
        login_response = requests.post(
            f"{api_base_url}/api/auth/login",
            json={
                "identifier": settings.get('email'),
                "password": settings.get('password')
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        if login_response.status_code == 200:
            login_data = login_response.json()
            if login_data.get('success') and login_data.get('data', {}).get('accessToken'):
                access_token = login_data['data']['accessToken']

                return {
                    "success": True,
                    "message": "Conexión exitosa con el servidor de WhatsApp",
                    "data": {
                        "token": access_token,
                        "user": login_data.get('data', {}).get('user', {}).get('email', 'Usuario desconocido')
                    }
                }
            else:
                return {
                    "success": False,
                    "error": f"Error de autenticación: {login_data.get('message', 'Credenciales inválidas')}"
            }
        else:
            error_data = login_response.json() if login_response.text else {}
            return {
                "success": False,
                "error": f"Error de conexión: {login_response.status_code} - {error_data.get('error', login_response.text[:200])}"
            }

    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": "No se puede conectar al servidor de WhatsApp. Verifica la URL y que el servidor esté funcionando."
        }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Timeout al conectar con el servidor de WhatsApp"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error inesperado: {str(e)}"
        }


def _resolve_session_doc(session_ref: Optional[str] = None):
    """Obtiene el documento de sesión a partir de un nombre o session_id."""
    session_doc = None

    if session_ref:
        if frappe.db.exists("WhatsApp Session", session_ref):
            session_doc = frappe.get_doc("WhatsApp Session", session_ref)
        else:
            existing = frappe.db.get_value("WhatsApp Session", {"session_id": session_ref}, "name")
            if existing:
                session_doc = frappe.get_doc("WhatsApp Session", existing)

    if not session_doc:
        default_session = frappe.db.get_single_value("WhatsApp Settings", "default_session")
        if default_session and frappe.db.exists("WhatsApp Session", default_session):
            session_doc = frappe.get_doc("WhatsApp Session", default_session)

    if not session_doc:
        any_session = frappe.db.get_value(
            "WhatsApp Session",
            {"is_active": 1},
            "name"
        )
        if any_session:
            session_doc = frappe.get_doc("WhatsApp Session", any_session)

    return session_doc


def _extract_sessions(payload: dict) -> list:
    """Normaliza la respuesta del servidor para obtener la lista de sesiones."""
    if not payload:
        return []

    data = payload.get("data")
    if isinstance(data, dict):
        candidates = data.get("items") or data.get("sessions") or data.get("data")
        if isinstance(candidates, list):
            return candidates
    elif isinstance(data, list):
        return data

    sessions = payload.get("sessions")
    if isinstance(sessions, list):
        return sessions

    return []


@frappe.whitelist()
def get_session_status(session_id: Optional[str] = None):
    """
    Obtener el estado actual de una sesión de WhatsApp
    """
    try:
        session_doc = _resolve_session_doc(session_id)

        if not session_doc:
            return {
                "success": False,
                "error": "No hay sesión de WhatsApp configurada"
            }

        client = WhatsAppAPIClient()
        response = client.get_sessions(limit=100)

        if not response.get("success"):
            return {
                "success": False,
                "error": response.get("message") or "Error obteniendo sesiones"
            }

        sessions = _extract_sessions(response)

        matched_session = None
        for remote in sessions:
            if remote.get("sessionId") == session_doc.session_id:
                matched_session = remote
                break
            if session_doc.session_db_id and str(remote.get("id")) == str(session_doc.session_db_id):
                matched_session = remote
                break

        if not matched_session:
            # Considerar la sesión como desconectada si no aparece en el listado
            session_doc.is_connected = 0
            session_doc.status = "Disconnected"
            session_doc.save(ignore_permissions=True)
            frappe.db.commit()
            return {
                "success": True,
                "data": {
                    "id": session_doc.session_db_id,
                    "sessionId": session_doc.session_id,
                    "status": "disconnected",
                    "is_connected": 0,
                    "phone_number": session_doc.phone_number,
                    "last_activity": session_doc.last_seen
                }
            }

        session_status = (matched_session.get("status") or "disconnected").lower()
        is_connected = 1 if session_status == "connected" else 0
        phone_number = matched_session.get("phoneNumber") or matched_session.get("msisdn") or session_doc.phone_number
        last_activity = matched_session.get("lastActivity") or matched_session.get("lastSeen")

        # Mapear estado al DocType
        frappe_status = "Disconnected"
        if session_status == "connected":
            frappe_status = "Connected"
        elif session_status == "connecting":
            frappe_status = "Connecting"
        elif session_status in ("qr_code", "qr_code_required"):
            frappe_status = "QR Code Required"
        elif session_status == "error":
            frappe_status = "Error"

        session_doc.status = frappe_status
        session_doc.is_connected = is_connected
        if phone_number:
            session_doc.phone_number = phone_number

        if last_activity:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(str(last_activity).replace('Z', '+00:00'))
                session_doc.last_seen = dt.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                session_doc.last_seen = last_activity

        if matched_session.get("id"):
            session_doc.session_db_id = matched_session.get("id")

        session_doc.save(ignore_permissions=True)
        frappe.db.commit()

        return {
            "success": True,
            "data": {
                "id": matched_session.get("id"),
                "sessionId": matched_session.get("sessionId"),
                "status": matched_session.get("status"),
                "is_connected": is_connected,
                "phone_number": phone_number,
                "last_activity": last_activity
            }
        }

    except Exception as e:
        print(f"Error obteniendo estado de sesión WhatsApp: {str(e)[:100]}")
        return {
            "success": False,
            "error": f"Error inesperado: {str(e)[:100]}"
        }


@frappe.whitelist()
def create_session(session_id, session_name, description=""):
    """
    Crear una nueva sesión de WhatsApp en el servidor
    """
    try:
        # Validar session_id según documentación (3-100 chars, alphanumeric + _ -)
        import re
        if not re.match(r'^[a-zA-Z0-9_-]{3,100}$', session_id):
            return {
                "success": False,
                "error": "ID de sesión inválido. Debe tener 3-100 caracteres alfanuméricos, guiones bajos o guiones"
            }

        # Validar session_name (1-255 chars)
        if not session_name or len(session_name) > 255:
            return {
                "success": False,
                "error": "Nombre de sesión inválido. Debe tener entre 1 y 255 caracteres"
            }

        # Obtener credenciales de configuración
        settings = get_api_credentials()
        api_base_url = get_api_base_url()

        if not settings or not api_base_url:
            return {
                "success": False,
                "error": "Configuración de WhatsApp no encontrada"
            }

        # Obtener token JWT fresco
        login_response = requests.post(
            f"{api_base_url}/api/auth/login",
            json={
                "identifier": settings.get('email'),
                "password": settings.get('password')
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        if login_response.status_code != 200:
            return {
                "success": False,
                "error": "Error de autenticación al crear sesión"
            }

        login_data = login_response.json()
        if not login_data.get('success') or not login_data.get('data', {}).get('accessToken'):
            return {
                "success": False,
                "error": "Token de acceso no obtenido"
            }

        access_token = login_data['data']['accessToken']

        # Preparar datos para el servidor
        session_data = {
            "session_id": session_id,
            "session_name": session_name,
            "description": description,
            "user_id": settings.get('api_user_id'),
            "organization_id": settings.get('organization_id')
        }

        # Crear nueva sesión en el servidor
        create_data = {
            "sessionId": session_id,
            "sessionName": session_name
        }

        # Solo agregar phoneNumber si está definido y no está vacío
        phone_number = settings.get('phone_number')
        if phone_number and phone_number.strip():
            create_data["phoneNumber"] = phone_number.strip()

        create_response = requests.post(
            f"{api_base_url}/api/sessions",
            json=create_data,
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-API-Key": settings.get('api_key'),
                "Content-Type": "application/json"
            },
            timeout=30
        )

        if create_response.status_code in [200, 201]:
            create_data = create_response.json()

            if create_data.get('success'):
                # El ID está en data.session.id según la respuesta real
                session_data = create_data.get('data', {}).get('session', {})
                session_id_created = session_data.get('id')

                if not session_id_created:
                    return {
                        "success": False,
                        "error": "No se pudo obtener el ID de la sesión creada"
                    }

                # Iniciar conexión de la sesión
                connect_response = requests.post(
                    f"{api_base_url}/api/sessions/{session_id_created}/connect",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "X-API-Key": settings.get('api_key'),
                        "Content-Type": "application/json"
                    },
                    timeout=30
                )

                # Obtener estado actualizado de la sesión
                status_response = requests.get(
                    f"{api_base_url}/api/sessions/{session_id_created}/status",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "X-API-Key": settings.get('api_key'),
                        "Content-Type": "application/json"
                    },
                    timeout=30
                )

                # Determinar estado final
                final_status = "Connecting"
                is_connected = 0

                if status_response.status_code == 200:
                    status_data = status_response.json()
                    if status_data.get('success'):
                        session_status = status_data.get('data', {}).get('status', 'disconnected')
                        if session_status == 'connected':
                            final_status = "Connected"
                            is_connected = 1
                        elif session_status == 'disconnected':
                            final_status = "Disconnected"
                            is_connected = 0
                        else:
                            final_status = "Connecting"
                            is_connected = 0

                # Obtener QR code (con retry)
                qr_code = ""

                for attempt in range(3):  # 3 intentos
                    qr_response = requests.get(
                        f"{api_base_url}/api/sessions/{session_id_created}/qr",
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "X-API-Key": settings.get('api_key'),
                            "Content-Type": "application/json"
                        },
                        timeout=30
                    )

                    if qr_response.status_code == 200:
                        qr_data = qr_response.json()
                        if qr_data.get('success') and qr_data.get('data', {}).get('qrCode'):
                            qr_code_raw = qr_data['data']['qrCode']

                            # Según la documentación, viene como "data:image/png;base64,..."
                            if qr_code_raw.startswith('data:image'):
                                # Extraer solo el base64 después de la coma
                                qr_code = qr_code_raw.split(',')[1] if ',' in qr_code_raw else qr_code_raw
                            else:
                                # Si no viene como data URL, usar tal como está
                                qr_code = qr_code_raw

                            break

                    # Esperar 2 segundos antes del siguiente intento
                    if attempt < 2:
                        import time
                        time.sleep(2)

                # Crear registro en Frappe
                try:
                    session_doc = frappe.get_doc({
                        "doctype": "WhatsApp Session",
                        "session_id": session_id,
                        "session_name": session_name,
                        "description": description,
                        "status": final_status,
                        "is_connected": is_connected,
                        "is_active": 1
                    })
                    session_doc.insert(ignore_permissions=True)
                except:
                    pass  # Ignorar si ya existe

                return {
                    "success": True,
                    "message": f"Sesión '{session_id}' creada exitosamente",
                    "qr_code": qr_code,
                    "session_id": session_id,
                    "status": final_status
                }
            else:
                return {
                    "success": False,
                    "error": f"Error creando sesión: {create_data.get('message', 'Error desconocido')}"
                }
        else:
            error_data = create_response.json() if create_response.text else {}
            return {
                "success": False,
                "error": f"Error del servidor: {create_response.status_code} - {error_data.get('error', create_response.text[:200])}"
            }

    except Exception as e:
        frappe.log_error(f"Error creando sesión WhatsApp: {str(e)}")
        return {
            "success": False,
            "error": f"Error interno: {str(e)}"
        }




@frappe.whitelist()
def disconnect_session(session_id):
    """
    Desconectar una sesión de WhatsApp
    """
    try:
        settings = get_api_credentials()
        api_base_url = get_api_base_url()

        # Llamar al servidor de WhatsApp
        response = requests.delete(
            f"{api_base_url}/api/sessions/{session_id}",
            headers={
                "Authorization": f"Bearer {settings.get('api_key')}",
                "Content-Type": "application/json"
            },
            timeout=30
        )

        if response.status_code == 200:
            # Actualizar estado en Frappe
            session_doc = frappe.get_doc("WhatsApp Session", {"session_id": session_id})
            if session_doc:
                session_doc.status = "disconnected"
                session_doc.is_connected = 0
                session_doc.is_active = 0
                session_doc.save(ignore_permissions=True)

            return {
                "success": True,
                "message": "Sesión desconectada exitosamente"
            }
        else:
            return {
                "success": False,
                "error": f"Error del servidor: {response.status_code}"
            }

    except Exception as e:
        frappe.log_error(f"Error desconectando sesión: {str(e)}")
        return {
            "success": False,
            "error": f"Error interno: {str(e)}"
        }


@frappe.whitelist()
def get_qr_code(session_id):
    """
    Obtener el código QR actual de una sesión
    """
    try:
        settings = get_api_credentials()
        api_base_url = get_api_base_url()

        # Llamar al servidor de WhatsApp
        response = requests.get(
            f"{api_base_url}/api/sessions/{session_id}/qr",
            headers={
                "Authorization": f"Bearer {settings.get('api_key')}",
                "Content-Type": "application/json"
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            qr_code = generate_qr_code(result.get('qr_data', ''))

            return {
                "success": True,
                "qr_code": qr_code
            }
        else:
            return {
                "success": False,
                "error": f"Error del servidor: {response.status_code}"
            }

    except Exception as e:
        frappe.log_error(f"Error obteniendo QR code: {str(e)}")
        return {
            "success": False,
            "error": f"Error interno: {str(e)}"
        }


def generate_qr_code(qr_data):
    """
    Generar código QR como imagen base64
    """
    try:
        if not qr_data:
            return ""

        # Crear código QR
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)

        # Crear imagen
        img = qr.make_image(fill_color="black", back_color="white")

        # Convertir a base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()

        return img_str

    except Exception as e:
        frappe.log_error(f"Error generando QR code: {str(e)}")
        return ""


@frappe.whitelist()
def list_sessions():
    """
    Listar todas las sesiones disponibles
    """
    try:
        settings = get_api_credentials()
        api_base_url = get_api_base_url()

        # Llamar al servidor de WhatsApp
        response = requests.get(
            f"{api_base_url}/api/sessions",
            headers={
                "Authorization": f"Bearer {settings.get('api_key')}",
                "Content-Type": "application/json"
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "sessions": result.get('sessions', [])
            }
        else:
            return {
                "success": False,
                "error": f"Error del servidor: {response.status_code}"
        }

    except Exception as e:
        frappe.log_error(f"Error listando sesiones: {str(e)}")
        return {
            "success": False,
            "error": f"Error interno: {str(e)}"
        }
