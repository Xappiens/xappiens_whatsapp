# Copyright (c) 2025, Xappiens and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_url


class WhatsAppSettings(Document):
	def before_save(self):
		"""Generar automáticamente la URL del webhook"""
		if not self.webhook_url:
			self.webhook_url = self.get_webhook_url()

	def get_webhook_url(self):
		"""Obtener la URL completa del webhook"""
		base_url = get_url()
		webhook_endpoint = "/api/method/xappiens_whatsapp.api.webhook.handle_webhook"
		return f"{base_url}{webhook_endpoint}"

	def validate(self):
		"""Validaciones del documento"""
		# Asegurar que la URL del webhook esté actualizada
		expected_url = self.get_webhook_url()
		if self.webhook_url != expected_url:
			self.webhook_url = expected_url

