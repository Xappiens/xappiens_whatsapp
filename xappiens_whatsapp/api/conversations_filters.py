#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API complementaria para filtros avanzados de conversaciones de WhatsApp.
Extiende la funcionalidad existente sin modificar las APIs base.
"""

import frappe
from frappe import _
from frappe.utils import getdate, add_days, now_datetime, get_datetime
from typing import Dict, Any, List, Optional
from .conversations import get_conversations
from .base import WhatsAppAPIClient


@frappe.whitelist()
def get_filterable_fields() -> List[Dict[str, Any]]:
    """
    Obtiene los campos filtrables para WhatsApp Conversation.
    Compatible con el sistema de filtros del CRM.

    Returns:
        Lista de campos filtrables con sus metadatos
    """
    try:
        # Campos principales del DocType WhatsApp Conversation
        fields = [
            {
                "fieldname": "contact_name",
                "fieldtype": "Data",
                "label": _("Contact Name"),
                "options": None
            },
            {
                "fieldname": "phone_number",
                "fieldtype": "Data",
                "label": _("Phone Number"),
                "options": None
            },
            {
                "fieldname": "chat_id",
                "fieldtype": "Data",
                "label": _("Chat ID"),
                "options": None
            },
            {
                "fieldname": "status",
                "fieldtype": "Select",
                "label": _("Status"),
                "options": "Active\nArchived\nBlocked\nMuted"
            },
            {
                "fieldname": "is_group",
                "fieldtype": "Check",
                "label": _("Is Group"),
                "options": None
            },
            {
                "fieldname": "is_archived",
                "fieldtype": "Check",
                "label": _("Is Archived"),
                "options": None
            },
            {
                "fieldname": "is_pinned",
                "fieldtype": "Check",
                "label": _("Is Pinned"),
                "options": None
            },
            {
                "fieldname": "is_muted",
                "fieldtype": "Check",
                "label": _("Is Muted"),
                "options": None
            },
            {
                "fieldname": "unread_count",
                "fieldtype": "Int",
                "label": _("Unread Count"),
                "options": None
            },
            {
                "fieldname": "assigned_to",
                "fieldtype": "Link",
                "label": _("Assigned To"),
                "options": "User"
            },
            {
                "fieldname": "linked_lead",
                "fieldtype": "Link",
                "label": _("Linked Lead"),
                "options": "CRM Lead"
            },
            {
                "fieldname": "linked_customer",
                "fieldtype": "Link",
                "label": _("Linked Customer"),
                "options": "CRM Customer"
            },
            {
                "fieldname": "linked_deal",
                "fieldtype": "Link",
                "label": _("Linked Deal"),
                "options": "CRM Deal"
            },
            {
                "fieldname": "priority",
                "fieldtype": "Select",
                "label": _("Priority"),
                "options": "Low\nMedium\nHigh\nUrgent"
            },
            {
                "fieldname": "last_message_time",
                "fieldtype": "Datetime",
                "label": _("Last Message Time"),
                "options": None
            },
            {
                "fieldname": "first_message_time",
                "fieldtype": "Datetime",
                "label": _("First Message Time"),
                "options": None
            },
            {
                "fieldname": "creation",
                "fieldtype": "Datetime",
                "label": _("Created On"),
                "options": None
            },
            {
                "fieldname": "modified",
                "fieldtype": "Datetime",
                "label": _("Last Modified"),
                "options": None
            },
            {
                "fieldname": "owner",
                "fieldtype": "Link",
                "label": _("Created By"),
                "options": "User"
            }
        ]

        # Agregar campos estándar
        for field in fields:
            field["label"] = _(field.get("label"))
            field["name"] = field.get("fieldname")

        return fields

    except Exception as e:
        frappe.log_error(f"Error getting filterable fields: {str(e)}", "WhatsApp Filters Error")
        return []


@frappe.whitelist()
def get_quick_filters() -> List[Dict[str, Any]]:
    """
    Obtiene filtros rápidos para WhatsApp Conversation.
    Similar al sistema de quick filters del CRM.

    Returns:
        Lista de filtros rápidos
    """
    try:
        quick_filters = [
            {
                "label": _("Contact Name"),
                "name": "contact_name",
                "type": "Data"
            },
            {
                "label": _("Phone Number"),
                "name": "phone_number",
                "type": "Data"
            },
            {
                "label": _("Status"),
                "name": "status",
                "type": "Select",
                "options": [
                    {"label": "", "value": ""},
                    {"label": _("Active"), "value": "Active"},
                    {"label": _("Archived"), "value": "Archived"},
                    {"label": _("Blocked"), "value": "Blocked"},
                    {"label": _("Muted"), "value": "Muted"}
                ]
            },
            {
                "label": _("Is Group"),
                "name": "is_group",
                "type": "Check"
            },
            {
                "label": _("Assigned To"),
                "name": "assigned_to",
                "type": "Link",
                "options": "User"
            },
            {
                "label": _("Priority"),
                "name": "priority",
                "type": "Select",
                "options": [
                    {"label": "", "value": ""},
                    {"label": _("Low"), "value": "Low"},
                    {"label": _("Medium"), "value": "Medium"},
                    {"label": _("High"), "value": "High"},
                    {"label": _("Urgent"), "value": "Urgent"}
                ]
            }
        ]

        return quick_filters

    except Exception as e:
        frappe.log_error(f"Error getting quick filters: {str(e)}", "WhatsApp Filters Error")
        return []


@frappe.whitelist()
def get_filtered_conversations(
    session_id: str = None,
    filters: Dict[str, Any] = None,
    search: str = None,
    limit: int = 50,
    offset: int = 0,
    order_by: str = "last_message_time desc"
) -> Dict[str, Any]:
    """
    Obtiene conversaciones filtradas usando la API base como fundamento.
    Extiende get_conversations() sin modificar su funcionalidad.

    Args:
        session_id: ID de la sesión de WhatsApp
        filters: Diccionario de filtros a aplicar
        search: Término de búsqueda
        limit: Límite de resultados
        offset: Offset para paginación
        order_by: Campo de ordenamiento

    Returns:
        Dict con conversaciones filtradas y metadatos
    """
    try:
        # Usar la API base existente como fundamento
        base_result = get_conversations(session_id=session_id, limit=limit * 2, offset=0)

        if not base_result.get("success", True):
            return base_result

        conversations = base_result.get("conversations", [])

        # Aplicar filtros si se proporcionan
        if filters:
            conversations = apply_conversation_filters(conversations, filters)

        # Aplicar búsqueda si se proporciona
        if search:
            conversations = apply_search_filter(conversations, search)

        # Aplicar ordenamiento
        conversations = apply_sorting(conversations, order_by)

        # Aplicar paginación
        total_count = len(conversations)
        conversations = conversations[offset:offset + limit]

        # Enriquecer con estadísticas
        stats = calculate_conversation_stats(conversations)

        return {
            "success": True,
            "conversations": conversations,
            "total_count": total_count,
            "filtered_count": len(conversations),
            "stats": stats
        }

    except Exception as e:
        frappe.log_error(f"Error filtering conversations: {str(e)}", "WhatsApp Filters Error")
        return {
            "success": False,
            "message": str(e),
            "conversations": [],
            "total_count": 0
        }


def apply_conversation_filters(conversations: List[Dict], filters: Dict[str, Any]) -> List[Dict]:
    """
    Aplica filtros a la lista de conversaciones.

    Args:
        conversations: Lista de conversaciones
        filters: Diccionario de filtros

    Returns:
        Lista filtrada de conversaciones
    """
    if not filters:
        return conversations

    filtered = []

    for conv in conversations:
        include = True

        for field_name, filter_value in filters.items():
            if not include:
                break

            # Obtener valor del campo
            field_value = get_conversation_field_value(conv, field_name)

            # Aplicar filtro según el tipo
            if isinstance(filter_value, list) and len(filter_value) == 2:
                # Filtro con operador [operador, valor]
                operator, value = filter_value
                include = apply_filter_operator(field_value, operator, value)
            else:
                # Filtro de igualdad simple
                include = (field_value == filter_value)

        if include:
            filtered.append(conv)

    return filtered


def apply_search_filter(conversations: List[Dict], search: str) -> List[Dict]:
    """
    Aplica filtro de búsqueda de texto.

    Args:
        conversations: Lista de conversaciones
        search: Término de búsqueda

    Returns:
        Lista filtrada por búsqueda
    """
    if not search:
        return conversations

    search_lower = search.lower()
    filtered = []

    for conv in conversations:
        # Campos donde buscar
        searchable_fields = [
            conv.get("contact_name", ""),
            conv.get("phone_number", ""),
            conv.get("last_message", ""),
            conv.get("chat_id", "")
        ]

        # Buscar en cualquier campo
        found = any(
            search_lower in str(field_value).lower()
            for field_value in searchable_fields
            if field_value
        )

        if found:
            filtered.append(conv)

    return filtered


def apply_sorting(conversations: List[Dict], order_by: str) -> List[Dict]:
    """
    Aplica ordenamiento a las conversaciones.

    Args:
        conversations: Lista de conversaciones
        order_by: Campo y dirección de ordenamiento

    Returns:
        Lista ordenada
    """
    if not order_by:
        return conversations

    # Parsear order_by (ej: "last_message_time desc")
    parts = order_by.split()
    field_name = parts[0]
    direction = parts[1].lower() if len(parts) > 1 else "asc"
    reverse = (direction == "desc")

    try:
        return sorted(
            conversations,
            key=lambda x: get_conversation_field_value(x, field_name) or "",
            reverse=reverse
        )
    except Exception:
        # Si falla el ordenamiento, devolver sin ordenar
        return conversations


def get_conversation_field_value(conversation: Dict, field_name: str) -> Any:
    """
    Obtiene el valor de un campo de la conversación.
    Maneja tanto campos directos como metadata.

    Args:
        conversation: Diccionario de conversación
        field_name: Nombre del campo

    Returns:
        Valor del campo
    """
    # Mapeo de campos
    field_map = {
        "contact_name": conversation.get("contact_name"),
        "phone_number": conversation.get("phone_number"),
        "chat_id": conversation.get("name") or conversation.get("chat_id"),
        "last_message": conversation.get("last_message"),
        "last_message_time": conversation.get("last_message_time"),
        "unread_count": conversation.get("unread_count", 0),
        "is_group": conversation.get("is_group", False),
        "assigned_to": (
            conversation.get("assigned_to") or
            conversation.get("metadata", {}).get("assigned_to")
        ),
        "linked_lead": (
            conversation.get("crm_lead") or
            conversation.get("metadata", {}).get("linked_lead")
        ),
        "linked_customer": (
            conversation.get("crm_customer") or
            conversation.get("metadata", {}).get("linked_customer")
        ),
        "linked_deal": (
            conversation.get("crm_deal") or
            conversation.get("metadata", {}).get("linked_deal")
        ),
        "creation": conversation.get("creation"),
        "modified": conversation.get("modified"),
        "owner": conversation.get("owner")
    }

    return field_map.get(field_name, conversation.get(field_name))


def apply_filter_operator(field_value: Any, operator: str, filter_value: Any) -> bool:
    """
    Aplica un operador de filtro específico.

    Args:
        field_value: Valor del campo
        operator: Operador (=, !=, like, >, <, etc.)
        filter_value: Valor del filtro

    Returns:
        True si pasa el filtro, False si no
    """
    if field_value is None:
        return operator.lower() in ["is", "is not"] and filter_value in [None, ""]

    operator = operator.lower()

    try:
        if operator in ["=", "equals"]:
            return field_value == filter_value
        elif operator in ["!=", "not equals"]:
            return field_value != filter_value
        elif operator == "like":
            return str(filter_value).replace("%", "") in str(field_value)
        elif operator == "not like":
            return str(filter_value).replace("%", "") not in str(field_value)
        elif operator == ">":
            return field_value > filter_value
        elif operator == "<":
            return field_value < filter_value
        elif operator == ">=":
            return field_value >= filter_value
        elif operator == "<=":
            return field_value <= filter_value
        elif operator == "between":
            if isinstance(filter_value, list) and len(filter_value) == 2:
                return filter_value[0] <= field_value <= filter_value[1]
        elif operator == "in":
            return field_value in filter_value if isinstance(filter_value, list) else False
        elif operator == "not in":
            return field_value not in filter_value if isinstance(filter_value, list) else True
        elif operator == "is":
            return field_value is None or field_value == ""
        elif operator == "is not":
            return field_value is not None and field_value != ""

    except Exception:
        return False

    return False


def calculate_conversation_stats(conversations: List[Dict]) -> Dict[str, Any]:
    """
    Calcula estadísticas de las conversaciones filtradas.

    Args:
        conversations: Lista de conversaciones

    Returns:
        Diccionario con estadísticas
    """
    if not conversations:
        return {
            "total": 0,
            "unread": 0,
            "groups": 0,
            "individual": 0,
            "assigned": 0,
            "with_crm_link": 0
        }

    stats = {
        "total": len(conversations),
        "unread": sum(1 for c in conversations if (c.get("unread_count", 0) > 0)),
        "groups": sum(1 for c in conversations if c.get("is_group", False)),
        "individual": sum(1 for c in conversations if not c.get("is_group", False)),
        "assigned": sum(1 for c in conversations if (
            c.get("assigned_to") or
            c.get("metadata", {}).get("assigned_to")
        )),
        "with_crm_link": sum(1 for c in conversations if (
            c.get("crm_lead") or
            c.get("crm_customer") or
            c.get("crm_deal") or
            c.get("metadata", {}).get("linked_lead") or
            c.get("metadata", {}).get("linked_customer") or
            c.get("metadata", {}).get("linked_deal")
        ))
    }

    return stats


@frappe.whitelist()
def get_conversation_stats(session_id: str = None, filters: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Obtiene solo las estadísticas de conversaciones sin devolver los datos completos.
    Útil para mostrar contadores en la UI.

    Args:
        session_id: ID de la sesión
        filters: Filtros a aplicar

    Returns:
        Diccionario con estadísticas
    """
    try:
        result = get_filtered_conversations(
            session_id=session_id,
            filters=filters,
            limit=1000  # Límite alto para estadísticas precisas
        )

        if result.get("success"):
            return {
                "success": True,
                "stats": result.get("stats", {}),
                "total_count": result.get("total_count", 0)
            }
        else:
            return result

    except Exception as e:
        frappe.log_error(f"Error getting conversation stats: {str(e)}", "WhatsApp Filters Error")
        return {
            "success": False,
            "message": str(e),
            "stats": {}
        }
