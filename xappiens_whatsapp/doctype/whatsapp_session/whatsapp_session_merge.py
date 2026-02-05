"""
Funcionalidad de fusión para WhatsApp Session
Permite combinar dos sesiones de WhatsApp y transferir todos los datos relacionados
"""

import frappe
from frappe import _
from frappe.model.document import Document
from typing import Dict, Any, List


class WhatsAppSessionMerge:
    """Clase para manejar la fusión de sesiones de WhatsApp"""

    def __init__(self, old_session: str, new_session: str):
        self.old_session = old_session
        self.new_session = new_session
        self.old_doc = None
        self.new_doc = None

    def validate_merge(self) -> Dict[str, Any]:
        """Validar que la fusión sea posible"""
        try:
            # Verificar que ambas sesiones existan
            if not frappe.db.exists("WhatsApp Session", self.old_session):
                return {"success": False, "error": f"Sesión origen '{self.old_session}' no encontrada"}

            if not frappe.db.exists("WhatsApp Session", self.new_session):
                return {"success": False, "error": f"Sesión destino '{self.new_session}' no encontrada"}

            # Cargar documentos
            self.old_doc = frappe.get_doc("WhatsApp Session", self.old_session)
            self.new_doc = frappe.get_doc("WhatsApp Session", self.new_session)

            # Verificar que no sean la misma sesión
            if self.old_session == self.new_session:
                return {"success": False, "error": "No se puede fusionar una sesión consigo misma"}

            # Obtener estadísticas de datos a fusionar
            stats = self.get_merge_statistics()

            return {
                "success": True,
                "statistics": stats,
                "old_session_name": self.old_doc.session_name,
                "new_session_name": self.new_doc.session_name
            }

        except Exception as e:
            frappe.log_error(f"Error validando fusión de sesiones: {str(e)}")
            return {"success": False, "error": f"Error interno: {str(e)}"}

    def get_merge_statistics(self) -> Dict[str, int]:
        """Obtener estadísticas de los datos que se van a fusionar"""
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
                count = frappe.db.count(doctype, {"session": self.old_session})
                stats[doctype.replace(" ", "_").lower()] = count
            except Exception:
                stats[doctype.replace(" ", "_").lower()] = 0

        return stats

    def execute_merge(self) -> Dict[str, Any]:
        """Ejecutar la fusión de sesiones"""
        try:
            # Validar antes de proceder
            validation = self.validate_merge()
            if not validation["success"]:
                return validation

            # Log del inicio del proceso
            frappe.log_error(f"Iniciando fusión: {self.old_session} -> {self.new_session}", "WhatsApp Merge Info")

            # 1. Fusionar estadísticas numéricas (sin transacción aún)
            self.merge_statistics()

            # 2. Manejar conflictos de datos únicos (con transacciones pequeñas)
            conflicts = self.handle_unique_conflicts()

            # 3. Fusionar metadatos específicos
            self.merge_metadata()

            # 4. Guardar sesión destino actualizada
            self.new_doc.save(ignore_permissions=True)
            frappe.db.commit()

            # Log del éxito
            frappe.log_error(f"Fusión completada exitosamente: {self.old_session} -> {self.new_session}", "WhatsApp Merge Success")

            return {
                "success": True,
                "message": f"Sesión '{self.old_session}' fusionada exitosamente con '{self.new_session}'",
                "conflicts_handled": conflicts,
                "final_statistics": self.get_merge_statistics_for_session(self.new_session)
            }

        except Exception as e:
            frappe.db.rollback()
            error_msg = f"Error ejecutando fusión de sesiones {self.old_session} -> {self.new_session}: {str(e)}"
            frappe.log_error(error_msg, "WhatsApp Merge Error")
            return {"success": False, "error": f"Error durante la fusión: {str(e)}"}

    def merge_statistics(self):
        """Fusionar estadísticas numéricas"""
        # Sumar contadores
        self.new_doc.total_contacts += (self.old_doc.total_contacts or 0)
        self.new_doc.total_chats += (self.old_doc.total_chats or 0)
        self.new_doc.total_messages_sent += (self.old_doc.total_messages_sent or 0)
        self.new_doc.total_messages_received += (self.old_doc.total_messages_received or 0)

        # Mantener el estado más reciente (sesión destino prevalece)
        # Solo actualizar si la sesión origen está más actualizada
        if self.old_doc.last_seen and (not self.new_doc.last_seen or self.old_doc.last_seen > self.new_doc.last_seen):
            self.new_doc.last_seen = self.old_doc.last_seen

    def handle_unique_conflicts(self) -> List[str]:
        """Manejar conflictos en datos únicos como contactos duplicados"""
        conflicts = []

        try:
            # 1. Manejar contactos duplicados por phone_number
            duplicate_contacts = frappe.db.sql("""
                SELECT old_contact.name as old_name, new_contact.name as new_name,
                       old_contact.phone_number
                FROM `tabWhatsApp Contact` old_contact
                INNER JOIN `tabWhatsApp Contact` new_contact
                    ON old_contact.phone_number = new_contact.phone_number
                WHERE old_contact.session = %s
                    AND new_contact.session = %s
                    AND old_contact.phone_number IS NOT NULL
                    AND old_contact.phone_number != ''
            """, (self.old_session, self.new_session), as_dict=True)

            for duplicate in duplicate_contacts:
                try:
                    # Actualizar mensajes y conversaciones para usar el contacto de la sesión destino
                    frappe.db.sql("""
                        UPDATE `tabWhatsApp Message`
                        SET contact = %s
                        WHERE contact = %s
                    """, (duplicate["new_name"], duplicate["old_name"]))

                    frappe.db.sql("""
                        UPDATE `tabWhatsApp Conversation`
                        SET contact = %s
                        WHERE contact = %s
                    """, (duplicate["new_name"], duplicate["old_name"]))

                    # Eliminar contacto duplicado de la sesión origen
                    frappe.delete_doc("WhatsApp Contact", duplicate["old_name"], ignore_permissions=True, force=True)

                    conflicts.append(f"Contacto duplicado fusionado: {duplicate['phone_number']}")

                except Exception as e:
                    frappe.log_error(f"Error fusionando contacto {duplicate['old_name']}: {str(e)}", "WhatsApp Merge Contact Error")
                    continue

            # 2. Manejar conversaciones duplicadas por chat_id
            duplicate_conversations = frappe.db.sql("""
                SELECT old_conv.name as old_name, new_conv.name as new_name,
                       old_conv.chat_id, old_conv.total_messages, old_conv.unread_count,
                       old_conv.last_message, old_conv.last_message_time, old_conv.last_message_from_me
                FROM `tabWhatsApp Conversation` old_conv
                INNER JOIN `tabWhatsApp Conversation` new_conv
                    ON old_conv.chat_id = new_conv.chat_id
                WHERE old_conv.session = %s
                    AND new_conv.session = %s
            """, (self.old_session, self.new_session), as_dict=True)

            for duplicate in duplicate_conversations:
                try:
                    # Mover mensajes de la conversación duplicada a la conversación destino
                    frappe.db.sql("""
                        UPDATE `tabWhatsApp Message`
                        SET conversation = %s
                        WHERE conversation = %s
                    """, (duplicate["new_name"], duplicate["old_name"]))

                    # Actualizar contadores en la conversación destino
                    frappe.db.sql("""
                        UPDATE `tabWhatsApp Conversation`
                        SET total_messages = COALESCE(total_messages, 0) + %s,
                            unread_count = COALESCE(unread_count, 0) + %s
                        WHERE name = %s
                    """, (duplicate.get("total_messages", 0), duplicate.get("unread_count", 0), duplicate["new_name"]))

                    # Actualizar último mensaje si es más reciente
                    if duplicate.get("last_message_time"):
                        frappe.db.sql("""
                            UPDATE `tabWhatsApp Conversation`
                            SET last_message = %s,
                                last_message_time = %s,
                                last_message_from_me = %s
                            WHERE name = %s
                                AND (last_message_time IS NULL OR last_message_time < %s)
                        """, (
                            duplicate.get("last_message"),
                            duplicate.get("last_message_time"),
                            duplicate.get("last_message_from_me", 0),
                            duplicate["new_name"],
                            duplicate.get("last_message_time")
                        ))

                    # Eliminar conversación duplicada
                    frappe.delete_doc("WhatsApp Conversation", duplicate["old_name"], ignore_permissions=True, force=True)

                    conflicts.append(f"Conversación duplicada fusionada: {duplicate['chat_id']}")

                except Exception as e:
                    frappe.log_error(f"Error fusionando conversación {duplicate['old_name']}: {str(e)}", "WhatsApp Merge Conversation Error")
                    continue

        except Exception as e:
            frappe.log_error(f"Error general en handle_unique_conflicts: {str(e)}", "WhatsApp Merge Conflicts Error")

        return conflicts

    def merge_metadata(self):
        """Fusionar metadatos y campos adicionales"""
        # Si la sesión origen tiene información que falta en la destino, copiarla
        if self.old_doc.phone_number and not self.new_doc.phone_number:
            self.new_doc.phone_number = self.old_doc.phone_number

        if self.old_doc.error_message and not self.new_doc.error_message:
            self.new_doc.error_message = self.old_doc.error_message
            self.new_doc.error_code = self.old_doc.error_code

        # Fusionar usuarios asignados
        if self.old_doc.assigned_users:
            existing_users = [user.user for user in (self.new_doc.assigned_users or [])]
            for old_user in self.old_doc.assigned_users:
                if old_user.user not in existing_users:
                    self.new_doc.append("assigned_users", {
                        "user": old_user.user,
                        "role": old_user.role,
                        "assigned_at": old_user.assigned_at
                    })

    def get_merge_statistics_for_session(self, session_name: str) -> Dict[str, int]:
        """Obtener estadísticas finales después de la fusión"""
        stats = {}

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


