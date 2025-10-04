# Copyright (c) 2025, Xappiens and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now


class WhatsAppAIAgent(Document):
	@frappe.whitelist()
	def process_message(self, session_id, chat_id, message, context=None):
		"""Process a message with this AI agent."""
		try:
			from xappiens_whatsapp.api.ai import process_message_with_agent

			result = process_message_with_agent(
				agent_id=self.agent_id or self.name,
				session_id=session_id,
				chat_id=chat_id,
				message=message,
				context=context or {}
			)

			if result.get("success"):
				# Log conversation
				self.append("conversation_logs", {
					"session_id": session_id,
					"chat_id": chat_id,
					"user_message": message,
					"ai_response": result.get("response"),
					"tokens_used": result.get("tokens_used", 0),
					"response_time": result.get("response_time", 0),
					"success": True
				})

				# Update statistics
				self.total_messages_processed = (self.total_messages_processed or 0) + 1
				self.total_tokens_used = (self.total_tokens_used or 0) + result.get("tokens_used", 0)
				self.last_used = now()

				self.save()

				return result
			else:
				# Log error
				self.append("conversation_logs", {
					"session_id": session_id,
					"chat_id": chat_id,
					"user_message": message,
					"error_message": result.get("message"),
					"success": False
				})

				self.save()

				return result

		except Exception as e:
			frappe.log_error(f"Error processing message with AI agent: {str(e)}")
			return {"success": False, "message": str(e)}

	@frappe.whitelist()
	def update_statistics(self):
		"""Update agent statistics."""
		try:
			# Calculate success rate
			if self.conversation_logs:
				successful = len([log for log in self.conversation_logs if log.success])
				total = len(self.conversation_logs)
				self.success_rate = (successful / total * 100) if total > 0 else 0

			# Calculate average response time
			if self.conversation_logs:
				total_time = sum([log.response_time for log in self.conversation_logs if log.response_time])
				count = len([log for log in self.conversation_logs if log.response_time])
				self.avg_response_time = (total_time / count) if count > 0 else 0

			self.save()

			return {"success": True}

		except Exception as e:
			frappe.log_error(f"Error updating AI agent statistics: {str(e)}")
			return {"success": False, "message": str(e)}

