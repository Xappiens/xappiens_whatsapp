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
from datetime import datetime
from xappiens_whatsapp.utils.settings import get_api_credentials, get_api_base_url
from .base import WhatsAppAPIClient


def map_baileys_status_to_frappe(baileys_status):
    """
    Mapea los estados del servidor Baileys a los estados válidos de Frappe

    Estados válidos en Frappe: "Disconnected", "Connecting", "Connected", "QR Code Required", "Error"
    """
    status_mapping = {
        'disconnected': 'Disconnected',
        'connecting': 'Connecting',
        'connected': 'Connected',
        'qr_code': 'QR Code Required',  # Mapeo principal del problema
        'qr': 'QR Code Required',
        'pending': 'QR Code Required',
        'error': 'Error',
        'rate_limited': 'Error',
        'timeout': 'Error'
    }

    # Normalizar el estado de entrada
    normalized_status = str(baileys_status).lower().strip()

    # Buscar mapeo exacto
    if normalized_status in status_mapping:
        return status_mapping[normalized_status]

    # Buscar mapeo parcial para casos como "qr_code_required"
    for baileys_key, frappe_value in status_mapping.items():
        if baileys_key in normalized_status:
            return frappe_value

    # Por defecto, si no encuentra mapeo, usar Disconnected
    frappe.log_error(f"Estado desconocido de Baileys: {baileys_status}", "WhatsApp Status Mapping")
    return 'Disconnected'



