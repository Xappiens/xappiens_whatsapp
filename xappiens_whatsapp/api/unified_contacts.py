"""
API Unificada por Contactos - WhatsApp Session Agnostic
Agrupa conversaciones y mensajes por número de teléfono, independientemente de la sesión
"""

import frappe
from frappe import _
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import re


def normalize_phone_number(phone: str) -> str:
    """Normalizar número de teléfono para comparación"""
    if not phone:
        return ""

    # Remover caracteres no numéricos
    clean_phone = re.sub(r'[^\d+]', '', str(phone))

    # Remover sufijos de WhatsApp (@c.us, @s.whatsapp.net)
    if '@' in clean_phone:
        clean_phone = clean_phone.split('@')[0]

    # Normalizar formato internacional
    if clean_phone.startswith('00'):
        clean_phone = '+' + clean_phone[2:]
    elif clean_phone.startswith('34') and len(clean_phone) == 11:
        clean_phone = '+' + clean_phone
    elif not clean_phone.startswith('+') and len(clean_phone) == 9:
        clean_phone = '+34' + clean_phone

    return clean_phone


def select_best_contact_name(all_names: str, phone_number: str) -> str:
    """
    Seleccionar el mejor contact_name de una lista de nombres separados por '|||'

    Prioridad:
    1. Nombres que no contengan "@" (formato de WhatsApp)
    2. Nombres que no sean solo números
    3. Nombres que no sean iguales al número de teléfono
    4. Si todos son números o tienen formato de WhatsApp, usar el primero disponible

    Args:
        all_names: String con nombres separados por '|||'
        phone_number: Número de teléfono para comparación

    Returns:
        El mejor nombre disponible, o phone_number si no hay nombres válidos
    """
    if not all_names:
        return phone_number

    # Separar nombres únicos
    names = [name.strip() for name in all_names.split('|||') if name and name.strip()]

    if not names:
        return phone_number

    # Normalizar número de teléfono para comparación
    normalized_phone = normalize_phone_number(phone_number)
    phone_without_plus = normalized_phone.replace('+', '')

    # Categorizar nombres por calidad
    best_names = []  # Nombres sin @, no solo números, diferentes al teléfono
    good_names = []  # Nombres sin @, pero pueden ser números o iguales al teléfono
    fallback_names = []  # Nombres con @ o solo números

    for name in names:
        name_clean = name.strip()
        if not name_clean:
            continue

        # Verificar si es solo números
        is_only_numbers = re.match(r'^[\d\s\+\-\(\)]+$', name_clean) is not None

        # Verificar si contiene @ (formato WhatsApp)
        has_at_symbol = '@' in name_clean

        # Verificar si es igual al número de teléfono
        normalized_name = normalize_phone_number(name_clean)
        is_same_as_phone = (
            normalized_name == normalized_phone or
            normalized_name == phone_without_plus or
            name_clean == phone_number or
            name_clean == normalized_phone or
            name_clean == phone_without_plus
        )

        # Categorizar
        if not has_at_symbol and not is_only_numbers and not is_same_as_phone:
            best_names.append(name_clean)
        elif not has_at_symbol:
            good_names.append(name_clean)
        else:
            fallback_names.append(name_clean)

    # Seleccionar el mejor disponible
    if best_names:
        return best_names[0]  # Usar el primero de los mejores
    elif good_names:
        return good_names[0]  # Usar el primero de los buenos
    elif fallback_names:
        return fallback_names[0]  # Usar el primero de los fallback
    else:
        return phone_number  # Fallback al número de teléfono


