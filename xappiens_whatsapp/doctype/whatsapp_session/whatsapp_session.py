# Copyright (c) 2025, Xappiens and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now, get_datetime


class WhatsAppSession(Document):
	def before_insert(self):
		"""Set created_by before insert."""
		if not self.created_by:
			self.created_by = frappe.session.user

	def before_save(self):
		"""Update modified_by before save."""
		self.modified_by = frappe.session.user

		# Update last_activity when status changes
		if self.has_value_changed("status") or self.has_value_changed("is_connected"):
			self.last_activity = now()

	def validate(self):
		"""Validate session data."""
		# Validate session_id format
		if not self.session_id:
			frappe.throw("Session ID is required")

		# Update connection count when connected
		if self.has_value_changed("is_connected"):
			if self.is_connected:
				self.connection_count = (self.connection_count or 0) + 1
				self.connected_at = now()
				self.status = "Connected"
			else:
				self.disconnection_count = (self.disconnection_count or 0) + 1
				if self.status == "Connected":
					self.status = "Disconnected"

	def on_update(self):
		"""Actions after update."""
		# Clear QR code if connected
		if self.is_connected and self.qr_code:
			frappe.db.set_value("WhatsApp Session", self.name, "qr_code", None, update_modified=False)

	def update_statistics(self):
		"""Update session statistics from related documents."""
		# Count contacts
		self.total_contacts = frappe.db.count("WhatsApp Contact", {"session": self.name})

		# Count conversations
		self.total_chats = frappe.db.count("WhatsApp Conversation", {"session": self.name})

		# Count messages
		sent_count = frappe.db.count("WhatsApp Message", {
			"session": self.name,
			"direction": "Outgoing"
		})
		received_count = frappe.db.count("WhatsApp Message", {
			"session": self.name,
			"direction": "Incoming"
		})

		self.total_messages_sent = sent_count
		self.total_messages_received = received_count

		# Count unread
		self.unread_count = frappe.db.sql("""
			SELECT SUM(unread_count)
			FROM `tabWhatsApp Conversation`
			WHERE session = %s AND unread_count > 0
		""", self.name)[0][0] or 0

		# Count active conversations (with activity in last 24 hours)
		self.active_conversations = frappe.db.sql("""
			SELECT COUNT(*)
			FROM `tabWhatsApp Conversation`
			WHERE session = %s
			AND last_message_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
		""", self.name)[0][0] or 0

		self.save()

	@frappe.whitelist()
	def connect_session(self):
		"""Conectar sesión de WhatsApp."""
		try:
			from xappiens_whatsapp.api.session import start_session
			result = start_session(self.name)
			return result
		except Exception as e:
			frappe.log_error(f"Error al conectar sesión {self.session_id}: {str(e)}")
			return {"success": False, "message": str(e)}

	@frappe.whitelist()
	def disconnect_session_btn(self):
		"""Desconectar sesión de WhatsApp."""
		try:
			from xappiens_whatsapp.api.session import disconnect_session
			result = disconnect_session(self.name)
			return result
		except Exception as e:
			frappe.log_error(f"Error al desconectar sesión {self.session_id}: {str(e)}")
			return {"success": False, "message": str(e)}

	@frappe.whitelist()
	def get_qr_code_btn(self):
		"""Obtener código QR para escanear."""
		try:
			from xappiens_whatsapp.api.session import get_qr_code
			result = get_qr_code(self.name, as_image=True)
			return result
		except Exception as e:
			frappe.log_error(f"Error al obtener QR {self.session_id}: {str(e)}")
			return {"success": False, "message": str(e)}

	@frappe.whitelist()
	def check_status(self):
		"""Verificar estado de la sesión."""
		try:
			from xappiens_whatsapp.api.session import get_session_status
			result = get_session_status(self.name)
			return result
		except Exception as e:
			frappe.log_error(f"Error al verificar estado {self.session_id}: {str(e)}")
			return {"success": False, "message": str(e)}

	@frappe.whitelist()
	def sync_all_data(self):
		"""Sincronizar todos los datos (contactos, conversaciones, mensajes)."""
		try:
			from xappiens_whatsapp.api.sync import sync_session_data
			result = sync_session_data(
				self.name,
				sync_contacts_flag=True,
				sync_conversations_flag=True,
				sync_messages_flag=False  # Mensajes se sincronizan por conversación
			)
			return result
		except Exception as e:
			frappe.log_error(f"Error al sincronizar datos {self.session_id}: {str(e)}")
			return {"success": False, "message": str(e)}

	@frappe.whitelist()
	def sync_contacts_btn(self):
		"""Sincronizar solo contactos."""
		try:
			from xappiens_whatsapp.api.contacts import sync_contacts
			result = sync_contacts(self.name)
			self.reload()  # Recargar para mostrar estadísticas actualizadas
			return result
		except Exception as e:
			frappe.log_error(f"Error al sincronizar contactos {self.session_id}: {str(e)}")
			return {"success": False, "message": str(e)}

	@frappe.whitelist()
	def sync_conversations_btn(self):
		"""Sincronizar solo conversaciones."""
		try:
			from xappiens_whatsapp.api.conversations import sync_conversations
			result = sync_conversations(self.name)
			self.reload()  # Recargar para mostrar estadísticas actualizadas
			return result
		except Exception as e:
			frappe.log_error(f"Error al sincronizar conversaciones {self.session_id}: {str(e)}")
			return {"success": False, "message": str(e)}

