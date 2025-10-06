# Copyright (c) 2025, Xappiens and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now, get_datetime


class WhatsAppConversation(Document):
	def validate(self):
		"""Validate conversation data."""
		# Extract phone number from chat_id
		if not self.phone_number and "@c.us" in self.chat_id:
			self.phone_number = self.chat_id.replace("@c.us", "").replace("@g.us", "")

		# Determine if it's a group
		if "@g.us" in self.chat_id:
			self.is_group = 1

		# Ensure session is provided
		if not self.session:
			frappe.throw("Session is required")

	def on_update(self):
		"""Actions after update."""
		# Auto-link to contact if not a group
		if not self.is_group and not self.contact and self.chat_id:
			self.auto_link_to_contact()

		# Auto-link to lead if phone number matches
		if not self.linked_lead and self.phone_number:
			self.auto_link_to_lead()

		# Check mute expiration
		if self.is_muted and self.mute_expiration:
			if get_datetime(self.mute_expiration) < get_datetime(now()):
				self.is_muted = 0
				self.mute_expiration = None

	def auto_link_to_contact(self):
		"""Auto-link to WhatsApp Contact."""
		try:
			contact = frappe.db.get_value(
				"WhatsApp Contact",
				{"contact_id": self.chat_id, "session": self.session},
				"name"
			)

			if contact:
				self.contact = contact
				self.db_set("contact", contact, update_modified=False)

		except Exception as e:
			frappe.log_error(f"Error auto-linking conversation to contact: {str(e)}")

	def auto_link_to_lead(self):
		"""Auto-link to Lead if phone number matches."""
		try:
			lead = frappe.db.get_value(
				"CRM Lead",
				{"mobile_no": self.phone_number},
				["name", "lead_name"],
				as_dict=True
			)

			if lead:
				self.linked_lead = lead.name
				if not self.contact_name:
					self.contact_name = lead.lead_name
				self.db_set("linked_lead", lead.name, update_modified=False)

		except Exception as e:
			frappe.log_error(f"Error auto-linking conversation to lead: {str(e)}")

	@frappe.whitelist()
	def mark_as_read(self):
		"""Mark conversation as read."""
		try:
			from xappiens_whatsapp.api.conversations import mark_conversation_read

			result = mark_conversation_read(self.session, self.chat_id)

			if result.get("success"):
				self.unread_count = 0
				self.save()

				# Mark all messages as read
				frappe.db.sql("""
					UPDATE `tabWhatsApp Message`
					SET status = 'Read', read_at = %s
					WHERE conversation = %s AND direction = 'Incoming' AND status != 'Read'
				""", (now(), self.name))

				frappe.db.commit()

				return {"success": True, "message": "Marked as read"}

			return {"success": False, "message": "Failed to mark as read"}

		except Exception as e:
			frappe.log_error(f"Error marking conversation as read: {str(e)}")
			return {"success": False, "message": str(e)}

	@frappe.whitelist()
	def archive_conversation(self):
		"""Archive this conversation."""
		try:
			from xappiens_whatsapp.api.conversations import archive_chat

			result = archive_chat(self.session, self.chat_id)

			if result.get("success"):
				self.is_archived = 1
				self.status = "Archived"
				self.save()

				return {"success": True, "message": "Conversation archived"}

			return {"success": False, "message": "Failed to archive"}

		except Exception as e:
			frappe.log_error(f"Error archiving conversation: {str(e)}")
			return {"success": False, "message": str(e)}

	@frappe.whitelist()
	def unarchive_conversation(self):
		"""Unarchive this conversation."""
		try:
			from xappiens_whatsapp.api.conversations import unarchive_chat

			result = unarchive_chat(self.session, self.chat_id)

			if result.get("success"):
				self.is_archived = 0
				self.status = "Active"
				self.save()

				return {"success": True, "message": "Conversation unarchived"}

			return {"success": False, "message": "Failed to unarchive"}

		except Exception as e:
			frappe.log_error(f"Error unarchiving conversation: {str(e)}")
			return {"success": False, "message": str(e)}

	@frappe.whitelist()
	def pin_conversation(self):
		"""Pin this conversation."""
		try:
			from xappiens_whatsapp.api.conversations import pin_chat

			result = pin_chat(self.session, self.chat_id)

			if result.get("success"):
				self.is_pinned = 1
				self.save()

				return {"success": True, "message": "Conversation pinned"}

			return {"success": False, "message": "Failed to pin"}

		except Exception as e:
			frappe.log_error(f"Error pinning conversation: {str(e)}")
			return {"success": False, "message": str(e)}

	@frappe.whitelist()
	def unpin_conversation(self):
		"""Unpin this conversation."""
		try:
			from xappiens_whatsapp.api.conversations import unpin_chat

			result = unpin_chat(self.session, self.chat_id)

			if result.get("success"):
				self.is_pinned = 0
				self.save()

				return {"success": True, "message": "Conversation unpinned"}

			return {"success": False, "message": "Failed to unpin"}

		except Exception as e:
			frappe.log_error(f"Error unpinning conversation: {str(e)}")
			return {"success": False, "message": str(e)}

	@frappe.whitelist()
	def mute_conversation(self, until=None):
		"""Mute conversation notifications."""
		try:
			from xappiens_whatsapp.api.conversations import mute_chat

			result = mute_chat(self.session, self.chat_id, until)

			if result.get("success"):
				self.is_muted = 1
				self.mute_expiration = until
				self.save()

				return {"success": True, "message": "Conversation muted"}

			return {"success": False, "message": "Failed to mute"}

		except Exception as e:
			frappe.log_error(f"Error muting conversation: {str(e)}")
			return {"success": False, "message": str(e)}

	@frappe.whitelist()
	def unmute_conversation(self):
		"""Unmute conversation notifications."""
		try:
			from xappiens_whatsapp.api.conversations import unmute_chat

			result = unmute_chat(self.session, self.chat_id)

			if result.get("success"):
				self.is_muted = 0
				self.mute_expiration = None
				self.save()

				return {"success": True, "message": "Conversation unmuted"}

			return {"success": False, "message": "Failed to unmute"}

		except Exception as e:
			frappe.log_error(f"Error unmuting conversation: {str(e)}")
			return {"success": False, "message": str(e)}

	@frappe.whitelist()
	def sync_messages(self, limit=50):
		"""Sync messages from WhatsApp API."""
		try:
			from xappiens_whatsapp.api.messages import sync_conversation_messages

			result = sync_conversation_messages(self.session, self.chat_id, limit)

			# Update message count
			self.total_messages = frappe.db.count("WhatsApp Message", {"conversation": self.name})
			self.save()

			return result

		except Exception as e:
			frappe.log_error(f"Error syncing messages: {str(e)}")
			return {"success": False, "message": str(e)}