@frappe.whitelist()
def get_unified_contacts(
    search: str = None,
    limit: int = 50,
    offset: int = 0,
    only_unread: bool = False,
    only_my_assigned: bool = False,
    time_period: str = 'all'
) -> Dict[str, Any]:
    """
    Obtener lista de contactos unificados (agrupados por número de teléfono)
    independientemente de la sesión de WhatsApp

    Args:
        search: Filtro de texto por nombre o teléfono
        limit: Límite de resultados
        offset: Offset para paginación
        only_unread: Solo conversaciones con mensajes no leídos
        only_my_assigned: Solo conversaciones de leads asignados al usuario actual
        time_period: Filtro de tiempo (today, week, month, quarter, all)
    """
    try:
        # Obtener usuario actual para filtros de asignación
        current_user = frappe.session.user

        # Calcular fecha de corte para filtros de tiempo
        time_cutoff = None
        if time_period != 'all':
            now = datetime.now()
            if time_period == 'today':
                time_cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif time_period == 'week':
                time_cutoff = now - timedelta(days=7)
            elif time_period == 'month':
                time_cutoff = now - timedelta(days=30)
            elif time_period == 'quarter':
                time_cutoff = now - timedelta(days=90)

        # Query base para obtener contactos únicos por teléfono
        # Incluir JOIN con CRM Lead para filtros de asignación
        # Obtener todos los contact_name posibles para seleccionar el mejor en Python
        base_query = """
            SELECT
                c.phone_number,
                GROUP_CONCAT(DISTINCT c.contact_name SEPARATOR '|||') as all_contact_names,
                COUNT(DISTINCT c.session) as session_count,
                GROUP_CONCAT(DISTINCT c.session) as sessions,
                MAX(c.last_message_time) as last_activity,
                SUM(c.unread_count) as total_unread,
                COUNT(*) as conversation_count,
                MAX(c.linked_lead) as linked_lead,
                MAX(c.linked_customer) as linked_customer,
                MAX(l.lead_name) as lead_name,
                MAX(l._assign) as lead_assigned_to
            FROM `tabWhatsApp Conversation` c
            LEFT JOIN `tabCRM Lead` l ON c.linked_lead = l.name
            WHERE c.phone_number IS NOT NULL
                AND c.phone_number != ''
                AND c.status = 'Active'
        """

        params = []

        # Filtro por mensajes no leídos
        if only_unread:
            base_query += " AND c.unread_count > 0"

        # Filtro por asignación de leads
        if only_my_assigned:
            base_query += " AND (l._assign LIKE %s OR l._assign = %s)"
            user_pattern = f"%{current_user}%"
            params.extend([user_pattern, current_user])

        # Filtro por tiempo
        if time_cutoff:
            base_query += " AND c.last_message_time >= %s"
            params.append(time_cutoff)

        # Agregar filtro de búsqueda si se proporciona
        if search:
            base_query += " AND (c.contact_name LIKE %s OR c.phone_number LIKE %s)"
            search_param = f"%{search}%"
            params.extend([search_param, search_param])

        # Agrupar por teléfono
        base_query += """
            GROUP BY c.phone_number
            ORDER BY last_activity DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])

        contacts = frappe.db.sql(base_query, params, as_dict=True)

        # Enriquecer cada contacto con información adicional
        enriched_contacts = []
        for contact in contacts:
            # Obtener información del lead si existe
            lead_info = None
            if contact.linked_lead:
                lead_info = frappe.get_value("CRM Lead", contact.linked_lead,
                                           ["name", "lead_name", "status"], as_dict=True)

            # Obtener último mensaje
            last_message = get_last_message_for_phone(contact.phone_number)

            # Obtener sesiones activas para este contacto
            active_sessions = get_active_sessions_for_phone(contact.phone_number)

            # Verificar si el lead está asignado al usuario actual
            is_assigned_to_me = False
            if contact.lead_assigned_to and current_user:
                is_assigned_to_me = current_user in (contact.lead_assigned_to or '')

            # Seleccionar el mejor contact_name de todos los disponibles
            best_contact_name = select_best_contact_name(
                contact.all_contact_names or '',
                contact.phone_number
            )

            enriched_contact = {
                "phone_number": contact.phone_number,
                "contact_name": best_contact_name,
                "session_count": contact.session_count,
                "sessions": contact.sessions.split(',') if contact.sessions else [],
                "active_sessions": active_sessions,
                "last_activity": contact.last_activity,
                "total_unread": contact.total_unread or 0,
                "conversation_count": contact.conversation_count,
                "linked_lead": lead_info,
                "last_message": last_message,
                "normalized_phone": normalize_phone_number(contact.phone_number),
                "is_assigned_to_me": is_assigned_to_me,
                "assigned_to": contact.lead_assigned_to
            }

            enriched_contacts.append(enriched_contact)

        # Obtener total para paginación (usar la misma lógica de filtros)
        count_query = """
            SELECT COUNT(DISTINCT c.phone_number) as total
            FROM `tabWhatsApp Conversation` c
            LEFT JOIN `tabCRM Lead` l ON c.linked_lead = l.name
            WHERE c.phone_number IS NOT NULL
                AND c.phone_number != ''
                AND c.status = 'Active'
        """

        count_params = []

        # Aplicar los mismos filtros que en la query principal
        if only_unread:
            count_query += " AND c.unread_count > 0"

        if only_my_assigned:
            count_query += " AND (l._assign LIKE %s OR l._assign = %s)"
            user_pattern = f"%{current_user}%"
            count_params.extend([user_pattern, current_user])

        if time_cutoff:
            count_query += " AND c.last_message_time >= %s"
            count_params.append(time_cutoff)

        if search:
            count_query += " AND (c.contact_name LIKE %s OR c.phone_number LIKE %s)"
            count_params.extend([search_param, search_param])

        total_count = frappe.db.sql(count_query, count_params, as_dict=True)[0].total

        return {
            "success": True,
            "contacts": enriched_contacts,
            "total_count": total_count,
            "has_more": (offset + limit) < total_count,
            "applied_filters": {
                "only_unread": only_unread,
                "only_my_assigned": only_my_assigned,
                "time_period": time_period,
                "search": search,
                "current_user": current_user
            },
            "filter_stats": {
                "unread_count": sum(1 for c in enriched_contacts if c["total_unread"] > 0),
                "assigned_to_me_count": sum(1 for c in enriched_contacts if c["is_assigned_to_me"]),
                "total_displayed": len(enriched_contacts)
            }
        }

    except Exception as e:
        frappe.log_error(f"Error getting unified contacts: {str(e)}", "WhatsApp Unified Contacts")
        return {
            "success": False,
            "error": str(e),
            "contacts": [],
            "total_count": 0
        }


@frappe.whitelist()
def get_unified_conversation(phone_number: str, limit: int = 100) -> Dict[str, Any]:
    """
    Obtener conversación unificada para un número de teléfono
    Incluye TODOS los mensajes de TODAS las sesiones para ese número
    """
    try:
        normalized_phone = normalize_phone_number(phone_number)

        # Obtener todas las conversaciones para este número
        conversations = frappe.get_all("WhatsApp Conversation",
            filters={"phone_number": phone_number, "status": "Active"},
            fields=["name", "session", "contact_name", "chat_id", "linked_lead", "linked_customer"]
        )

        if not conversations:
            return {
                "success": True,
                "phone_number": phone_number,
                "contact_name": phone_number,
                "messages": [],
                "sessions": [],
                "total_messages": 0
            }

        # Obtener información de las sesiones
        session_info = {}
        for conv in conversations:
            if conv.session not in session_info:
                session_data = frappe.get_value("WhatsApp Session", conv.session,
                    ["session_name", "phone_number", "status", "is_connected"], as_dict=True)
                session_info[conv.session] = session_data

        # Obtener TODOS los mensajes de TODAS las conversaciones
        conversation_names = [conv.name for conv in conversations]

        messages_query = """
            SELECT
                m.*,
                c.session,
                c.contact_name as conversation_contact_name,
                c.chat_id
            FROM `tabWhatsApp Message` m
            JOIN `tabWhatsApp Conversation` c ON m.conversation = c.name
            WHERE m.conversation IN ({})
            ORDER BY m.timestamp DESC
            LIMIT %s
        """.format(','.join(['%s'] * len(conversation_names)))

        params = conversation_names + [limit]
        messages = frappe.db.sql(messages_query, params, as_dict=True)

        # Enriquecer mensajes con información de sesión
        enriched_messages = []
        for msg in messages:
            enriched_msg = dict(msg)
            enriched_msg["session_info"] = session_info.get(msg.session, {})
            enriched_msg["session_name"] = session_info.get(msg.session, {}).get("session_name", "Desconocida")
            enriched_messages.append(enriched_msg)

        # Información del contacto
        contact_name = conversations[0].contact_name or phone_number
        linked_lead = conversations[0].linked_lead

        # Información del lead si existe
        lead_info = None
        if linked_lead:
            lead_info = frappe.get_value("CRM Lead", linked_lead,
                ["name", "lead_name", "status", "mobile_no"], as_dict=True)

        return {
            "success": True,
            "phone_number": phone_number,
            "normalized_phone": normalized_phone,
            "contact_name": contact_name,
            "messages": enriched_messages,
            "conversations": conversations,
            "sessions": list(session_info.values()),
            "session_info": session_info,
            "total_messages": len(enriched_messages),
            "linked_lead": lead_info
        }

    except Exception as e:
        frappe.log_error(f"Error getting unified conversation for {phone_number}: {str(e)}", "WhatsApp Unified Conversation")
        return {
            "success": False,
            "error": str(e),
            "phone_number": phone_number,
            "messages": []
        }


@frappe.whitelist()
def send_message_smart(phone_number: str, message: str, preferred_session: str = None, file_path: str = None, media_type: str = None) -> Dict[str, Any]:
    """
    Enviar mensaje de forma inteligente (con soporte para archivos adjuntos):
    1. Si se especifica sesión preferida y está activa, usar esa
    2. Si no, usar la sesión más reciente que tenga conversación con ese número
    3. Si no hay conversación previa, usar cualquier sesión activa

    Args:
        phone_number: Número de teléfono del destinatario
        message: Contenido del mensaje
        preferred_session: Sesión preferida (opcional)
        file_path: Ruta del archivo adjunto (opcional)
        media_type: Tipo de media (opcional, se detecta automáticamente)
    """
    try:
        target_session = None
        target_conversation = None

        # Opción 1: Usar sesión preferida si está activa
        if preferred_session:
            session_status = frappe.get_value("WhatsApp Session", preferred_session,
                                            ["is_connected", "status"], as_dict=True)
            if session_status and session_status.is_connected and session_status.status == "Connected":
                target_session = preferred_session

        # Opción 2: Buscar sesión con conversación existente más reciente
        if not target_session:
            existing_conversations = frappe.get_all("WhatsApp Conversation",
                filters={"phone_number": phone_number, "status": "Active"},
                fields=["session", "last_message_time", "name"],
                order_by="last_message_time desc",
                limit=1
            )

            if existing_conversations:
                conv = existing_conversations[0]
                session_status = frappe.get_value("WhatsApp Session", conv.session,
                                                ["is_connected", "status"], as_dict=True)
                if session_status and session_status.is_connected and session_status.status == "Connected":
                    target_session = conv.session
                    target_conversation = conv.name

        # Opción 3: Usar cualquier sesión activa disponible (selección aleatoria)
        if not target_session:
            active_sessions = frappe.get_all("WhatsApp Session",
                filters={"is_connected": 1, "status": "Connected", "is_active": 1},
                fields=["name", "session_name"]
                # Sin limit para obtener todas las sesiones disponibles
            )

            if active_sessions:
                # Selección aleatoria para distribuir carga entre sesiones
                import random
                selected_session = random.choice(active_sessions)
                target_session = selected_session.name

        if not target_session:
            return {
                "success": False,
                "error": "No hay sesiones de WhatsApp activas disponibles"
            }

        # Enviar mensaje usando la API existente
        from .messages import send_message

        # Si no hay conversación existente, crear una nueva
        if not target_conversation:
            # Buscar o crear conversación
            chat_id = normalize_phone_number(phone_number)
            if not chat_id.endswith('@c.us'):
                chat_id = chat_id.replace('+', '') + '@c.us'

            existing_conv = frappe.get_value("WhatsApp Conversation",
                                           {"session": target_session, "phone_number": phone_number},
                                           "name")

            if existing_conv:
                target_conversation = existing_conv
            else:
                # Crear nueva conversación
                new_conv = frappe.get_doc({
                    "doctype": "WhatsApp Conversation",
                    "session": target_session,
                    "phone_number": phone_number,
                    "contact_name": phone_number,
                    "chat_id": chat_id,
                    "status": "Active"
                })
                new_conv.insert(ignore_permissions=True)
                target_conversation = new_conv.name

        # Detectar si hay cambio de sesión para notificar al usuario
        session_changed = False
        previous_session = None

        # Si había conversaciones previas, verificar si cambió la sesión
        if existing_conversations:
            last_conv = existing_conversations[0]
            previous_session = last_conv.session
            if previous_session != target_session:
                session_changed = True

        # Enviar mensaje de notificación si cambió la sesión
        if session_changed and previous_session:
            try:
                # Obtener nombres de las sesiones para el mensaje
                old_session_name = frappe.get_value("WhatsApp Session", previous_session, "session_name") or previous_session
                new_session_name = frappe.get_value("WhatsApp Session", target_session, "session_name") or target_session

                notification_message = f"🔄 *Cambio de sesión WhatsApp*\n\nEsta conversación ahora usa una sesión diferente:\n• Anterior: {old_session_name}\n• Actual: {new_session_name}\n\nTodos los mensajes anteriores se mantienen disponibles."

                # Enviar mensaje de notificación primero
                from .messages import send_message
                notification_result = send_message(target_conversation, notification_message)

                if notification_result.get("success"):
                    frappe.log_error(f"Session change notification sent for {phone_number}: {previous_session} -> {target_session}", "WhatsApp Session Change")
            except Exception as e:
                frappe.log_error(f"Error sending session change notification: {str(e)}", "WhatsApp Session Change Error")

        # Enviar el mensaje (con o sin archivo adjunto)
        if file_path:
            # Enviar mensaje con archivo adjunto
            from .messages import send_message_with_media
            result = send_message_with_media(target_conversation, message, file_path, media_type)
        else:
            # Enviar mensaje de texto normal
            from .messages import send_message
            result = send_message(target_conversation, message)

        if result.get("success"):
            # Agregar información de la sesión usada
            session_info = frappe.get_value("WhatsApp Session", target_session,
                                          ["session_name", "phone_number"], as_dict=True)
            result["sent_from_session"] = session_info
            result["conversation"] = target_conversation
            # Asegurar que el contenido del mensaje esté en la respuesta
            if not result.get("content") and not result.get("message"):
                result["content"] = message
                result["message"] = message
            # Forzar commit para asegurar que el mensaje esté disponible inmediatamente
            frappe.db.commit()

        return result

    except Exception as e:
        frappe.log_error(f"Error sending smart message to {phone_number}: {str(e)}", "WhatsApp Smart Send")
        return {
            "success": False,
            "error": str(e)
        }


def get_last_message_for_phone(phone_number: str) -> Optional[Dict[str, Any]]:
    """Obtener el último mensaje para un número de teléfono"""
    try:
        query = """
            SELECT m.content, m.timestamp, m.direction, m.message_type, c.session
            FROM `tabWhatsApp Message` m
            JOIN `tabWhatsApp Conversation` c ON m.conversation = c.name
            WHERE c.phone_number = %s
            ORDER BY m.timestamp DESC
            LIMIT 1
        """

        result = frappe.db.sql(query, [phone_number], as_dict=True)
        return result[0] if result else None

    except Exception:
        return None


def get_active_sessions_for_phone(phone_number: str) -> List[Dict[str, Any]]:
    """Obtener sesiones activas que tienen conversación con este número"""
    try:
        query = """
            SELECT DISTINCT s.name, s.session_name, s.phone_number, s.status, s.is_connected
            FROM `tabWhatsApp Session` s
            JOIN `tabWhatsApp Conversation` c ON s.name = c.session
            WHERE c.phone_number = %s AND s.is_active = 1
            ORDER BY s.is_connected DESC, c.last_message_time DESC
        """

        return frappe.db.sql(query, [phone_number], as_dict=True)

    except Exception:
        return []


@frappe.whitelist()
def search_unified_contacts(query: str, limit: int = 20) -> Dict[str, Any]:
    """Buscar contactos unificados por nombre o teléfono"""
    try:
        search_param = f"%{query}%"

        sql_query = """
            SELECT DISTINCT
                phone_number,
                GROUP_CONCAT(DISTINCT contact_name SEPARATOR '|||') as all_contact_names,
                COUNT(DISTINCT session) as session_count,
                MAX(last_message_time) as last_activity,
                SUM(unread_count) as total_unread
            FROM `tabWhatsApp Conversation`
            WHERE (contact_name LIKE %s OR phone_number LIKE %s)
                AND phone_number IS NOT NULL
                AND phone_number != ''
                AND status = 'Active'
            GROUP BY phone_number
            ORDER BY last_activity DESC
            LIMIT %s
        """

        results = frappe.db.sql(sql_query, [search_param, search_param, limit], as_dict=True)

        # Procesar resultados para seleccionar el mejor contact_name
        processed_results = []
        for contact in results:
            best_contact_name = select_best_contact_name(
                contact.all_contact_names or '',
                contact.phone_number
            )
            processed_results.append({
                "phone_number": contact.phone_number,
                "contact_name": best_contact_name,
                "session_count": contact.session_count,
                "last_activity": contact.last_activity,
                "total_unread": contact.total_unread
            })

        return {
            "success": True,
            "contacts": processed_results
        }

    except Exception as e:
        frappe.log_error(f"Error searching unified contacts: {str(e)}", "WhatsApp Unified Search")
        return {
            "success": False,
            "error": str(e),
            "contacts": []
        }


@frappe.whitelist()
def get_global_sessions_count() -> Dict[str, Any]:
    """
    Obtiene el contador global de sesiones de WhatsApp conectadas
    """
    try:
        # Contar sesiones conectadas
        connected_sessions = frappe.db.count(
            "WhatsApp Session",
            filters={
                "is_connected": 1,
                "status": "Connected"
            }
        )

        # Contar sesiones totales
        total_sessions = frappe.db.count("WhatsApp Session")

        return {
            "success": True,
            "connected_count": connected_sessions,
            "total_count": total_sessions,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        frappe.log_error(f"Error getting global sessions count: {str(e)}", "WhatsApp Global Sessions Count Error")
        return {
            "success": False,
            "error": str(e),
            "connected_count": 0,
            "total_count": 0
        }
