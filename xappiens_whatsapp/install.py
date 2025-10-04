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

