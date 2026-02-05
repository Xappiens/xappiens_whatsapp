#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Endpoint de test para verificar conectividad del webhook de WhatsApp.
"""

import frappe
import json
from typing import Dict, Any
from datetime import datetime


@frappe.whitelist(allow_guest=True)
def test_webhook_connectivity():
    """
    Endpoint de test para verificar que el webhook es accesible desde Inbox Hub.

    URL: https://crm.grupoatu.com/api/method/xappiens_whatsapp.api.webhook_test.test_webhook_connectivity
    """
    try:
        # Obtener información de la request
        method = frappe.request.method
        headers = dict(frappe.request.headers)
        user_agent = headers.get('User-Agent', 'Unknown')
        ip_address = frappe.local.request_ip or 'Unknown'

        # Obtener payload si existe
        payload = {}
        if method == 'POST':
            try:
                raw_payload = frappe.request.get_data(as_text=True) or ""
                if raw_payload:
                    payload = json.loads(raw_payload)
            except json.JSONDecodeError:
                payload = {"raw_data": raw_payload}

        # Log de la prueba
        test_log = {
            "timestamp": datetime.now().isoformat(),
            "method": method,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "headers": headers,
            "payload": payload,
            "status": "success"
        }

        frappe.log_error(
            f"Webhook Test Success: {json.dumps(test_log, indent=2)}",
            "WhatsApp Webhook Test"
        )

        return {
            "success": True,
            "message": "Webhook endpoint is accessible",
            "timestamp": datetime.now().isoformat(),
            "method": method,
            "ip_address": ip_address,
            "webhook_url": "https://crm.grupoatu.com/api/method/xappiens_whatsapp.api.webhook.handle_webhook",
            "test_successful": True
        }

    except Exception as e:
        frappe.log_error(f"Webhook Test Error: {str(e)}", "WhatsApp Webhook Test Error")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@frappe.whitelist(allow_guest=True)
def test_webhook_with_signature():
    """
    Endpoint de test que simula un webhook real con validación de firma.

    URL: https://crm.grupoatu.com/api/method/xappiens_whatsapp.api.webhook_test.test_webhook_with_signature
    """
    try:
        # Obtener datos de la request
        raw_payload = frappe.request.get_data(as_text=True) or ""
        signature = frappe.request.headers.get("X-Webhook-Signature")
        event = frappe.request.headers.get("X-Webhook-Event")
        session = frappe.request.headers.get("X-Webhook-Session")

        # Validar firma si se proporciona
        signature_valid = False
        if signature and raw_payload:
            from .webhook import _verify_webhook_signature
            signature_valid = _verify_webhook_signature(raw_payload, signature)

        # Parsear payload
        data = {}
        if raw_payload:
            try:
                data = json.loads(raw_payload)
            except json.JSONDecodeError:
                data = {"raw_data": raw_payload}

        # Log del test
        test_result = {
            "timestamp": datetime.now().isoformat(),
            "ip_address": frappe.local.request_ip,
            "headers": {
                "signature": signature,
                "event": event,
                "session": session
            },
            "signature_provided": bool(signature),
            "signature_valid": signature_valid,
            "payload_size": len(raw_payload),
            "data_keys": list(data.keys()) if isinstance(data, dict) else [],
            "status": "success"
        }

        frappe.log_error(
            f"Webhook Signature Test: {json.dumps(test_result, indent=2)}",
            "WhatsApp Webhook Signature Test"
        )

        return {
            "success": True,
            "message": "Webhook signature test completed",
            "signature_provided": bool(signature),
            "signature_valid": signature_valid,
            "event": event,
            "session": session,
            "payload_received": bool(raw_payload),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        frappe.log_error(f"Webhook Signature Test Error: {str(e)}", "WhatsApp Webhook Signature Test Error")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@frappe.whitelist()
def get_webhook_config():
    """
    Obtener la configuración actual del webhook para mostrar al administrador.
    """
    try:
        settings = frappe.get_single("WhatsApp Settings")

        config = {
            "webhook_url": getattr(settings, 'webhook_url', None) or "https://crm.grupoatu.com/api/method/xappiens_whatsapp.api.webhook.handle_webhook",
            "webhook_enabled": settings.webhook_enabled,
            "webhook_secret": "***configurado***" if settings.get_password("webhook_secret") else "No configurado",
            "webhook_events": settings.webhook_events,
            "webhook_timeout": settings.webhook_timeout,
            "webhook_retry_attempts": settings.webhook_retry_attempts,
            "api_base_url": settings.api_base_url,
            "session_status": settings.session_status,
            "test_endpoints": {
                "connectivity": "https://crm.grupoatu.com/api/method/xappiens_whatsapp.api.webhook_test.test_webhook_connectivity",
                "signature": "https://crm.grupoatu.com/api/method/xappiens_whatsapp.api.webhook_test.test_webhook_with_signature"
            }
        }

        return {
            "success": True,
            "config": config
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def get_recent_webhook_activity():
    """
    Obtener actividad reciente de webhooks para debugging.
    """
    try:
        # Obtener logs de error recientes relacionados con webhooks
        webhook_logs = frappe.db.sql("""
            SELECT name, error, creation
            FROM `tabError Log`
            WHERE creation >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
            AND (error LIKE '%WhatsApp%' OR error LIKE '%webhook%' OR error LIKE '%handle_webhook%')
            ORDER BY creation DESC
            LIMIT 20
        """, as_dict=True)

        # Obtener mensajes recientes
        recent_messages = frappe.db.sql("""
            SELECT name, session, direction, content, timestamp, message_id
            FROM `tabWhatsApp Message`
            WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
            ORDER BY timestamp DESC
            LIMIT 10
        """, as_dict=True)

        return {
            "success": True,
            "webhook_logs": webhook_logs,
            "recent_messages": recent_messages,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