@frappe.whitelist()
def test_connection():
    """
    Probar la conexión con el servidor de WhatsApp
    """
    try:
        settings = get_api_credentials()
        api_base_url = get_api_base_url()

        if not settings or not api_base_url:
            error_msg = "Configuración de WhatsApp no encontrada"
            return {
                "success": False,
                "error": error_msg,
                "debug": {
                    "settings_present": bool(settings),
                    "api_base_url": api_base_url
                }
            }

        # Probar conexión con API Key (sin JWT)
        url = f"{api_base_url}/api/sessions"
        headers = {
            "X-API-Key": settings.get('api_key'),
            "Content-Type": "application/json"
        }

        test_response = requests.get(url, headers=headers, timeout=30)

        if test_response.status_code in [200, 401]:  # 401 es OK, significa que la API responde
            success_msg = "Conexión exitosa con el servidor de WhatsApp (solo API Key)"
            return {
                "success": True,
                "message": success_msg,
                "data": {
                    "token": "API_KEY_ONLY",
                    "user": "API Key Authentication"
                },
                "debug": {
                    "url": url,
                    "status_code": test_response.status_code,
                    "response_preview": test_response.text[:200],
                    "api_key_present": bool(settings.get('api_key')),
                    "api_key_preview": settings.get('api_key', '')[:20] + "..." if settings.get('api_key') else None
                }
            }
        else:
            error_msg = f"Error de conexión: No se pudo conectar al servidor (Status: {test_response.status_code})"
            return {
                "success": False,
                "error": error_msg,
                "debug": {
                    "url": url,
                    "status_code": test_response.status_code,
                    "response_preview": test_response.text[:200],
                    "api_key_present": bool(settings.get('api_key')),
                    "api_key_preview": settings.get('api_key', '')[:20] + "..." if settings.get('api_key') else None,
                    "headers_sent": dict(headers)
                }
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
    Actualizado según nueva documentación - usa endpoint específico de estado
    """
    try:
        session_doc = _resolve_session_doc(session_id)

        if not session_doc:
            return {
                "success": False,
                "error": "No hay sesión de WhatsApp configurada"
            }

        # Usar el endpoint unificado de estado (acepta tanto ID numérico como sessionId string)
        settings = get_api_credentials()
        api_base_url = get_api_base_url()

        # El endpoint unificado acepta ambos formatos automáticamente
        # Priorizar session_db_id (ID numérico), pero también funciona con session_id (string)
        status_url = None
        if session_doc.session_db_id:
            status_url = f"{api_base_url}/api/sessions/{session_doc.session_db_id}/status"
        elif session_doc.session_id:
            # El endpoint unificado también acepta sessionId string
            status_url = f"{api_base_url}/api/sessions/{session_doc.session_id}/status"
        else:
            return {
                "success": False,
                "error": "No se encontró ID de sesión válido"
            }

        response = requests.get(
            status_url,
            headers={
                "X-API-Key": settings.get('api_key'),
                "Content-Type": "application/json"
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()

            if result.get('success'):
                data = result.get('data', {})

                # IMPORTANTE: El estado ahora viene de memoria (fuente de verdad), no de BD
                # Priorizar isConnected sobre status para determinar el estado real
                server_status = data.get('status', 'disconnected').lower()
                is_connected_real = bool(data.get('isConnected'))  # Fuente de verdad

                # Si isConnected es False, la sesión NO está conectada realmente
                # independientemente del valor de status
                if not is_connected_real and server_status == 'connected':
                    # Desincronización: status dice connected pero isConnected es False
                    # Esto puede pasar si el servidor se reinició y la sesión no está en memoria
                    server_status = 'disconnected'
                    frappe.log_error(
                        f"Desincronización detectada en sesión {session_doc.session_id}: "
                        f"status='connected' pero isConnected=False. Estado real: disconnected",
                        "WhatsApp Session Status Desync"
                    )

                frappe_status = map_baileys_status_to_frappe(server_status)

                # Actualizar session_db_id si viene del servidor y no está guardado
                server_session_id = data.get('id')
                if server_session_id and not session_doc.session_db_id:
                    session_doc.session_db_id = server_session_id

                session_doc.status = frappe_status
                session_doc.is_connected = 1 if is_connected_real else 0
                session_doc.phone_number = data.get('phoneNumber')

                # Convertir lastActivity de ISO 8601 a formato MySQL/Frappe
                last_activity = data.get('lastActivity')
                if last_activity:
                    try:
                        # Parsear fecha ISO 8601
                        if isinstance(last_activity, str):
                            # Reemplazar Z por +00:00 para compatibilidad con fromisoformat
                            if last_activity.endswith('Z'):
                                last_activity = last_activity.replace('Z', '+00:00')
                            parsed_datetime = datetime.fromisoformat(last_activity)
                        else:
                            parsed_datetime = last_activity

                        # Convertir a naive datetime (sin timezone) para MySQL
                        # Si tiene timezone, convertir a UTC y luego quitar timezone info
                        if parsed_datetime.tzinfo is not None:
                            # Convertir a UTC y hacer naive
                            parsed_datetime = parsed_datetime.astimezone(datetime.timezone.utc).replace(tzinfo=None)

                        # Usar get_datetime de Frappe para asegurar formato correcto
                        session_doc.last_seen = frappe.utils.get_datetime(parsed_datetime)
                    except (ValueError, AttributeError, TypeError) as e:
                        frappe.log_error(
                            f"Error parseando lastActivity '{last_activity}': {str(e)}",
                            "WhatsApp Session Date Parse Error"
                        )
                        # Si falla el parsing, no actualizar last_seen

                session_doc.save(ignore_permissions=True)
                frappe.db.commit()

                # Normalizar el estado para el frontend
                normalized_status = server_status.lower()

                return {
                    "success": True,
                    "data": {
                        "id": session_doc.session_db_id or server_session_id,
                        "sessionId": data.get('sessionId') or session_doc.session_id,
                        "status": normalized_status,  # Estado REAL desde memoria
                        "status_frappe": frappe_status,  # Estado mapeado a Frappe
                        "phoneNumber": data.get('phoneNumber'),
                        "lastActivity": data.get('lastActivity'),
                        "isConnected": is_connected_real,  # Fuente de verdad - estado REAL
                        "is_connected": is_connected_real,  # También en formato snake_case
                        "hasQR": data.get('hasQR', False)
                    }
                }
            else:
                return {
                    "success": False,
                    "error": result.get('message', 'Error obteniendo estado de sesión')
                }
        elif response.status_code == 404:
            # Sesión no encontrada en el servidor - puede ser que aún no esté lista
            # Intentar obtener estado desde la lista de sesiones como fallback
            try:
                list_response = requests.get(
                    f"{api_base_url}/api/sessions",
                    headers={
                        "X-API-Key": settings.get('api_key'),
                        "Content-Type": "application/json"
                    },
                    timeout=10
                )

                if list_response.status_code == 200:
                    list_data = list_response.json()
                    sessions = list_data.get('data', {}).get('sessions', []) or list_data.get('sessions', [])

                    # Buscar nuestra sesión en la lista
                    for s in sessions:
                        if (str(s.get('id')) == str(session_doc.session_db_id) or
                            s.get('sessionId') == session_doc.session_id):
                            # Encontrada - usar datos del servidor
                            server_status = (s.get('status') or 'disconnected').lower()
                            frappe_status = map_baileys_status_to_frappe(server_status)
                            is_connected = 1 if server_status == 'connected' else 0

                            session_doc.status = frappe_status
                            session_doc.is_connected = is_connected
                            session_doc.phone_number = s.get('phoneNumber') or session_doc.phone_number
                            session_doc.save(ignore_permissions=True)
                            frappe.db.commit()

                            return {
                                "success": True,
                                "data": {
                                    "id": session_doc.session_db_id,
                                    "sessionId": s.get('sessionId'),
                                    "status": server_status,
                                    "status_frappe": frappe_status,
                                    "phoneNumber": s.get('phoneNumber'),
                                    "isConnected": is_connected,
                                    "is_connected": is_connected,
                                    "hasQR": False
                                }
                            }
            except Exception as e:
                frappe.log_error(f"Error obteniendo lista de sesiones como fallback: {str(e)}", "WhatsApp Session Status Fallback")

            # Si no se encontró en la lista, devolver estado desconectado
            return {
                "success": True,
                "data": {
                    "id": session_doc.session_db_id,
                    "sessionId": session_doc.session_id,
                    "status": "disconnected",
                    "status_frappe": "Disconnected",
                    "isConnected": False,
                    "is_connected": False,
                    "phoneNumber": session_doc.phone_number,
                    "lastActivity": session_doc.last_seen,
                    "hasQR": False
                }
            }
        else:
            # Otro error HTTP
            frappe.log_error(f"Error obteniendo estado de sesión: HTTP {response.status_code}", "WhatsApp Session Status Error")
            return {
                "success": False,
                "error": f"Error del servidor: {response.status_code}"
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"Error interno: {str(e)}"
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

        # Ya no se necesita autenticación JWT según nueva documentación
        # Solo usamos API Key directamente

        # Preparar datos para el servidor
        session_data = {
            "session_id": session_id,
            "session_name": session_name,
            "description": description,
            "user_id": settings.get('api_user_id'),
            "organization_id": settings.get('organization_id')
        }

        # Crear nueva sesión en el servidor según nueva documentación
        create_data = {
            "sessionId": session_id,
            "sessionName": session_name,
            "fromFrappe": True  # Identificar que viene de Frappe
        }

        # Solo agregar phoneNumber si está definido y no está vacío
        phone_number = settings.get('phone_number')
        if phone_number and phone_number.strip():
            create_data["phoneNumber"] = phone_number.strip()

        # Agregar webhook si está configurado
        webhook_url = settings.get('webhook_url')
        if webhook_url and webhook_url.strip():
            create_data["webhookUrl"] = webhook_url.strip()

        webhook_secret = settings.get('webhook_secret')
        if webhook_secret and webhook_secret.strip():
            create_data["webhookSecret"] = webhook_secret.strip()

        create_response = requests.post(
            f"{api_base_url}/api/sessions",
            json=create_data,
            headers={
                "X-API-Key": settings.get('api_key'),
                "Content-Type": "application/json",
                "X-Frappe-Origin": "true"  # Header para identificar origen Frappe
            },
            timeout=30
        )

        if create_response.status_code in [200, 201]:
            create_result = create_response.json()

            if create_result.get('success'):
                # Según respuesta real del servidor, el ID está en data.session.id
                session_data = create_result.get('data', {}).get('session', {})
                session_id_created = session_data.get('id')
                session_id_returned = session_data.get('sessionId')
                session_status = session_data.get('status', 'pending')

                if not session_id_created:
                    return {
                        "success": False,
                        "error": "No se pudo obtener el ID de la sesión creada"
                    }

                # Iniciar conexión de la sesión
                connect_response = None
                connect_exception = None
                try:
                    connect_response = requests.post(
                        f"{api_base_url}/api/sessions/{session_id_created}/connect",
                        headers={
                            "X-API-Key": settings.get('api_key'),
                            "Content-Type": "application/json"
                        },
                        json={},  # Body vacío explícito
                        timeout=10
                    )

                except Exception as e:
                    # Capturar excepción y guardar info para debug
                    connect_exception = str(e)

                # Obtener estado actualizado de la sesión
                status_response = requests.get(
                    f"{api_base_url}/api/sessions/{session_id_created}/status",
                    headers={
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
                        # Usar el mapeo para convertir estados de Baileys a Frappe
                        final_status = map_baileys_status_to_frappe(session_status)
                        is_connected = 1 if session_status.lower() == 'connected' else 0

                # Obtener QR code según nueva documentación (con retry mejorado y manejo de rate limiting)
                qr_code = ""
                qr_expires_at = None
                qr_error = None

                # Intentar obtener QR directamente - el servidor ahora funciona correctamente
                import time
                for attempt in range(3):  # Reducido a 3 intentos para evitar rate limiting
                    try:
                        # Intentar obtener QR directamente (el servidor ya está arreglado)
                        qr_response = requests.get(
                            f"{api_base_url}/api/sessions/{session_id_created}/qr",
                            headers={
                                "X-API-Key": settings.get('api_key'),
                                "Content-Type": "application/json"
                            },
                            timeout=15
                        )

                        if qr_response.status_code == 200:
                            qr_data = qr_response.json()
                            if qr_data.get('success') and qr_data.get('data', {}).get('qrCode'):
                                qr_code_raw = qr_data['data']['qrCode']
                                qr_expires_at = qr_data['data'].get('expiresAt')

                                # Según la nueva documentación, viene como "data:image/png;base64,..."
                                if qr_code_raw.startswith('data:image'):
                                    # Extraer solo el base64 después de la coma
                                    qr_code = qr_code_raw.split(',')[1] if ',' in qr_code_raw else qr_code_raw
                                else:
                                    # Si no viene como data URL, usar tal como está
                                    qr_code = qr_code_raw

                                # QR obtenido exitosamente
                                break
                        elif qr_response.status_code == 429:
                            # Rate limiting - esperar más tiempo y no continuar
                            qr_error = "Demasiadas solicitudes. El QR se obtendrá automáticamente cuando esté disponible."
                            frappe.log_error(
                                f"Rate limiting (429) obteniendo QR para sesión {session_id_created}",
                                "WhatsApp QR Rate Limit"
                            )
                            break  # No continuar intentando si hay rate limiting
                        elif qr_response.status_code == 404:
                            # Sesión no encontrada o QR no disponible aún
                            qr_error = "QR no disponible aún. El sistema seguirá intentando automáticamente."
                            if attempt < 2:
                                time.sleep(5)  # Esperar más tiempo entre intentos
                            continue
                        elif qr_response.status_code == 500:
                            # Error del servidor de Baileys - registrar pero continuar
                            error_data = qr_response.json() if qr_response.text else {}
                            qr_error = error_data.get('error', 'QR_GENERATION_ERROR')
                            frappe.log_error(
                                f"Error 500 obteniendo QR para sesión {session_id_created}: {qr_error}",
                                "WhatsApp QR Generation Error"
                            )
                            # Esperar más tiempo antes del siguiente intento
                            if attempt < 2:
                                time.sleep(5)
                            continue
                        else:
                            # Otro error HTTP
                            qr_error = f"HTTP {qr_response.status_code}: {qr_response.text[:200]}"
                            if attempt < 2:
                                time.sleep(5)
                            continue

                    except requests.exceptions.Timeout:
                        qr_error = "Timeout esperando respuesta del servidor"
                        if attempt < 2:
                            time.sleep(5)
                        continue
                    except Exception as e:
                        qr_error = f"Error inesperado: {str(e)}"
                        frappe.log_error(f"Error obteniendo QR (intento {attempt + 1}): {str(e)}", "WhatsApp QR Error")
                        if attempt < 2:
                            time.sleep(3)
                        continue

                    # Esperar antes del siguiente intento si no se obtuvo el QR
                    if attempt < 2 and not qr_code:
                        time.sleep(5)  # Esperar más tiempo entre intentos

                # Crear o actualizar registro en Frappe
                try:
                    # Intentar obtener sesión existente
                    existing_session = frappe.db.get_value("WhatsApp Session", {"session_id": session_id}, "name")

                    if existing_session:
                        # Actualizar sesión existente con session_db_id si no lo tiene
                        session_doc = frappe.get_doc("WhatsApp Session", existing_session)
                        if not session_doc.session_db_id:
                            session_doc.session_db_id = session_id_created
                        session_doc.status = final_status
                        session_doc.is_connected = is_connected
                        session_doc.is_active = 1
                        session_doc.save(ignore_permissions=True)
                    else:
                        # Crear nueva sesión
                        session_doc = frappe.get_doc({
                            "doctype": "WhatsApp Session",
                            "session_id": session_id,
                            "session_name": session_name,
                            "description": description,
                            "status": final_status,
                            "is_connected": is_connected,
                            "is_active": 1,
                            "session_db_id": session_id_created  # CRÍTICO: Guardar el ID numérico del servidor
                        })
                        session_doc.insert(ignore_permissions=True)
                except Exception as e:
                    frappe.log_error(f"Error creando/actualizando sesión en Frappe: {str(e)}", "WhatsApp Session Create")
                    # Continuar aunque falle la creación en Frappe

                # Preparar mensaje según si se obtuvo el QR o no
                if qr_code:
                    message = f"Sesión '{session_id}' creada exitosamente. QR disponible."
                elif qr_error and 'QR_GENERATION_ERROR' in str(qr_error):
                    message = f"Sesión '{session_id}' creada exitosamente, pero el servidor de Baileys no pudo generar el QR. El QR se generará automáticamente cuando esté disponible."
                elif qr_error:
                    message = f"Sesión '{session_id}' creada exitosamente. Error obteniendo QR: {qr_error}. El QR se generará automáticamente cuando esté disponible."
                else:
                    message = f"Sesión '{session_id}' creada exitosamente. El QR se generará automáticamente cuando esté disponible."

                return {
                    "success": True,
                    "message": message,
                    "qr_code": qr_code,
                    "session_id": session_id,
                    "status": final_status,
                    "qr_available": bool(qr_code),
                    "qr_error": qr_error if not qr_code else None,
                    "session_db_id": session_id_created,  # Incluir para referencia
                    "debug": {
                        "api_base_url": api_base_url,
                        "session_id_created": session_id_created,
                        "create_response_status": create_response.status_code,
                        "connect_response_status": connect_response.status_code if connect_response else None,
                        "connect_response_text": connect_response.text if connect_response and connect_response.status_code != 200 else None,
                        "connect_endpoint": f"{api_base_url}/api/sessions/{session_id_created}/connect",
                        "connect_exception": connect_exception,
                        "status_response_status": status_response.status_code if 'status_response' in locals() else None,
                        "status_response_text": status_response.text[:300] if 'status_response' in locals() and status_response.status_code != 200 else None,
                        "qr_error": qr_error,
                        "qr_attempts": 5,
                        "api_key_present": bool(settings.get('api_key')),
                        "api_key_preview": settings.get('api_key', '')[:20] + "..." if settings.get('api_key') else None
                    }
                }
            else:
                return {
                    "success": False,
                    "error": f"Error creando sesión: {create_data.get('message', 'Error desconocido')}",
                    "debug": {
                        "api_base_url": api_base_url,
                        "create_response_status": create_response.status_code,
                        "create_response_text": create_response.text[:300],
                        "api_key_present": bool(settings.get('api_key')),
                        "api_key_preview": settings.get('api_key', '')[:20] + "..." if settings.get('api_key') else None,
                        "create_data": create_data
                    }
                }
        else:
            error_data = create_response.json() if create_response.text else {}
            return {
                "success": False,
                "error": f"Error del servidor: {create_response.status_code} - {error_data.get('error', create_response.text[:200])}",
                "debug": {
                    "api_base_url": api_base_url,
                    "create_response_status": create_response.status_code,
                    "create_response_text": create_response.text[:300],
                    "api_key_present": bool(settings.get('api_key')),
                    "api_key_preview": settings.get('api_key', '')[:20] + "..." if settings.get('api_key') else None,
                    "error_data": error_data
                }
            }

    except Exception as e:
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

        # CRÍTICO: Resolver session_db_id desde session_id
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

        # Llamar al servidor de WhatsApp usando session_db_id
        response = requests.delete(
            f"{api_base_url}/api/sessions/{session_identifier}",
            headers={
                "X-API-Key": settings.get('api_key'),
                "Content-Type": "application/json"
            },
            timeout=30
        )

        if response.status_code == 200:
            # Actualizar estado en Frappe
            session_doc.status = "Disconnected"
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
        return {
            "success": False,
            "error": f"Error interno: {str(e)}"
        }


@frappe.whitelist()
def update_session_webhook(session_id, webhook_url=None, webhook_secret=None):
	"""
	Actualizar la configuración del webhook de una sesión existente en Baileys/Inbox Hub.

	Args:
		session_id: ID de la sesión (session_id string, no session_db_id)
		webhook_url: URL del webhook (opcional, usa el de settings si no se proporciona)
		webhook_secret: Secret del webhook (opcional, usa el de settings si no se proporciona)

	Returns:
		Dict con resultado de la actualización
	"""
	try:
		settings = get_api_credentials()
		api_base_url = get_api_base_url()

		if not settings or not api_base_url:
			return {
				"success": False,
				"error": "Configuración de WhatsApp no encontrada"
			}

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

		# Obtener webhook URL y secret de settings si no se proporcionan
		if not webhook_url:
			webhook_url = settings.get('webhook_url')
		if not webhook_secret:
			webhook_secret = settings.get('webhook_secret')

		# Preparar datos para actualizar
		update_data = {}
		if webhook_url and webhook_url.strip():
			update_data["webhookUrl"] = webhook_url.strip()
		if webhook_secret and webhook_secret.strip():
			update_data["webhookSecret"] = webhook_secret.strip()

		if not update_data:
			return {
				"success": False,
				"error": "No se proporcionaron datos para actualizar el webhook"
			}

		# Actualizar webhook en el servidor
		response = requests.put(
			f"{api_base_url}/api/sessions/{session_identifier}/webhook",
			json=update_data,
			headers={
				"X-API-Key": settings.get('api_key'),
				"Content-Type": "application/json"
			},
			timeout=30
		)

		if response.status_code in [200, 204]:
			return {
				"success": True,
				"message": "Webhook actualizado exitosamente",
				"webhook_url": webhook_url
			}
		else:
			error_text = response.text
			try:
				error_json = response.json()
				error_text = error_json.get('error') or error_json.get('message') or error_text
			except:
				pass

			return {
				"success": False,
				"error": f"Error del servidor ({response.status_code}): {error_text}"
			}

	except Exception as e:
		frappe.log_error(f"Error actualizando webhook de sesión: {str(e)}", "WhatsApp Session Webhook Update")
		return {
			"success": False,
			"error": f"Error interno: {str(e)}"
		}


@frappe.whitelist()
def delete_session_from_api(session_id):
	"""
	Eliminar una sesión del servidor de WhatsApp API
	"""
	try:
		settings = get_api_credentials()
		api_base_url = get_api_base_url()

		# Resolver session_db_id desde session_id
		session_doc = _resolve_session_doc(session_id)

		if not session_doc:
			# Si no existe en Frappe, intentar eliminar directamente con session_id
			session_identifier = session_id
		else:
			# Usar session_db_id si está disponible, sino intentar con session_id
			session_identifier = session_doc.session_db_id if session_doc.session_db_id else session_doc.session_id

		if not session_identifier:
			return {
				"success": False,
				"error": "No se encontró identificador válido para la sesión"
			}

		# Llamar al servidor de WhatsApp para eliminar la sesión
		response = requests.delete(
			f"{api_base_url}/api/sessions/{session_identifier}",
			headers={
				"X-API-Key": settings.get('api_key'),
				"Content-Type": "application/json"
			},
			timeout=30
		)

		if response.status_code in [200, 204]:
			return {
				"success": True,
				"message": "Sesión eliminada del servidor exitosamente"
			}
		else:
			return {
				"success": False,
				"error": f"Error del servidor: {response.status_code}"
			}

	except Exception as e:
		return {
			"success": False,
			"error": f"Error interno: {str(e)}"
		}


@frappe.whitelist()
def get_qr_code(session_id):
    """
    Obtener el código QR actual de una sesión
    Actualizado según nueva documentación - solo requiere API Key
    """
    try:
        settings = get_api_credentials()
        api_base_url = get_api_base_url()

        # CRÍTICO: Resolver session_db_id desde session_id
        # El endpoint del servidor requiere el ID numérico (session_db_id), no el string (session_id)
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

        # Llamar al servidor de WhatsApp - SOLO API Key según nueva documentación
        # Usar session_db_id (numérico) que es lo que requiere el endpoint
        response = requests.get(
            f"{api_base_url}/api/sessions/{session_identifier}/qr",
            headers={
                "X-API-Key": settings.get('api_key'),
                "Content-Type": "application/json"
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()

            if result.get('success'):
                data = result.get('data', {})
                return {
                    "success": True,
                    "qr_code": data.get('qrCode'),  # Base64 del QR desde el servidor
                    "qr_code_data_url": data.get('qrCode'),  # Listo para <img src="">
                    "expires_at": data.get('expiresAt'),  # Cuándo expira
                    "status": data.get('status'),
                    "session_id": data.get('sessionId')
                }
            else:
                return {
                    "success": False,
                    "error": result.get('message', 'Error obteniendo QR code')
                }
        else:
            return {
                "success": False,
                "error": f"Error del servidor: {response.status_code} - {response.text}"
            }

    except Exception as e:
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
        return {
            "success": False,
            "error": f"Error interno: {str(e)}"
        }