@frappe.whitelist()
def validate_session_merge(old_session: str, new_session: str) -> Dict[str, Any]:
    """API endpoint para validar una fusión de sesiones"""
    merger = WhatsAppSessionMerge(old_session, new_session)
    return merger.validate_merge()


@frappe.whitelist()
def execute_session_merge(old_session: str, new_session: str) -> Dict[str, Any]:
    """API endpoint para ejecutar una fusión de sesiones"""
    merger = WhatsAppSessionMerge(old_session, new_session)
    return merger.execute_merge()


@frappe.whitelist()
def get_session_merge_preview(old_session: str, new_session: str) -> Dict[str, Any]:
    """Obtener vista previa de lo que se fusionará"""
    try:
        merger = WhatsAppSessionMerge(old_session, new_session)
        validation = merger.validate_merge()

        if not validation["success"]:
            return validation

        # Obtener detalles adicionales
        old_doc = frappe.get_doc("WhatsApp Session", old_session)
        new_doc = frappe.get_doc("WhatsApp Session", new_session)

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
            conflicts.append(f"{duplicate_contacts} contactos duplicados serán fusionados")

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
            conflicts.append(f"{duplicate_conversations} conversaciones duplicadas serán fusionadas")

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
            "statistics": validation["statistics"],
            "potential_conflicts": conflicts,
            "warning": "Esta operación no se puede deshacer. Todos los datos de la sesión origen se transferirán a la sesión destino y la sesión origen será eliminada."
        }

    except Exception as e:
        frappe.log_error(f"Error obteniendo preview de fusión: {str(e)}")
        return {"success": False, "error": f"Error interno: {str(e)}"}
