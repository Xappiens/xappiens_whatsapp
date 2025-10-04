# Copyright (c) 2025, Xappiens and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now


class WhatsAppMediaFile(Document):
	def validate(self):
		"""Extract file extension and set metadata."""
		if self.filename and not self.file_extension:
			self.file_extension = self.filename.split('.')[-1] if '.' in self.filename else ''

	@frappe.whitelist()
	def download_from_api(self):
		"""Download media file from WhatsApp API."""
		try:
			from xappiens_whatsapp.api.media import download_media_from_message

			result = download_media_from_message(self.session, self.message)

			if result.get("success"):
				self.file = result.get("file_path")
				self.is_downloaded = 1
				self.downloaded_at = now()
				self.status = "Downloaded"
				self.save()

				return {"success": True, "message": "Media downloaded successfully"}
			else:
				self.status = "Failed"
				self.download_error = result.get("message")
				self.retry_count = (self.retry_count or 0) + 1
				self.save()

				return {"success": False, "message": self.download_error}

		except Exception as e:
			frappe.log_error(f"Error downloading media: {str(e)}")
			self.status = "Failed"
			self.download_error = str(e)
			self.retry_count = (self.retry_count or 0) + 1
			self.save()

			return {"success": False, "message": str(e)}

