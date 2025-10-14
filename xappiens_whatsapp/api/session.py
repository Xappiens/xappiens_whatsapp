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
from xappiens_whatsapp.utils.settings import get_api_credentials, get_api_base_url



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


@frappe.whitelist()
def get_session_status(session_id):
    """
    Obtener el estado actual de una sesión de WhatsApp
    """
    try:
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
                "error": "Error de autenticación al obtener estado"
            }

        login_data = login_response.json()
        if not login_data.get('success') or not login_data.get('data', {}).get('accessToken'):
            return {
                "success": False,
                "error": "Token de acceso no obtenido"
            }

        access_token = login_data['data']['accessToken']

        # Buscar la sesión por session_id en la lista de sesiones
        sessions_response = requests.get(
            f"{api_base_url}/api/sessions",
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-API-Key": settings.get('api_key'),
                "Content-Type": "application/json"
            },
            timeout=30
        )

        if sessions_response.status_code == 200:
            sessions_data = sessions_response.json()
            if sessions_data.get('success'):
                # Buscar la sesión por sessionId
                for session in sessions_data.get('data', {}).get('sessions', []):
                    if session.get('sessionId') == session_id:
                        # Obtener datos de la sesión
                        session_status = session.get('status', 'disconnected')
                        is_connected = 1 if session_status == 'connected' else 0
                        phone_number = session.get('phoneNumber', '')
                        last_activity = session.get('lastActivity', '')

                        # Actualizar estado en Frappe
                        try:
                            session_doc = frappe.get_doc("WhatsApp Session", {"session_id": session_id})
                            if session_doc:
                                # Mapear estado del servidor a estado de Frappe
                                frappe_status = "Disconnected"
                                if session_status == 'connected':
                                    frappe_status = "Connected"
                                elif session_status == 'connecting':
                                    frappe_status = "Connecting"
                                elif session_status == 'qr_code_required':
                                    frappe_status = "QR Code Required"
                                elif session_status == 'error':
                                    frappe_status = "Error"

                                # Actualizar campos
                                session_doc.status = frappe_status
                                session_doc.is_connected = is_connected
                                if phone_number:
                                    session_doc.phone_number = phone_number

                                # Convertir last_activity a formato MySQL si existe
                                if last_activity:
                                    try:
                                        from datetime import datetime
                                        # Convertir ISO string a datetime de Python
                                        dt = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
                                        # Formatear para MySQL (YYYY-MM-DD HH:MM:SS)
                                        session_doc.last_seen = dt.strftime('%Y-%m-%d %H:%M:%S')
                                    except:
                                        # Si no se puede convertir, usar solo la fecha
                                        session_doc.last_seen = last_activity.split('T')[0] if 'T' in last_activity else last_activity

                                session_doc.save(ignore_permissions=True)
                                frappe.db.commit()
                        except Exception as e:
                            print(f"Error actualizando sesión en Frappe: {str(e)[:100]}")

                        return {
                            "success": True,
                            "data": {
                                "id": session.get('id'),
                                "sessionId": session.get('sessionId'),
                                "status": session_status,
                                "is_connected": is_connected,
                                "phone_number": phone_number,
                                "last_activity": last_activity
                            }
                        }

                return {
                    "success": False,
                    "error": "Sesión no encontrada"
                }
            else:
                return {
                    "success": False,
                    "error": f"Error obteniendo sesiones: {sessions_data.get('message', 'Error desconocido')}"
                }
        else:
            return {
                "success": False,
                "error": f"Error del servidor: {sessions_response.status_code}"
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
