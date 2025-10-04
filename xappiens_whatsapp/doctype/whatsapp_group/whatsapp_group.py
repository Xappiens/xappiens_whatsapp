# Copyright (c) 2025, Xappiens and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now


class WhatsAppGroup(Document):
	def validate(self):
		"""Validate group data."""
		# Update counts
		self.participant_count = len(self.participants) if self.participants else 0
		self.admin_count = len([p for p in self.participants if p.is_admin]) if self.participants else 0

		# Generate invite URL
		if self.invite_code and not self.invite_url:
			self.invite_url = f"https://chat.whatsapp.com/{self.invite_code}"

	@frappe.whitelist()
	def get_invite_code(self):
		"""Get group invite code from API."""
		try:
			from xappiens_whatsapp.api.groups import get_group_invite_code_api

			result = get_group_invite_code_api(self.session, self.group_id)

			if result.get("success"):
				self.invite_code = result.get("inviteCode")
				self.invite_url = f"https://chat.whatsapp.com/{self.invite_code}"
				self.save()

				return {"success": True, "invite_code": self.invite_code, "invite_url": self.invite_url}

			return {"success": False, "message": "Failed to get invite code"}

		except Exception as e:
			frappe.log_error(f"Error getting invite code: {str(e)}")
			return {"success": False, "message": str(e)}

	@frappe.whitelist()
	def revoke_invite_code(self):
		"""Revoke current invite code."""
		try:
			from xappiens_whatsapp.api.groups import revoke_invite_code_api

			result = revoke_invite_code_api(self.session, self.group_id)

			if result.get("success"):
				self.invite_code_revoked_at = now()
				self.invite_code = None
				self.invite_url = None
				self.save()

				return {"success": True, "message": "Invite code revoked"}

			return {"success": False, "message": "Failed to revoke invite code"}

		except Exception as e:
			frappe.log_error(f"Error revoking invite code: {str(e)}")
			return {"success": False, "message": str(e)}

	@frappe.whitelist()
	def add_participants(self, participant_numbers):
		"""Add participants to group."""
		try:
			from xappiens_whatsapp.api.groups import add_participants_api
			import json

			if isinstance(participant_numbers, str):
				participant_numbers = json.loads(participant_numbers)

			result = add_participants_api(self.session, self.group_id, participant_numbers)

			if result.get("success"):
				# Reload participants
				self.sync_participants()

				return {"success": True, "message": f"Added {len(participant_numbers)} participants"}

			return {"success": False, "message": "Failed to add participants"}

		except Exception as e:
			frappe.log_error(f"Error adding participants: {str(e)}")
			return {"success": False, "message": str(e)}

	@frappe.whitelist()
	def sync_participants(self):
		"""Sync participants from WhatsApp API."""
		try:
			from xappiens_whatsapp.api.groups import get_group_participants

			result = get_group_participants(self.session, self.group_id)

			if result.get("success"):
				# Clear existing participants
				self.participants = []

				# Add participants from API
				participants_data = result.get("participants", [])
				for p in participants_data:
					self.append("participants", {
						"contact": p.get("id"),
						"contact_name": p.get("name", ""),
						"is_admin": p.get("isAdmin", False),
						"is_super_admin": p.get("isSuperAdmin", False)
					})

				self.save()

				return {"success": True, "message": f"Synced {len(participants_data)} participants"}

			return {"success": False, "message": "Failed to sync participants"}

		except Exception as e:
			frappe.log_error(f"Error syncing participants: {str(e)}")
			return {"success": False, "message": str(e)}

