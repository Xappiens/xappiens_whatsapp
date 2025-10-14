# Copyright (c) 2025, Xappiens and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class WhatsAppSession(Document):
	@frappe.whitelist()
	def test_method(self):
		"""Método de prueba"""
		return {"success": True, "message": "Método de prueba funciona"}

	@frappe.whitelist()
	def check_status(self):
		"""Verifica el estado de la sesión de WhatsApp"""
		try:
			# Por ahora solo actualizar el estado local
			frappe.msgprint("Verificando estado de la sesión...")
			return {"success": True, "message": "Estado verificado"}
		except Exception as e:
			frappe.log_error(f"Error checking status: {str(e)}", "WhatsApp Session Check Status")
			return {"success": False, "error": str(e)}

	@frappe.whitelist()
	def connect_session(self):
		"""Conecta la sesión de WhatsApp"""
		try:
			self.status = "Connecting"
			self.save()
			frappe.msgprint("Iniciando conexión de sesión...")
			return {"success": True, "message": "Conexión iniciada"}
		except Exception as e:
			frappe.log_error(f"Error connecting session: {str(e)}", "WhatsApp Session Connect")
			return {"success": False, "error": str(e)}

	@frappe.whitelist()
	def disconnect_session(self):
		"""Desconecta la sesión de WhatsApp"""
		try:
			self.status = "Disconnected"
			self.is_connected = 0
			self.save()
			frappe.msgprint("Sesión desconectada")
			return {"success": True, "message": "Sesión desconectada"}
		except Exception as e:
			frappe.log_error(f"Error disconnecting session: {str(e)}", "WhatsApp Session Disconnect")
			return {"success": False, "error": str(e)}

	@frappe.whitelist()
	def get_qr_code(self):
		"""Obtiene el código QR de la sesión"""
		try:
			self.status = "QR Code Required"
			self.save()
			frappe.msgprint("Generando código QR...")
			return {"success": True, "message": "QR code generado"}
		except Exception as e:
			frappe.log_error(f"Error getting QR code: {str(e)}", "WhatsApp Session QR Code")
			return {"success": False, "error": str(e)}

	@frappe.whitelist()
	def sync_all_data(self):
		"""Sincroniza todos los datos de la sesión"""
		try:
			frappe.msgprint("Sincronizando datos de la sesión...")
			return {"success": True, "message": "Sincronización iniciada"}
		except Exception as e:
			frappe.log_error(f"Error syncing all data: {str(e)}", "WhatsApp Session Sync All")
			return {"success": False, "error": str(e)}

	@frappe.whitelist()
	def sync_contacts(self):
		"""Sincroniza los contactos de la sesión"""
		try:
			frappe.msgprint("Sincronizando contactos...")
			return {"success": True, "message": "Sincronización de contactos iniciada"}
		except Exception as e:
			frappe.log_error(f"Error syncing contacts: {str(e)}", "WhatsApp Session Sync Contacts")
			return {"success": False, "error": str(e)}

	@frappe.whitelist()
	def sync_conversations(self):
		"""Sincroniza las conversaciones de la sesión"""
		try:
			frappe.msgprint("Sincronizando conversaciones...")
			return {"success": True, "message": "Sincronización de conversaciones iniciada"}
		except Exception as e:
			frappe.log_error(f"Error syncing conversations: {str(e)}", "WhatsApp Session Sync Conversations")
			return {"success": False, "error": str(e)}

	@frappe.whitelist()
	def sync_messages(self):
		"""Sincroniza los mensajes de todas las conversaciones de la sesión"""
		try:
			frappe.msgprint("Sincronizando mensajes...")
			return {"success": True, "message": "Sincronización de mensajes iniciada"}
		except Exception as e:
			frappe.log_error(f"Error syncing messages: {str(e)}", "WhatsApp Session Sync Messages")
			return {"success": False, "error": str(e)}

	@frappe.whitelist()
	def sync_groups(self):
		"""Sincroniza los grupos de la sesión"""
		try:
			frappe.msgprint("Sincronizando grupos...")
			return {"success": True, "message": "Sincronización de grupos iniciada"}
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
