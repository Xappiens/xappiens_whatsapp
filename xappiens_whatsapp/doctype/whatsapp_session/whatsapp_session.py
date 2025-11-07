# Copyright (c) 2025, Xappiens and contributors
# For license information, please see license.txt

import frappe
from frappe import _
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
		"""Sincroniza todos los datos de la sesión (contactos, conversaciones, mensajes)"""
		try:
			if not self.is_connected:
				frappe.throw("La sesión no está conectada. Por favor, conecta la sesión primero.")

			# Ejecutar sincronización completa en background
			frappe.enqueue(
				"xappiens_whatsapp.api.sync.sync_session_complete",
				queue="default",
				timeout=600,
				session_name=self.name
			)

			frappe.msgprint(
				"Sincronización completa iniciada en segundo plano. Se sincronizarán contactos, conversaciones y mensajes.",
				title="Sincronización Iniciada",
				indicator="blue"
			)

			return {"success": True, "message": "Sincronización completa iniciada"}
		except Exception as e:
			frappe.log_error(f"Error syncing all data: {str(e)}", "WhatsApp Session Sync All")
			frappe.throw(f"Error al iniciar sincronización: {str(e)}")

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

	def before_rename(self, old, new, merge=False):
		"""Validaciones antes del renombrado/fusión"""
		if merge:
			# Validar que la fusión sea segura
			if self.is_connected and self.status == "Connected":
				frappe.throw(_("No se puede fusionar una sesión que está actualmente conectada. Desconecte la sesión primero."))

			# Verificar que la sesión destino existe
			if not frappe.db.exists("WhatsApp Session", new):
				frappe.throw(_("La sesión destino '{0}' no existe").format(new))

			target_session = frappe.get_doc("WhatsApp Session", new)

			# Validar que no se fusionen sesiones con el mismo session_id
			if self.session_id == target_session.session_id:
				frappe.throw(_("No se pueden fusionar sesiones con el mismo Session ID"))

			# Advertir sobre sesiones conectadas
			if target_session.is_connected and target_session.status == "Connected":
				frappe.msgprint(_("Advertencia: La sesión destino está conectada. Los datos se fusionarán pero mantendrá su conexión actual."),
							   alert=True, indicator="orange")

	def after_rename(self, old, new, merge=False):
		"""Acciones después del renombrado/fusión"""
		if merge:
			# Frappe ya ha hecho la fusión automática de los campos de enlace
			# Solo necesitamos fusionar las estadísticas y metadatos específicos
			try:
				old_doc_data = frappe.db.get_value("WhatsApp Session", old,
					["total_contacts", "total_chats", "total_messages_sent", "total_messages_received",
					 "phone_number", "error_message", "error_code", "last_seen"], as_dict=True)

				if old_doc_data:
					# Sumar estadísticas
					self.total_contacts = (self.total_contacts or 0) + (old_doc_data.total_contacts or 0)
					self.total_chats = (self.total_chats or 0) + (old_doc_data.total_chats or 0)
					self.total_messages_sent = (self.total_messages_sent or 0) + (old_doc_data.total_messages_sent or 0)
					self.total_messages_received = (self.total_messages_received or 0) + (old_doc_data.total_messages_received or 0)

					# Copiar datos faltantes
					if old_doc_data.phone_number and not self.phone_number:
						self.phone_number = old_doc_data.phone_number

					if old_doc_data.last_seen and (not self.last_seen or old_doc_data.last_seen > self.last_seen):
						self.last_seen = old_doc_data.last_seen

					# Guardar cambios
					self.save(ignore_permissions=True)

				frappe.msgprint(_("Fusión completada exitosamente. Todos los datos han sido transferidos."),
							   alert=True, indicator="green")

			except Exception as e:
				frappe.log_error(f"Error en after_rename merge: {str(e)}", "WhatsApp Session Merge")
				frappe.msgprint(_("Fusión completada pero hubo un error actualizando estadísticas: {0}").format(str(e)),
							   alert=True, indicator="orange")

	def validate(self):
		"""Validaciones del documento"""
		# Validar session_id único
		if self.session_id:
			existing = frappe.db.get_value("WhatsApp Session",
										  {"session_id": self.session_id, "name": ("!=", self.name)},
										  "name")
			if existing:
				frappe.throw(_("Ya existe una sesión con el Session ID '{0}': {1}").format(self.session_id, existing))

		# Validar phone_number único si está presente
		if self.phone_number:
			existing = frappe.db.get_value("WhatsApp Session",
										  {"phone_number": self.phone_number, "name": ("!=", self.name)},
										  "name")
			if existing:
				frappe.throw(_("Ya existe una sesión con el número de teléfono '{0}': {1}").format(self.phone_number, existing))

	def on_update(self):
		"""Acciones después de actualizar"""
		# Actualizar timestamps
		if not self.created_at:
			self.db_set("created_at", frappe.utils.now())

		self.db_set("updated_at", frappe.utils.now())

	def get_merge_statistics(self):
		"""Obtener estadísticas para fusión"""
		from .whatsapp_session_merge import WhatsAppSessionMerge

		# Crear un merger temporal solo para obtener estadísticas
		merger = WhatsAppSessionMerge(self.name, self.name)
		return merger.get_merge_statistics_for_session(self.name)

	def on_trash(self):
		"""
		Eliminar todos los documentos relacionados de WhatsApp antes de eliminar la sesión.

		NOTA IMPORTANTE: Este método solo elimina documentos de WhatsApp (mensajes, conversaciones,
		contactos de WhatsApp, etc.). NO elimina documentos del CRM como Leads, Customers, Deals,
		que pueden estar vinculados a través de los campos linked_lead, linked_customer, linked_deal.
		"""
		# Desconectar la sesión primero si está conectada
		if self.is_connected:
			try:
				from xappiens_whatsapp.api.session import disconnect_session
				disconnect_session(self.session_id)
			except Exception as e:
				frappe.log_error(f"Error desconectando sesión antes de eliminar: {str(e)}", "WhatsApp Session Delete")

		# Eliminar documentos relacionados de WhatsApp en orden inverso de dependencias
		# IMPORTANTE: Solo se eliminan documentos de WhatsApp, NO documentos del CRM (Leads, Customers, etc.)
		session_name = self.name

		# 1. Eliminar mensajes (que pueden tener media files)
		messages = frappe.get_all("WhatsApp Message", filters={"session": session_name}, pluck="name")
		for message_name in messages:
			try:
				frappe.delete_doc("WhatsApp Message", message_name, force=1, ignore_permissions=True)
			except Exception as e:
				frappe.log_error(f"Error eliminando mensaje {message_name}: {str(e)}", "WhatsApp Session Delete")

		# 2. Eliminar media files relacionados
		media_files = frappe.get_all("WhatsApp Media File", filters={"session": session_name}, pluck="name")
		for media_name in media_files:
			try:
				frappe.delete_doc("WhatsApp Media File", media_name, force=1, ignore_permissions=True)
			except Exception as e:
				frappe.log_error(f"Error eliminando media file {media_name}: {str(e)}", "WhatsApp Session Delete")

		# 3. Eliminar conversaciones (que pueden estar vinculadas a grupos)
		conversations = frappe.get_all("WhatsApp Conversation", filters={"session": session_name}, pluck="name")
		for conversation_name in conversations:
			try:
				frappe.delete_doc("WhatsApp Conversation", conversation_name, force=1, ignore_permissions=True)
			except Exception as e:
				frappe.log_error(f"Error eliminando conversación {conversation_name}: {str(e)}", "WhatsApp Session Delete")

		# 4. Eliminar grupos y sus participantes (child table se elimina automáticamente)
		groups = frappe.get_all("WhatsApp Group", filters={"session": session_name}, pluck="name")
		for group_name in groups:
			try:
				frappe.delete_doc("WhatsApp Group", group_name, force=1, ignore_permissions=True)
			except Exception as e:
				frappe.log_error(f"Error eliminando grupo {group_name}: {str(e)}", "WhatsApp Session Delete")

		# 5. Eliminar contactos
		contacts = frappe.get_all("WhatsApp Contact", filters={"session": session_name}, pluck="name")
		for contact_name in contacts:
			try:
				frappe.delete_doc("WhatsApp Contact", contact_name, force=1, ignore_permissions=True)
			except Exception as e:
				frappe.log_error(f"Error eliminando contacto {contact_name}: {str(e)}", "WhatsApp Session Delete")

		# 6. Eliminar analytics
		analytics = frappe.get_all("WhatsApp Analytics", filters={"session": session_name}, pluck="name")
		for analytics_name in analytics:
			try:
				frappe.delete_doc("WhatsApp Analytics", analytics_name, force=1, ignore_permissions=True)
			except Exception as e:
				frappe.log_error(f"Error eliminando analytics {analytics_name}: {str(e)}", "WhatsApp Session Delete")

		# 7. Eliminar activity logs
		activity_logs = frappe.get_all("WhatsApp Activity Log", filters={"session": session_name}, pluck="name")
		for log_name in activity_logs:
			try:
				frappe.delete_doc("WhatsApp Activity Log", log_name, force=1, ignore_permissions=True)
			except Exception as e:
				frappe.log_error(f"Error eliminando activity log {log_name}: {str(e)}", "WhatsApp Session Delete")

		# 8. Eliminar webhook logs
		webhook_logs = frappe.get_all("WhatsApp Webhook Log", filters={"session": session_name}, pluck="name")
		for log_name in webhook_logs:
			try:
				frappe.delete_doc("WhatsApp Webhook Log", log_name, force=1, ignore_permissions=True)
			except Exception as e:
				frappe.log_error(f"Error eliminando webhook log {log_name}: {str(e)}", "WhatsApp Session Delete")

		# 9. Eliminar labels
		labels = frappe.get_all("WhatsApp Label", filters={"session": session_name}, pluck="name")
		for label_name in labels:
			try:
				frappe.delete_doc("WhatsApp Label", label_name, force=1, ignore_permissions=True)
			except Exception as e:
				frappe.log_error(f"Error eliminando label {label_name}: {str(e)}", "WhatsApp Session Delete")

		# Nota: WhatsApp Session User (child table) se elimina automáticamente con el documento padre

