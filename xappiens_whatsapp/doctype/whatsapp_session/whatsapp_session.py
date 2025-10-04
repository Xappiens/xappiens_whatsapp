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
		"""Connect to WhatsApp session via API."""
		try:
			from xappiens_whatsapp.api.session import start_session
			result = start_session(self.session_id)

			if result.get("success"):
				self.is_connected = True
				self.status = "Connected"
				self.connected_at = now()
				self.last_activity = now()
				self.save()

				return {"success": True, "message": "Session connected successfully"}
			else:
				return {"success": False, "message": result.get("message", "Failed to connect")}

		except Exception as e:
			frappe.log_error(f"Error connecting session {self.session_id}: {str(e)}")
			return {"success": False, "message": str(e)}

	@frappe.whitelist()
	def disconnect_session(self):
		"""Disconnect from WhatsApp session."""
		try:
			from xappiens_whatsapp.api.session import disconnect_session
			result = disconnect_session(self.session_id)

			if result.get("success"):
				self.is_connected = False
				self.status = "Disconnected"
				self.last_activity = now()
				self.save()

				return {"success": True, "message": "Session disconnected successfully"}
			else:
				return {"success": False, "message": result.get("message", "Failed to disconnect")}

		except Exception as e:
			frappe.log_error(f"Error disconnecting session {self.session_id}: {str(e)}")
			return {"success": False, "message": str(e)}

	@frappe.whitelist()
	def get_qr_code(self):
		"""Get QR code for session."""
		try:
			from xappiens_whatsapp.api.session import get_session_qr
			result = get_session_qr(self.session_id)

			if result.get("success"):
				self.qr_code = result.get("qr")
				self.qr_generated_at = now()
				self.status = "QR Pending"
				self.save()

				return {"success": True, "qr_code": self.qr_code}
			else:
				return {"success": False, "message": result.get("message", "Failed to get QR")}

		except Exception as e:
			frappe.log_error(f"Error getting QR for session {self.session_id}: {str(e)}")
			return {"success": False, "message": str(e)}

	@frappe.whitelist()
	def sync_contacts(self):
		"""Sync contacts from WhatsApp API."""
		try:
			from xappiens_whatsapp.api.contacts import sync_session_contacts
			result = sync_session_contacts(self.session_id)

			self.update_statistics()

			return result

		except Exception as e:
			frappe.log_error(f"Error syncing contacts for session {self.session_id}: {str(e)}")
			return {"success": False, "message": str(e)}

	@frappe.whitelist()
	def sync_conversations(self):
		"""Sync conversations from WhatsApp API."""
		try:
			from xappiens_whatsapp.api.conversations import sync_session_conversations
			result = sync_session_conversations(self.session_id)

			self.update_statistics()

			return result

		except Exception as e:
			frappe.log_error(f"Error syncing conversations for session {self.session_id}: {str(e)}")
			return {"success": False, "message": str(e)}

