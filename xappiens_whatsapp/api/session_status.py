#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Endpoints ligeros para exponer el estado de las sesiones de WhatsApp al portal.
No dependen del módulo legacy `session.py` para evitar problemas de caché en producción.
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List

import frappe

from .base import WhatsAppAPIClient


def _resolve_session(session_name: Optional[str] = None, session_id: Optional[str] = None):
    """Intenta localizar el DocType de sesión a partir del nombre o del session_id de Baileys."""
    doc = None

    if session_name and frappe.db.exists("WhatsApp Session", session_name):
        doc = frappe.get_doc("WhatsApp Session", session_name)

    if not doc and session_id:
        name = frappe.db.get_value("WhatsApp Session", {"session_id": session_id}, "name")
        if name:
            doc = frappe.get_doc("WhatsApp Session", name)

    if not doc:
        default_session = frappe.db.get_single_value("WhatsApp Settings", "default_session")
        if default_session and frappe.db.exists("WhatsApp Session", default_session):
            doc = frappe.get_doc("WhatsApp Session", default_session)

    if not doc:
        any_session = frappe.db.get_value("WhatsApp Session", {"is_active": 1}, "name")
        if any_session:
            doc = frappe.get_doc("WhatsApp Session", any_session)

    return doc


def _extract_sessions(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Normaliza la respuesta del backend Baileys para devolver la lista de sesiones."""
    if not payload:
        return []

    data = payload.get("data")
    if isinstance(data, dict):
        items = data.get("items") or data.get("sessions") or data.get("data")
        if isinstance(items, list):
            return items
    elif isinstance(data, list):
        return data

    sessions = payload.get("sessions")
    if isinstance(sessions, list):
        return sessions

    return []


def _map_status(remote_status: str) -> str:
    """Mapea el estado remoto al estado utilizado en el DocType."""
    status = (remote_status or "").lower()

    if status == "connected":
        return "Connected"
    if status == "connecting":
        return "Connecting"
    if status in ("qr_code_required", "qr_code"):
        return "QR Code Required"
    if status == "error":
        return "Error"
    return "Disconnected"


@frappe.whitelist()
def get_session_status(session_name: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Devuelve el estado de la sesión (o de la sesión por defecto) y sincroniza el DocType local.

    Args:
        session_name: Nombre del documento `WhatsApp Session`
        session_id: Identificador Baileys de la sesión
    """
    try:
        session_doc = _resolve_session(session_name=session_name, session_id=session_id)
        if not session_doc:
            return {
                "success": False,
                "error": "No se encontró ninguna sesión de WhatsApp configurada"
            }

        client = WhatsAppAPIClient()
        response = client.get_sessions(limit=200)

        if not response.get("success"):
            return {
                "success": False,
                "error": response.get("message") or "Error obteniendo sesiones remotas"
            }

        remote_sessions = _extract_sessions(response)

        remote_session = None
        for candidate in remote_sessions:
            if candidate.get("sessionId") == session_doc.session_id:
                remote_session = candidate
                break
            if session_doc.session_db_id and str(candidate.get("id")) == str(session_doc.session_db_id):
                remote_session = candidate
                break

        # Si no aparece en remoto, marcar como desconectada
        if not remote_session:
            session_doc.is_connected = 0
            session_doc.status = "Disconnected"
            session_doc.save(ignore_permissions=True)
            frappe.db.commit()

            return {
                "success": True,
                "data": {
                    "id": session_doc.session_db_id,
                    "sessionId": session_doc.session_id,
                    "doc_name": session_doc.name,
                    "status": "disconnected",
                    "is_connected": 0,
                    "phone_number": session_doc.phone_number,
                    "last_activity": session_doc.last_seen
                }
            }

        remote_status = remote_session.get("status") or "disconnected"
        mapped_status = _map_status(remote_status)
        is_connected = 1 if mapped_status == "Connected" else 0
        phone_number = (
            remote_session.get("phoneNumber")
            or remote_session.get("msisdn")
            or session_doc.phone_number
        )
        last_activity = remote_session.get("lastActivity") or remote_session.get("lastSeen")

        session_doc.status = mapped_status
        session_doc.is_connected = is_connected
        if phone_number:
            session_doc.phone_number = phone_number

        if remote_session.get("id"):
            session_doc.session_db_id = remote_session.get("id")

        if last_activity:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(str(last_activity).replace("Z", "+00:00"))
                session_doc.last_seen = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                session_doc.last_seen = last_activity

        session_doc.save(ignore_permissions=True)
        frappe.db.commit()

        return {
            "success": True,
            "data": {
                "id": remote_session.get("id"),
                "sessionId": remote_session.get("sessionId"),
                "doc_name": session_doc.name,
                "status": remote_status,
                "is_connected": is_connected,
                "phone_number": phone_number,
                "last_activity": last_activity
            }
        }

    except Exception as exc:
        frappe.log_error(f"Error obteniendo estado de sesión (portal): {str(exc)}")
        return {
            "success": False,
            "error": str(exc)
        }
