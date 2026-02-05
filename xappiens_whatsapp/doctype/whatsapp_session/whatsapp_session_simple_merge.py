"""
Funcionalidad simplificada de fusión para WhatsApp Session
Usa directamente la funcionalidad nativa de Frappe
"""

import frappe
from frappe import _
from frappe.model.rename_doc import rename_doc


@frappe.whitelist()
def simple_merge_sessions(old_session: str, new_session: str):
    """
    Fusionar sesiones usando la funcionalidad nativa de Frappe
    """
    try:
        # Validaciones básicas
        if not frappe.db.exists("WhatsApp Session", old_session):
            return {"success": False, "error": f"Sesión origen '{old_session}' no encontrada"}

        if not frappe.db.exists("WhatsApp Session", new_session):
            return {"success": False, "error": f"Sesión destino '{new_session}' no encontrada"}

        if old_session == new_session:
            return {"success": False, "error": "No se puede fusionar una sesión consigo misma"}

        # Obtener datos antes de la fusión
        old_doc = frappe.get_doc("WhatsApp Session", old_session)
        new_doc = frappe.get_doc("WhatsApp Session", new_session)

        # Validar que la sesión origen no esté conectada
        if old_doc.is_connected and old_doc.status == "Connected":
            return {"success": False, "error": "No se puede fusionar una sesión que está conectada. Desconecte la sesión primero."}

        # Obtener estadísticas antes de la fusión
        stats_before = get_session_statistics(old_session)

        # Ejecutar la fusión usando la funcionalidad nativa de Frappe
        frappe.log_error(f"Iniciando fusión simple: {old_session} -> {new_session}", "WhatsApp Simple Merge")

        # Usar rename_doc con merge=True
        result = rename_doc(
            doctype="WhatsApp Session",
            old=old_session,
            new=new_session,
            merge=True,
            ignore_permissions=True,
            show_alert=False
        )

        # Obtener estadísticas después de la fusión
        stats_after = get_session_statistics(new_session)

        frappe.log_error(f"Fusión simple completada: {old_session} -> {new_session}", "WhatsApp Simple Merge Success")

        return {
            "success": True,
            "message": f"Sesión '{old_session}' fusionada exitosamente con '{new_session}'",
            "stats_transferred": stats_before,
            "final_stats": stats_after
        }

    except Exception as e:
        error_msg = f"Error en fusión simple {old_session} -> {new_session}: {str(e)}"
        frappe.log_error(error_msg, "WhatsApp Simple Merge Error")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_simple_merge_preview(old_session: str, new_session: str):
    """
    Obtener vista previa simplificada de la fusión
    """
    try:
        # Validaciones básicas
        if not frappe.db.exists("WhatsApp Session", old_session):
            return {"success": False, "error": f"Sesión origen '{old_session}' no encontrada"}

        if not frappe.db.exists("WhatsApp Session", new_session):
            return {"success": False, "error": f"Sesión destino '{new_session}' no encontrada"}

        # Obtener documentos
        old_doc = frappe.get_doc("WhatsApp Session", old_session)
        new_doc = frappe.get_doc("WhatsApp Session", new_session)

        # Obtener estadísticas
        old_stats = get_session_statistics(old_session)
        new_stats = get_session_statistics(new_session)

        # Detectar conflictos potenciales
        conflicts = []

        # Contactos duplicados
        duplicate_contacts = frappe.db.sql("""
            SELECT COUNT(*) as count
            FROM `tabWhatsApp Contact` old_contact
            INNER JOIN `tabWhatsApp Contact` new_contact
                ON old_contact.phone_number = new_contact.phone_number
            WHERE old_contact.session = %s
                AND new_contact.session = %s
                AND old_contact.phone_number IS NOT NULL
                AND old_contact.phone_number != ''
        """, (old_session, new_session))[0][0]

        if duplicate_contacts > 0:
            conflicts.append(f"{duplicate_contacts} contactos duplicados serán fusionados automáticamente")

        # Conversaciones duplicadas
        duplicate_conversations = frappe.db.sql("""
            SELECT COUNT(*) as count
            FROM `tabWhatsApp Conversation` old_conv
            INNER JOIN `tabWhatsApp Conversation` new_conv
                ON old_conv.chat_id = new_conv.chat_id
            WHERE old_conv.session = %s
                AND new_conv.session = %s
        """, (old_session, new_session))[0][0]

        if duplicate_conversations > 0:
            conflicts.append(f"{duplicate_conversations} conversaciones duplicadas serán fusionadas automáticamente")

        return {
            "success": True,
            "old_session": {
                "name": old_session,
                "session_name": old_doc.session_name,
                "phone_number": old_doc.phone_number,
                "status": old_doc.status,
                "is_connected": old_doc.is_connected
            },
            "new_session": {
                "name": new_session,
                "session_name": new_doc.session_name,
                "phone_number": new_doc.phone_number,
                "status": new_doc.status,
                "is_connected": new_doc.is_connected
            },
            "statistics": old_stats,
            "current_destination_stats": new_stats,
            "potential_conflicts": conflicts,
            "warning": "Esta operación no se puede deshacer. Todos los datos de la sesión origen se transferirán a la sesión destino y la sesión origen será eliminada."
        }

    except Exception as e:
        frappe.log_error(f"Error obteniendo preview simple: {str(e)}")
        return {"success": False, "error": f"Error interno: {str(e)}"}


def get_session_statistics(session_name: str):
    """Obtener estadísticas de una sesión"""
    try:
        stats = {}

        # Doctypes relacionados con session
        related_doctypes = [
            "WhatsApp Contact",
            "WhatsApp Conversation",
            "WhatsApp Message",
            "WhatsApp Group",
            "WhatsApp Analytics",
            "WhatsApp Activity Log",
            "WhatsApp Webhook Log",
            "WhatsApp Media File"
        ]

        for doctype in related_doctypes:
            try:
                count = frappe.db.count(doctype, {"session": session_name})
                stats[doctype.replace(" ", "_").lower()] = count
            except Exception:
                stats[doctype.replace(" ", "_").lower()] = 0

        return stats

    except Exception as e:
        frappe.log_error(f"Error obteniendo estadísticas: {str(e)}")
        return {}
