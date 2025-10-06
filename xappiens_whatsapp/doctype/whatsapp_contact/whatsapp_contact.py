# Copyright (c) 2025, Xappiens and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now


class WhatsAppContact(Document):
	def before_insert(self):
		"""Set first_seen before insert."""
		if not self.first_seen:
			self.first_seen = now()
		self.last_sync = now()
		self.sync_count = 1

	def before_save(self):
		"""Update last_sync before save."""
		if self.has_value_changed("name1") or self.has_value_changed("pushname"):
			self.last_sync = now()
			self.sync_count = (self.sync_count or 0) + 1

	def validate(self):
		"""Validate contact data."""
		# Ensure contact_id is properly formatted
		if not self.contact_id:
			frappe.throw("Contact ID is required")

		# Ensure phone_number is extracted from contact_id if not provided
		if not self.phone_number and "@c.us" in self.contact_id:
			self.phone_number = self.contact_id.replace("@c.us", "")

		# Ensure session is provided
		if not self.session:
			frappe.throw("Session is required")

		# Ensure contact_name doesn't exceed 140 characters if provided
		if self.contact_name and len(self.contact_name) > 140:
			self.contact_name = self.contact_name[:140]

	def on_update(self):
		"""Actions after update."""
		# Auto-linking deshabilitado - no necesario para la funcionalidad
		pass

	def auto_link_to_lead(self):
		"""Automatically link to Lead if phone number matches."""
		try:
			# Search for Lead with matching phone
			lead = frappe.db.get_value(
				"CRM Lead",
				{"mobile_no": self.phone_number},
				["name", "lead_name"],
				as_dict=True
			)

			if lead:
				self.linked_lead = lead.name
				if not self.contact_name:
					self.contact_name = (lead.lead_name or "")[:140]
				self.db_set("linked_lead", lead.name, update_modified=False)

				frappe.msgprint(f"Contacto vinculado automáticamente con Lead: {lead.name}")

		except Exception as e:
			frappe.log_error(f"Error auto-linking contact to lead: {str(e)}")

	def auto_link_to_customer(self):
		"""Automatically link to Customer if phone number matches."""
		try:
			# Search for Customer with matching phone
			customer = frappe.db.get_value(
				"CRM Organization",
				{"mobile_no": self.phone_number},
				["name", "organization_name"],
				as_dict=True
			)

			if customer:
				self.linked_customer = customer.name
				if not self.contact_name:
					self.contact_name = (customer.organization_name or "")[:140]
				self.db_set("linked_customer", customer.name, update_modified=False)

				frappe.msgprint(f"Contacto vinculado automáticamente con Cliente: {customer.name}")

		except Exception as e:
			frappe.log_error(f"Error auto-linking contact to customer: {str(e)}")

	@frappe.whitelist()
	def sync_from_api(self):
		"""Sync contact information from WhatsApp API."""
		try:
			from xappiens_whatsapp.api.contacts import get_contact_details

			result = get_contact_details(self.session, self.contact_id)

			if result.get("success"):
				contact_data = result.get("contact", {})

				# Update contact information
				self.contact_name = contact_data.get("name") or self.contact_name
				self.pushname = contact_data.get("pushname") or self.pushname
				self.profile_pic_url = contact_data.get("profilePicUrl") or self.profile_pic_url
				self.about = contact_data.get("about") or self.about
				self.is_user = contact_data.get("isUser", self.is_user)
				self.is_my_contact = contact_data.get("isMyContact", self.is_my_contact)
				self.is_wa_contact = contact_data.get("isWAContact", self.is_wa_contact)
				self.is_blocked = contact_data.get("isBlocked", self.is_blocked)
				self.is_enterprise = contact_data.get("isBusiness", self.is_enterprise)

				self.last_sync = now()
				self.sync_count = (self.sync_count or 0) + 1
				self.sync_status = "Synced"
				self.sync_error = None

				self.save()

				return {"success": True, "message": "Contact synced successfully"}
			else:
				self.sync_status = "Error"
				self.sync_error = result.get("message", "Unknown error")
				self.save()

				return {"success": False, "message": self.sync_error}

		except Exception as e:
			frappe.log_error(f"Error syncing contact {self.contact_id}: {str(e)}")
			self.sync_status = "Error"
			self.sync_error = str(e)
			self.save()

			return {"success": False, "message": str(e)}

	@frappe.whitelist()
	def get_profile_picture(self):
		"""Download and save profile picture."""
		try:
			from xappiens_whatsapp.api.contacts import download_profile_picture

			result = download_profile_picture(self.session, self.contact_id)

			if result.get("success"):
				# Save profile picture as attachment
				file_path = result.get("file_path")
				if file_path:
					self.profile_pic_thumb = file_path
					self.last_profile_pic_update = now()
					self.save()

					return {"success": True, "message": "Profile picture downloaded"}

			return {"success": False, "message": "Failed to download profile picture"}

		except Exception as e:
			frappe.log_error(f"Error downloading profile picture for {self.contact_id}: {str(e)}")
			return {"success": False, "message": str(e)}

	@frappe.whitelist()
	def block_contact(self):
		"""Block this contact."""
		try:
			from xappiens_whatsapp.api.contacts import block_contact_api

			result = block_contact_api(self.session, self.contact_id)

			if result.get("success"):
				self.is_blocked = 1
				self.save()

				return {"success": True, "message": "Contact blocked"}

			return {"success": False, "message": "Failed to block contact"}

		except Exception as e:
			frappe.log_error(f"Error blocking contact {self.contact_id}: {str(e)}")
			return {"success": False, "message": str(e)}

	@frappe.whitelist()
	def unblock_contact(self):
		"""Unblock this contact."""
		try:
			from xappiens_whatsapp.api.contacts import unblock_contact_api

			result = unblock_contact_api(self.session, self.contact_id)

			if result.get("success"):
				self.is_blocked = 0
				self.save()

				return {"success": True, "message": "Contact unblocked"}

			return {"success": False, "message": "Failed to unblock contact"}

		except Exception as e:
			frappe.log_error(f"Error unblocking contact {self.contact_id}: {str(e)}")
			return {"success": False, "message": str(e)}

	def auto_link_to_lead(self):
		"""
		Vincula automáticamente este contacto de WhatsApp con un lead de CRM
		a través del número de teléfono.

		Returns:
			Dict con resultado de la vinculación
		"""
		try:
			if not self.phone_number:
				return {
					"success": False,
					"message": "No hay número de teléfono para vincular"
				}

			# Normalizar número de teléfono para búsqueda
			# WhatsApp: 34657032985 (sin +)
			# CRM Lead: +34657032985 (con +)
			phone_with_plus = f"+{self.phone_number}"

			# Buscar lead por número de teléfono
			leads = frappe.get_all("CRM Lead",
				filters={"mobile_no": phone_with_plus},
				fields=["name", "lead_name", "mobile_no", "status"],
				limit=1
			)

			if not leads:
				return {
					"success": False,
					"message": f"No se encontró lead con número {phone_with_plus}",
					"phone_searched": phone_with_plus
				}

			lead = leads[0]

			# Verificar si ya está vinculado
			if self.linked_lead == lead.name:
				return {
					"success": True,
					"message": f"Ya está vinculado con el lead {lead.lead_name}",
					"lead_name": lead.lead_name,
					"lead_status": lead.status
				}

			# Vincular con el lead encontrado
			frappe.db.set_value("WhatsApp Contact", self.name, "linked_lead", lead.name)
			frappe.db.commit()

			return {
				"success": True,
				"message": f"Vinculado exitosamente con el lead {lead.lead_name}",
				"lead_name": lead.lead_name,
				"lead_status": lead.status,
				"phone_matched": phone_with_plus
			}

		except Exception as e:
			frappe.log_error(f"Error linking contact {self.contact_id} to lead: {str(e)}")
			return {
				"success": False,
				"message": f"Error al vincular: {str(e)}"
			}

	def unlink_from_lead(self):
		"""
		Desvincula este contacto de WhatsApp del lead actual.

		Returns:
			Dict con resultado de la desvinculación
		"""
		try:
			if not self.linked_lead:
				return {
					"success": False,
					"message": "No hay lead vinculado para desvincular"
				}

			lead_name = self.linked_lead
			frappe.db.set_value("WhatsApp Contact", self.name, "linked_lead", None)
			frappe.db.commit()

			return {
				"success": True,
				"message": f"Desvinculado exitosamente del lead {lead_name}"
			}

		except Exception as e:
			frappe.log_error(f"Error unlinking contact {self.contact_id} from lead: {str(e)}")
			return {
				"success": False,
				"message": f"Error al desvincular: {str(e)}"
			}

	@staticmethod
	def bulk_auto_link_contacts():
		"""
		Vincula automáticamente todos los contactos de WhatsApp con leads de CRM
		que tengan números de teléfono coincidentes.

		Returns:
			Dict con estadísticas de la vinculación masiva
		"""
		try:
			# Obtener todos los contactos de WhatsApp con número de teléfono
			contacts = frappe.get_all("WhatsApp Contact",
				filters={"phone_number": ["!=", ""]},
				fields=["name", "contact_id", "phone_number", "linked_lead"]
			)

			stats = {
				"total_contacts": len(contacts),
				"already_linked": 0,
				"newly_linked": 0,
				"no_lead_found": 0,
				"errors": 0,
				"details": []
			}

			for contact in contacts:
				try:
					# Si ya está vinculado, contar como ya vinculado
					if contact.linked_lead:
						stats["already_linked"] += 1
						stats["details"].append({
							"contact": contact.contact_id,
							"status": "already_linked",
							"lead": contact.linked_lead
						})
						continue

					# Normalizar número para búsqueda
					phone_with_plus = f"+{contact.phone_number}"

					# Buscar lead
					leads = frappe.get_all("CRM Lead",
						filters={"mobile_no": phone_with_plus},
						fields=["name", "lead_name"],
						limit=1
					)

					if not leads:
						stats["no_lead_found"] += 1
						stats["details"].append({
							"contact": contact.contact_id,
							"status": "no_lead_found",
							"phone_searched": phone_with_plus
						})
						continue

					# Vincular
					lead = leads[0]
					frappe.db.set_value("WhatsApp Contact", contact.name, "linked_lead", lead.name)

					stats["newly_linked"] += 1
					stats["details"].append({
						"contact": contact.contact_id,
						"status": "newly_linked",
						"lead": lead.lead_name,
						"phone_matched": phone_with_plus
					})

				except Exception as e:
					stats["errors"] += 1
					stats["details"].append({
						"contact": contact.contact_id,
						"status": "error",
						"error": str(e)
					})

			# Commit todos los cambios
			frappe.db.commit()

			return {
				"success": True,
				"message": f"Vinculación masiva completada",
				"stats": stats
			}

		except Exception as e:
			frappe.log_error(f"Error in bulk auto link contacts: {str(e)}")
			return {
				"success": False,
				"message": f"Error en vinculación masiva: {str(e)}"
			}

