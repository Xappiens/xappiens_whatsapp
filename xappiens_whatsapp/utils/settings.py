"""
Utilidades para manejar configuraciones de WhatsApp
"""

import frappe
from frappe import _


def get_whatsapp_settings():
    """
    Obtiene la configuración de WhatsApp Settings
    """
    try:
        settings = frappe.get_single("WhatsApp Settings")
        return settings
    except Exception as e:
        frappe.log_error(f"Error obteniendo configuración de WhatsApp: {str(e)}")
        return None


def get_api_credentials():
    """
    Obtiene las credenciales de API para autenticación
    """
    settings = get_whatsapp_settings()
    if not settings:
        return None

    return {
        "email": settings.api_email,
        "password": settings.api_password,
        "user_id": settings.api_user_id,
        "organization_id": settings.organization_id,
        "api_key": settings.api_key,
        "base_url": settings.api_base_url,
        "session_id": settings.session_id
    }


def get_session_config():
    """
    Obtiene la configuración de la sesión de WhatsApp
    """
    settings = get_whatsapp_settings()
    if not settings:
        return None

    return {
        "session_id": settings.session_id,
        "session_db_id": settings.session_db_id,
        "phone_number": settings.phone_number,
        "status": settings.session_status
    }


def get_webhook_config():
    """
    Obtiene la configuración de webhooks
    """
    settings = get_whatsapp_settings()
    if not settings:
        return None

    return {
        "enabled": settings.webhook_enabled,
        "secret": settings.webhook_secret,
        "events": settings.webhook_events.split(",") if settings.webhook_events else [],
        "timeout": settings.webhook_timeout,
        "retry_attempts": settings.webhook_retry_attempts
    }


def is_whatsapp_enabled():
    """
    Verifica si el módulo de WhatsApp está habilitado
    """
    settings = get_whatsapp_settings()
    return settings and settings.enabled


def validate_settings():
    """
    Valida que todas las configuraciones necesarias estén presentes
    """
    settings = get_whatsapp_settings()
    if not settings:
        return False, "No se encontró configuración de WhatsApp"

    required_fields = [
        "api_email", "api_password", "api_key", "api_base_url",
        "session_id", "session_db_id"
    ]

    missing_fields = []
    for field in required_fields:
        if not getattr(settings, field, None):
            missing_fields.append(field)

    if missing_fields:
        return False, f"Faltan campos requeridos: {', '.join(missing_fields)}"

    return True, "Configuración válida"


def update_session_status(status):
    """
    Actualiza el estado de la sesión de WhatsApp
    """
    try:
        settings = frappe.get_single("WhatsApp Settings")
        settings.session_status = status
        settings.save()
        frappe.db.commit()
        return True
    except Exception as e:
        frappe.log_error(f"Error actualizando estado de sesión: {str(e)}")
        return False


def get_api_base_url():
    """
    Obtiene la URL base de la API
    """
    settings = get_whatsapp_settings()
    if not settings:
        return None

    return settings.api_base_url


def get_rate_limits():
    """
    Obtiene los límites de rate limiting configurados
    """
    settings = get_whatsapp_settings()
    if not settings:
        return None

    return {
        "enabled": settings.rate_limit_enabled,
        "per_minute": settings.rate_limit_messages_per_minute,
        "per_hour": settings.rate_limit_messages_per_hour,
        "per_day": settings.rate_limit_messages_per_day
    }
