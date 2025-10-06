# Copyright (c) 2025, Xappiens and contributors
# For license information, please see license.txt

import frappe


@frappe.whitelist()
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

                # Extraer número limpio del phone_number (quitar @c.us)
                clean_phone = contact.phone_number
                if "@c.us" in clean_phone:
                    clean_phone = clean_phone.replace("@c.us", "")
                elif "@lid" in clean_phone:
                    clean_phone = clean_phone.replace("@lid", "")

                # Normalizar número para búsqueda (agregar +)
                phone_with_plus = f"+{clean_phone}"

                # Buscar lead con diferentes formatos
                search_terms = [
                    phone_with_plus,  # +34657032985
                    clean_phone,      # 34657032985
                    f"+{clean_phone}", # +34657032985
                ]

                leads = []
                for term in search_terms:
                    leads = frappe.get_all("CRM Lead",
                        filters={"mobile_no": term},
                        fields=["name", "lead_name", "mobile_no"],
                        limit=1
                    )
                    if leads:
                        break

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


@frappe.whitelist()
def auto_link_single_contact(contact_name):
    """
    Vincula automáticamente un contacto específico de WhatsApp con un lead de CRM.

    Args:
        contact_name (str): Nombre del contacto de WhatsApp

    Returns:
        Dict con resultado de la vinculación
    """
    try:
        # Obtener el contacto
        contact = frappe.get_doc("WhatsApp Contact", contact_name)

        if not contact.phone_number:
            return {
                "success": False,
                "message": "No hay número de teléfono para vincular"
            }

        # Extraer número limpio del phone_number (quitar @c.us)
        clean_phone = contact.phone_number
        if "@c.us" in clean_phone:
            clean_phone = clean_phone.replace("@c.us", "")
        elif "@lid" in clean_phone:
            clean_phone = clean_phone.replace("@lid", "")

        # Normalizar número para búsqueda (agregar +)
        phone_with_plus = f"+{clean_phone}"

        # Buscar lead con diferentes formatos
        search_terms = [
            phone_with_plus,  # +34657032985
            clean_phone,      # 34657032985
            f"+{clean_phone}", # +34657032985
        ]

        leads = []
        for term in search_terms:
            leads = frappe.get_all("CRM Lead",
                filters={"mobile_no": term},
                fields=["name", "lead_name", "mobile_no", "status"],
                limit=1
            )
            if leads:
                break

        if not leads:
            return {
                "success": False,
                "message": f"No se encontró lead con número {phone_with_plus}",
                "phone_searched": phone_with_plus
            }

        lead = leads[0]

        # Verificar si ya está vinculado
        if contact.linked_lead == lead.name:
            return {
                "success": True,
                "message": f"Ya está vinculado con el lead {lead.lead_name}",
                "lead_name": lead.lead_name,
                "lead_status": lead.status
            }

        # Vincular con el lead encontrado
        frappe.db.set_value("WhatsApp Contact", contact.name, "linked_lead", lead.name)
        frappe.db.commit()

        return {
            "success": True,
            "message": f"Vinculado exitosamente con el lead {lead.lead_name}",
            "lead_name": lead.lead_name,
            "lead_status": lead.status,
            "phone_matched": phone_with_plus
        }

    except Exception as e:
        frappe.log_error(f"Error linking contact {contact_name} to lead: {str(e)}")
        return {
            "success": False,
            "message": f"Error al vincular: {str(e)}"
        }


@frappe.whitelist()
def unlink_single_contact(contact_name):
    """
    Desvincula un contacto específico de WhatsApp de su lead actual.

    Args:
        contact_name (str): Nombre del contacto de WhatsApp

    Returns:
        Dict con resultado de la desvinculación
    """
    try:
        # Obtener el contacto
        contact = frappe.get_doc("WhatsApp Contact", contact_name)

        if not contact.linked_lead:
            return {
                "success": False,
                "message": "No hay lead vinculado para desvincular"
            }

        lead_name = contact.linked_lead
        frappe.db.set_value("WhatsApp Contact", contact.name, "linked_lead", None)
        frappe.db.commit()

        return {
            "success": True,
            "message": f"Desvinculado exitosamente del lead {lead_name}"
        }

    except Exception as e:
        frappe.log_error(f"Error unlinking contact {contact_name} from lead: {str(e)}")
        return {
            "success": False,
            "message": f"Error al desvincular: {str(e)}"
        }
