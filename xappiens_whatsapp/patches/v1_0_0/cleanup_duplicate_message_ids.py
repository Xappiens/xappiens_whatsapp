"""
Patch para limpiar message_ids duplicados en WhatsApp Message
antes de aplicar la restricción unique
"""

import frappe
from frappe import _

def execute():
    """Limpiar message_ids duplicados en tabWhatsApp Message"""

    # Verificar si la tabla existe
    if not frappe.db.table_exists("WhatsApp Message"):
        return

    # Obtener todos los message_ids duplicados
    duplicate_message_ids = frappe.db.sql("""
        SELECT message_id, COUNT(*) as count
        FROM `tabWhatsApp Message`
        WHERE message_id IS NOT NULL AND message_id != ''
        GROUP BY message_id
        HAVING COUNT(*) > 1
        ORDER BY count DESC
    """, as_dict=True)

    if not duplicate_message_ids:
        frappe.msgprint(_("No se encontraron message_ids duplicados"))
        return

    frappe.msgprint(_("Encontrados {0} message_ids duplicados").format(len(duplicate_message_ids)))

    # Limpiar duplicados manteniendo solo el más reciente
    for duplicate in duplicate_message_ids:
        message_id = duplicate.message_id

        # Obtener todos los registros con este message_id
        duplicate_records = frappe.db.sql("""
            SELECT name, creation
            FROM `tabWhatsApp Message`
            WHERE message_id = %s
            ORDER BY creation DESC
        """, (message_id,), as_dict=True)

        # Mantener solo el más reciente, eliminar el resto
        if len(duplicate_records) > 1:
            records_to_delete = duplicate_records[1:]  # Todos excepto el primero (más reciente)

            for record in records_to_delete:
                # Actualizar el message_id para que sea único
                new_message_id = f"{message_id}_duplicate_{record.name}"
                frappe.db.sql("""
                    UPDATE `tabWhatsApp Message`
                    SET message_id = %s
                    WHERE name = %s
                """, (new_message_id, record.name))

                frappe.msgprint(_("Actualizado message_id duplicado: {0} -> {1}").format(
                    message_id, new_message_id
                ))

    frappe.db.commit()
    frappe.msgprint(_("Limpieza de message_ids duplicados completada"))
