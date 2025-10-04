#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script alternativo para instalar DocTypes sin usar migrate.
Usa carga directa desde JSON.
"""

import frappe
import json
import os
from frappe.modules.import_file import import_file_by_path


def install_all_doctypes_v2():
    """
    Instala DocTypes cargando directamente los archivos JSON.
    """

    app_path = frappe.get_app_path("xappiens_whatsapp")
    doctype_path = os.path.join(app_path, "doctype")

    # Lista de DocTypes en orden de dependencias
    doctypes_folders = [
        "whatsapp_session_user",
        "whatsapp_message_media",
        "whatsapp_group_participant",
        "whatsapp_ai_conversation_log",
        "whatsapp_settings",
        "whatsapp_label",
        "whatsapp_session",
        "whatsapp_contact",
        "whatsapp_group",
        "whatsapp_conversation",
        "whatsapp_message",
        "whatsapp_media_file",
        "whatsapp_ai_agent",
        "whatsapp_analytics",
        "whatsapp_activity_log",
        "whatsapp_webhook_config",
        "whatsapp_webhook_log",
    ]

    print("\n" + "="*70)
    print("🚀 INSTALACIÓN DIRECTA DE DOCTYPES - XAPPIENS WHATSAPP")
    print("="*70)
    print(f"\nApp path: {app_path}")
    print(f"DocType path: {doctype_path}")
    print(f"Total DocTypes: {len(doctypes_folders)}")
    print(f"Sitio: {frappe.local.site}")
    print("\n" + "-"*70)

    success_count = 0
    error_count = 0
    errors = []

    for idx, doctype_folder in enumerate(doctypes_folders, 1):
        try:
            json_path = os.path.join(doctype_path, doctype_folder, f"{doctype_folder}.json")

            print(f"\n[{idx}/{len(doctypes_folders)}] Procesando: {doctype_folder}")
            print(f"   Ruta: {json_path}")

            if not os.path.exists(json_path):
                print(f"   ❌ Archivo JSON no encontrado")
                error_count += 1
                errors.append(f"{doctype_folder}: JSON no encontrado")
                continue

            # Leer el JSON
            with open(json_path, 'r') as f:
                doc_dict = json.load(f)

            doctype_name = doc_dict.get("name")
            print(f"   DocType: {doctype_name}")

            # Usar import_file_by_path para cargar el DocType
            import_file_by_path(
                json_path,
                data_import=False,
                force=True,
                pre_process=None,
                reset_permissions=False
            )

            # Verificar que se creó
            if frappe.db.exists("DocType", doctype_name):
                print(f"   ✅ {doctype_name} - Creado exitosamente")

                # Verificar tabla
                table_name = f"tab{doctype_name}"
                if frappe.db.table_exists(table_name):
                    print(f"   ✅ Tabla '{table_name}' creada")
                    success_count += 1
                else:
                    # Para child tables, verificar si es child
                    if doc_dict.get("istable"):
                        print(f"   ✅ Child table (no necesita tabla independiente)")
                        success_count += 1
                    else:
                        print(f"   ⚠️  Tabla no encontrada, intentando sincronizar...")
                        # Forzar sincronización de la tabla
                        doctype_obj = frappe.get_doc("DocType", doctype_name)
                        doctype_obj.run_method("on_update")
                        frappe.db.commit()

                        if frappe.db.table_exists(table_name):
                            print(f"   ✅ Tabla '{table_name}' creada después de sincronización")
                            success_count += 1
                        else:
                            print(f"   ❌ No se pudo crear la tabla")
                            error_count += 1
                            errors.append(f"{doctype_name}: Tabla no creada")
            else:
                print(f"   ❌ DocType no encontrado después de importación")
                error_count += 1
                errors.append(f"{doctype_name}: DocType no encontrado")

        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            error_count += 1
            errors.append(f"{doctype_folder}: {str(e)}")

    # Commit final
    frappe.db.commit()

    # Resumen
    print("\n" + "="*70)
    print("📊 RESUMEN DE INSTALACIÓN")
    print("="*70)
    print(f"\n✅ DocTypes instalados exitosamente: {success_count}/{len(doctypes_folders)}")
    print(f"❌ Errores: {error_count}/{len(doctypes_folders)}")

    if errors:
        print("\n⚠️  ERRORES DETALLADOS:")
        for error in errors:
            print(f"   - {error}")

    print("\n" + "="*70)

    if error_count == 0:
        print("🎉 ¡INSTALACIÓN COMPLETADA CON ÉXITO!")
        print("\nPróximos pasos:")
        print("1. bench --site [sitio] clear-cache")
        print("2. bench restart")
    else:
        print("⚠️  INSTALACIÓN COMPLETADA CON ERRORES")

    print("="*70 + "\n")

    return {
        "success": error_count == 0,
        "total": len(doctypes_folders),
        "success_count": success_count,
        "error_count": error_count,
        "errors": errors
    }

