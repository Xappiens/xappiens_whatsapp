#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de instalación para Xappiens WhatsApp.
Se ejecuta automáticamente después de instalar la app.
"""

import os
import frappe


def after_install():
	"""
	Se ejecuta después de instalar la app en un sitio.
	Crea el enlace simbólico necesario para que los módulos funcionen correctamente.
	"""
	create_module_symlink()
	cleanup_duplicate_message_ids()
	print("\n✅ Xappiens WhatsApp instalado correctamente")


def create_module_symlink():
	"""
	Crea un enlace simbólico para resolver el problema de rutas de módulos.

	Frappe busca: xappiens_whatsapp.xappiens_whatsapp.doctype
	Pero la estructura es: xappiens_whatsapp/xappiens_whatsapp/doctype

	El enlace simbólico permite que ambas rutas funcionen.
	"""
	try:
		app_path = frappe.get_app_path("xappiens_whatsapp")
		symlink_path = os.path.join(app_path, "xappiens_whatsapp")

		# Si el enlace ya existe, no hacer nada
		if os.path.exists(symlink_path):
			if os.path.islink(symlink_path):
				print(f"✓ Enlace simbólico ya existe: {symlink_path}")
				return
			else:
				print(f"⚠️ Existe un archivo/carpeta en {symlink_path}, no se puede crear el enlace")
				return

		# Crear el enlace simbólico apuntando al directorio actual (.)
		os.symlink(".", symlink_path)
		print(f"✅ Enlace simbólico creado: {symlink_path} -> .")

	except Exception as e:
		print(f"❌ Error al crear enlace simbólico: {str(e)}")
		print("⚠️ Es posible que necesites crear el enlace manualmente:")
		print(f"    cd {frappe.get_app_path('xappiens_whatsapp')}")
		print(f"    ln -s . xappiens_whatsapp")


def before_uninstall():
	"""
	Se ejecuta antes de desinstalar la app.
	Limpia el enlace simbólico.
	"""
	remove_module_symlink()
	print("\n✅ Xappiens WhatsApp desinstalado correctamente")


def remove_module_symlink():
	"""
	Elimina el enlace simbólico creado durante la instalación.
	"""
	try:
		app_path = frappe.get_app_path("xappiens_whatsapp")
		symlink_path = os.path.join(app_path, "xappiens_whatsapp")

		if os.path.islink(symlink_path):
			os.unlink(symlink_path)
			print(f"✅ Enlace simbólico eliminado: {symlink_path}")
		else:
			print(f"✓ No hay enlace simbólico para eliminar")

	except Exception as e:
		print(f"⚠️ Error al eliminar enlace simbólico: {str(e)}")


def cleanup_duplicate_message_ids():
	"""
	Limpia message_ids duplicados en WhatsApp Message antes de aplicar restricciones unique.
	Esto evita errores durante la instalación en sitios con datos existentes.
	"""
	try:
		# Verificar si la tabla existe
		if not frappe.db.table_exists("WhatsApp Message"):
			return

		# Obtener todos los message_ids duplicados
		duplicate_message_ids = frappe.db.sql("""
			SELECT message_id, COUNT(*) as count
			FROM `tabWhatsApp Message`
			WHERE message_id IS NOT NULL AND message_id != ''
			GROUP BY message_id
			HAVING COUNT(*) > 1
			ORDER BY count DESC
		""", as_dict=True)

		if not duplicate_message_ids:
			print("✓ No se encontraron message_ids duplicados")
			return

		print(f"⚠️ Encontrados {len(duplicate_message_ids)} message_ids duplicados")

		# Limpiar duplicados manteniendo solo el más reciente
		for duplicate in duplicate_message_ids:
			message_id = duplicate.message_id

			# Obtener todos los registros con este message_id
			duplicate_records = frappe.db.sql("""
				SELECT name, creation
				FROM `tabWhatsApp Message`
				WHERE message_id = %s
				ORDER BY creation DESC
			""", (message_id,), as_dict=True)

			# Mantener solo el más reciente, actualizar el resto
			if len(duplicate_records) > 1:
				records_to_update = duplicate_records[1:]  # Todos excepto el primero (más reciente)

				for record in records_to_update:
					# Actualizar el message_id para que sea único
					new_message_id = f"{message_id}_duplicate_{record.name}"
					frappe.db.sql("""
						UPDATE `tabWhatsApp Message`
						SET message_id = %s
						WHERE name = %s
					""", (new_message_id, record.name))

					print(f"✓ Actualizado message_id duplicado: {message_id} -> {new_message_id}")

		frappe.db.commit()
		print("✅ Limpieza de message_ids duplicados completada")

	except Exception as e:
		print(f"⚠️ Error durante la limpieza de message_ids duplicados: {str(e)}")
		print("⚠️ La aplicación se instalará, pero puede haber problemas con message_ids duplicados")