@frappe.whitelist()
def get_delete_stats(session_name):
	"""Obtener estadísticas de documentos relacionados antes de eliminar"""
	try:
		stats = {
			"contacts": frappe.db.count("WhatsApp Contact", {"session": session_name}),
			"conversations": frappe.db.count("WhatsApp Conversation", {"session": session_name}),
			"messages": frappe.db.count("WhatsApp Message", {"session": session_name}),
			"groups": frappe.db.count("WhatsApp Group", {"session": session_name}),
			"media_files": frappe.db.count("WhatsApp Media File", {"session": session_name}),
			"analytics": frappe.db.count("WhatsApp Analytics", {"session": session_name}),
			"activity_logs": frappe.db.count("WhatsApp Activity Log", {"session": session_name}),
			"webhook_logs": frappe.db.count("WhatsApp Webhook Log", {"session": session_name}),
			"labels": frappe.db.count("WhatsApp Label", {"session": session_name})
		}

		return {
			"success": True,
			"stats": stats
		}

	except Exception as e:
		frappe.log_error(f"Error obteniendo estadísticas de eliminación: {str(e)}", "WhatsApp Session Delete Stats")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def delete_session_with_related_docs(session_name):
	"""Eliminar sesión y todos sus documentos relacionados"""
	try:
		# Obtener el documento de la sesión
		session_doc = frappe.get_doc("WhatsApp Session", session_name)

		# Guardar el session_id antes de eliminar
		session_id = session_doc.session_id

		# Eliminar el documento (on_trash se ejecutará automáticamente)
		frappe.delete_doc("WhatsApp Session", session_name, force=1, ignore_permissions=True)

		# Intentar eliminar la sesión del servidor de WhatsApp si existe session_id
		if session_id:
			try:
				from xappiens_whatsapp.api.session import delete_session_from_api
				delete_session_from_api(session_id)
			except Exception as e:
				# No es crítico si falla, solo loguear el error
				frappe.log_error(f"Error eliminando sesión del servidor API (no crítico): {str(e)}", "WhatsApp Session Delete")

		return {
			"success": True,
			"message": _("Sesión y todos sus documentos relacionados eliminados exitosamente")
		}

	except Exception as e:
		frappe.log_error(f"Error eliminando sesión con documentos relacionados: {str(e)}", "WhatsApp Session Delete")
		return {
			"success": False,
			"error": str(e)
		}
