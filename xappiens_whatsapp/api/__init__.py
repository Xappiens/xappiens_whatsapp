#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Layer para Xappiens WhatsApp.
Conecta con el servidor externo de WhatsApp y sincroniza datos con Frappe.
"""

from .base import WhatsAppAPIClient
from .session import (
    start_session,
    get_qr_code,
    disconnect_session,
    reconnect_session,
    get_session_status,
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
    get_messages,
    get_profile_pic,
    mark_as_read,
)
from .conversations import (
    sync_conversations,
    get_conversation_details,
    get_conversations,
)
from .sync import (
    sync_session_data,
    auto_sync_all_sessions,
)
from .contacts_linking import (
    bulk_auto_link_contacts,
    auto_link_single_contact,
    unlink_single_contact,
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
    "get_messages",
    "get_profile_pic",
    "mark_as_read",
    "sync_conversations",
    "get_conversation_details",
    "get_conversations",
    "sync_session_data",
    "auto_sync_all_sessions",
    "bulk_auto_link_contacts",
    "auto_link_single_contact",
    "unlink_single_contact",
]

