#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Layer para Xappiens WhatsApp.
Conecta con el servidor externo de WhatsApp y sincroniza datos con Frappe.
"""

from .base import WhatsAppAPIClient
from .session import (
    start_session,
    get_session_status,
    get_qr_code,
    disconnect_session,
    reconnect_session,
)
from .contacts import (
    sync_contacts,
    get_contact_details,
    update_contact_avatar,
)
from .messages import (
    sync_messages,
    send_message,
    get_chat_messages,
)
from .conversations import (
    sync_conversations,
    get_conversation_details,
)
from .sync import (
    sync_session_data,
    auto_sync_all_sessions,
)

__all__ = [
    "WhatsAppAPIClient",
    "start_session",
    "get_session_status",
    "get_qr_code",
    "disconnect_session",
    "reconnect_session",
    "sync_contacts",
    "get_contact_details",
    "update_contact_avatar",
    "sync_messages",
    "send_message",
    "get_chat_messages",
    "sync_conversations",
    "get_conversation_details",
    "sync_session_data",
    "auto_sync_all_sessions",
]

