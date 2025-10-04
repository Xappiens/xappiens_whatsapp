# Copyright (c) 2025, Xappiens and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now


class WhatsAppMessage(Document):
	def validate(self):
		"""Validate message data."""
		# Set from_me based on direction
		if self.direction == "Outgoing":
			self.from_me = 1
		else:
			self.from_me = 0

		# Set initial status if pending
		if self.direction == "Outgoing" and not self.sent_at:
			self.status = "Pending"
		elif self.direction == "Incoming":
			self.status = "Delivered"

	def after_insert(self):
		"""Actions after insert."""
		# Update conversation with last message
		self.update_conversation()

	def on_update(self):
		"""Actions after update."""
		# Update conversation when message changes
		if self.has_value_changed("content") or self.has_value_changed("timestamp"):
			self.update_conversation()

		# Set status timestamps
		if self.has_value_changed("status"):
			if self.status == "Sent" and not self.sent_at:
				self.sent_at = now()
			elif self.status == "Delivered" and not self.delivered_at:
				self.delivered_at = now()
			elif self.status == "Read" and not self.read_at:
				self.read_at = now()

	def update_conversation(self):
		"""Update parent conversation with last message info."""
		try:
			conversation = frappe.get_doc("WhatsApp Conversation", self.conversation)

			# Get the latest message for this conversation
			latest_message = frappe.db.sql("""
				SELECT content, timestamp, direction
				FROM `tabWhatsApp Message`
				WHERE conversation = %s
				ORDER BY timestamp DESC
				LIMIT 1
			""", self.conversation, as_dict=True)

			if latest_message:
				msg = latest_message[0]
				conversation.last_message = msg.content
				conversation.last_message_time = msg.timestamp
				conversation.last_message_from_me = 1 if msg.direction == "Outgoing" else 0

			# Update unread count for incoming messages
			if self.direction == "Incoming" and self.status != "Read":
				conversation.unread_count = frappe.db.count("WhatsApp Message", {
					"conversation": self.conversation,
					"direction": "Incoming",
					"status": ["!=", "Read"]
				})

			# Update total messages
			conversation.total_messages = frappe.db.count("WhatsApp Message", {
				"conversation": self.conversation
			})

			conversation.flags.ignore_version = True
			conversation.save(ignore_permissions=True)

		except Exception as e:
			frappe.log_error(f"Error updating conversation from message: {str(e)}")

	@frappe.whitelist()
	def mark_as_read(self):
		"""Mark message as read."""
		if self.direction == "Incoming":
			self.status = "Read"
			self.read_at = now()
			self.save()

			# Update conversation unread count
			self.update_conversation()

			return {"success": True, "message": "Message marked as read"}

		return {"success": False, "message": "Only incoming messages can be marked as read"}

	@frappe.whitelist()
	def delete_message(self, for_everyone=False):
		"""Delete message."""
		try:
			from xappiens_whatsapp.api.messages import delete_message_api

			result = delete_message_api(self.session, self.message_id, for_everyone)

			if result.get("success"):
				self.status = "Deleted"
				self.save()

				return {"success": True, "message": "Message deleted"}

			return {"success": False, "message": "Failed to delete message"}

		except Exception as e:
			frappe.log_error(f"Error deleting message: {str(e)}")
			return {"success": False, "message": str(e)}

	@frappe.whitelist()
	def star_message(self):
		"""Star/favorite this message."""
		try:
			from xappiens_whatsapp.api.messages import star_message_api

			result = star_message_api(self.session, self.message_id)

			if result.get("success"):
				self.is_starred = 1
				self.save()

				return {"success": True, "message": "Message starred"}

			return {"success": False, "message": "Failed to star message"}

		except Exception as e:
			frappe.log_error(f"Error starring message: {str(e)}")
			return {"success": False, "message": str(e)}

	@frappe.whitelist()
	def unstar_message(self):
		"""Unstar this message."""
		try:
			from xappiens_whatsapp.api.messages import unstar_message_api

			result = unstar_message_api(self.session, self.message_id)

			if result.get("success"):
				self.is_starred = 0
				self.save()

				return {"success": True, "message": "Message unstarred"}

			return {"success": False, "message": "Failed to unstar message"}

		except Exception as e:
			frappe.log_error(f"Error unstarring message: {str(e)}")
			return {"success": False, "message": str(e)}

	@frappe.whitelist()
	def react_to_message(self, reaction):
		"""React to this message with an emoji."""
		try:
			from xappiens_whatsapp.api.messages import react_to_message_api

			result = react_to_message_api(self.session, self.message_id, reaction)

			if result.get("success"):
				self.has_reaction = 1
				self.reaction = reaction
				self.reacted_at = now()
				self.save()

				return {"success": True, "message": "Reaction added"}

			return {"success": False, "message": "Failed to add reaction"}

		except Exception as e:
			frappe.log_error(f"Error reacting to message: {str(e)}")
			return {"success": False, "message": str(e)}

	@frappe.whitelist()
	def forward_message(self, to_chat_id):
		"""Forward this message to another chat."""
		try:
			from xappiens_whatsapp.api.messages import forward_message_api

			result = forward_message_api(self.session, self.message_id, to_chat_id)

			return result

		except Exception as e:
			frappe.log_error(f"Error forwarding message: {str(e)}")
			return {"success": False, "message": str(e)}

	@frappe.whitelist()
	def download_media(self):
		"""Download media from this message."""
		try:
			if not self.has_media:
				return {"success": False, "message": "Message has no media"}

			from xappiens_whatsapp.api.messages import download_media_api

			result = download_media_api(self.session, self.message_id)

			return result

		except Exception as e:
			frappe.log_error(f"Error downloading media: {str(e)}")
			return {"success": False, "message": str(e)}

