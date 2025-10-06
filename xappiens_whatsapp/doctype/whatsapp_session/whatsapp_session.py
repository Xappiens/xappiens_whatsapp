# Copyright (c) 2025, Xappiens and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from xappiens_whatsapp.api import session, contacts, conversations, messages, sync


class WhatsAppSession(Document):
	@frappe.whitelist()
	def test_method(self):
		"""Método de prueba"""
		return {"success": True, "message": "Método de prueba funciona"}

	@frappe.whitelist()
	def check_status(self):
		"""Verifica el estado de la sesión de WhatsApp"""
		try:
			result = session.get_session_status(self.session_id)

			# Actualizar campos del documento si hay información
			if result.get("success") and result.get("data"):
				data = result.get("data", {})
				if data.get("state"):
					self.status = self._map_status(data.get("state"))
				if data.get("phone"):
					self.phone_number = data.get("phone")
				self.is_connected = data.get("state") == "CONNECTED"
				self.save()

			return result
		except Exception as e:
			frappe.log_error(f"Error checking status: {str(e)}", "WhatsApp Session Check Status")
			return {"success": False, "error": str(e)}

	@frappe.whitelist()
	def connect_session(self):
		"""Conecta la sesión de WhatsApp"""
		try:
			result = session.start_session(self.session_id)

			# Actualizar estado
			if result.get("success"):
				self.status = "Connecting"
				self.save()

			return result
		except Exception as e:
			frappe.log_error(f"Error connecting session: {str(e)}", "WhatsApp Session Connect")
			return {"success": False, "error": str(e)}

	@frappe.whitelist()
	def disconnect_session(self):
		"""Desconecta la sesión de WhatsApp"""
		try:
			result = session.disconnect_session(self.session_id)

			# Actualizar estado
			if result.get("success"):
				self.status = "Disconnected"
				self.is_connected = 0
				self.save()

			return result
		except Exception as e:
			frappe.log_error(f"Error disconnecting session: {str(e)}", "WhatsApp Session Disconnect")
			return {"success": False, "error": str(e)}

	@frappe.whitelist()
	def get_qr_code(self):
		"""Obtiene el código QR de la sesión"""
		try:
			result = session.get_qr_code(self.session_id)

			# Actualizar QR code en el documento
			if result.get("success") and result.get("qr_code"):
				self.qr_code = result.get("qr_code")
				self.qr_image = result.get("qr_code_image")
				self.status = "QR Code Required"
				self.save()

			return result
		except Exception as e:
			frappe.log_error(f"Error getting QR code: {str(e)}", "WhatsApp Session QR Code")
			return {"success": False, "error": str(e)}

	@frappe.whitelist()
	def sync_all_data(self):
		"""Sincroniza todos los datos de la sesión"""
		try:
			result = sync.sync_session_data(self.session_id)

			# Actualizar estadísticas
			if result.get("success"):
				self._update_statistics()

			return result
		except Exception as e:
			frappe.log_error(f"Error syncing all data: {str(e)}", "WhatsApp Session Sync All")
			return {"success": False, "error": str(e)}

	@frappe.whitelist()
	def sync_contacts(self):
		"""Sincroniza los contactos de la sesión"""
		try:
			result = contacts.sync_contacts(self.session_id)
			return result
		except Exception as e:
			frappe.log_error(f"Error syncing contacts: {str(e)}", "WhatsApp Session Sync Contacts")
			return {"success": False, "error": str(e)}

	@frappe.whitelist()
	def sync_conversations(self):
		"""Sincroniza las conversaciones de la sesión"""
		try:
			result = conversations.sync_conversations(self.session_id)
			return result
		except Exception as e:
			frappe.log_error(f"Error syncing conversations: {str(e)}", "WhatsApp Session Sync Conversations")
			return {"success": False, "error": str(e)}

	@frappe.whitelist()
	def sync_messages(self):
		"""Sincroniza los mensajes de todas las conversaciones de la sesión"""
		try:
			# Obtener todas las conversaciones de la sesión
			conversations = frappe.get_all(
				"WhatsApp Conversation",
				filters={"session": self.name, "status": "Active"},
				limit=20  # Limitar a las 20 conversaciones más recientes
			)

			if not conversations:
				return {
					"success": True,
					"message": "No hay conversaciones activas para sincronizar",
					"conversations_synced": 0,
					"total_messages": 0
				}

			results = []
			total_messages = 0

			for conv in conversations:
				try:
					msg_result = messages.sync_messages(conv.name, limit=20)
					results.append(msg_result)
					if msg_result.get("success"):
						total_messages += msg_result.get("created", 0) + msg_result.get("updated", 0)
				except Exception as e:
					frappe.log_error(f"Error syncing messages for conversation {conv.name}: {str(e)}")
					continue

			return {
				"success": True,
				"conversations_synced": len(results),
				"total_messages": total_messages,
				"results": results
			}
		except Exception as e:
			frappe.log_error(f"Error syncing messages: {str(e)}", "WhatsApp Session Sync Messages")
			return {"success": False, "error": str(e)}

	@frappe.whitelist()
	def sync_groups(self):
		"""Sincroniza los grupos de la sesión"""
		try:
			# Por ahora retornar un placeholder ya que no tenemos la función de grupos en el API
			# TODO: Implementar sync de grupos cuando esté disponible en el API
			return {
				"success": True,
				"message": "Sync de grupos no implementado aún",
				"data": {}
			}
		except Exception as e:
			frappe.log_error(f"Error syncing groups: {str(e)}", "WhatsApp Session Sync Groups")
			return {"success": False, "error": str(e)}

	def _update_statistics(self):
		"""Actualiza las estadísticas de la sesión"""
		self.total_contacts = frappe.db.count("WhatsApp Contact", {"session": self.name})
		self.total_chats = frappe.db.count("WhatsApp Conversation", {"session": self.name})
		self.total_messages_sent = frappe.db.count("WhatsApp Message", {
			"session": self.name,
			"direction": "Outgoing"
		})
		self.total_messages_received = frappe.db.count("WhatsApp Message", {
			"session": self.name,
			"direction": "Incoming"
		})
		self.save()

	def _map_status(self, api_status):
		"""Mapea el estado de la API al estado del DocType"""
		status_map = {
			"CONNECTED": "Connected",
			"DISCONNECTED": "Disconnected",
			"CONNECTING": "Connecting",
			"QR": "QR Code Required",
			"ERROR": "Error"
		}
		return status_map.get(api_status, "Disconnected")
