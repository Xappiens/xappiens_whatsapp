# Copyright (c) 2025, Xappiens and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class WhatsAppAnalytics(Document):
	def before_save(self):
		"""Calculate derived fields."""
		# Total messages
		self.total_messages = (self.total_messages_sent or 0) + (self.total_messages_received or 0)

		# Messages per conversation
		if self.total_conversations and self.total_conversations > 0:
			self.messages_per_conversation = self.total_messages / self.total_conversations

		# Webhook success rate
		if self.total_webhooks_received and self.total_webhooks_received > 0:
			self.webhook_success_rate = ((self.webhooks_processed or 0) / self.total_webhooks_received) * 100

