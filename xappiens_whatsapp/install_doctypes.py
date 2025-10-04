#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para instalar DocTypes de Xappiens WhatsApp sin usar migrate.

Este script carga manualmente cada DocType desde sus archivos JSON
y crea las tablas correspondientes en la base de datos.

Uso:
    bench --site [sitio] execute xappiens_whatsapp.install_doctypes.install_all_doctypes

Autor: Xappiens
Fecha: 2025-10-04
"""

import frappe


def install_all_doctypes():
    """
    Instala todos los DocTypes de Xappiens WhatsApp.

    Este método:
    1. Lee los archivos JSON de cada DocType
    2. Crea/actualiza el DocType en la base de datos
    3. Sincroniza la tabla en la base de datos
    4. NO ejecuta patches ni otras migraciones

    Returns:
        dict: Resultado de la operación con contadores de éxito/error
    """

    module_name = "Xappiens Whatsapp"
    app_name = "xappiens_whatsapp"

    # Lista completa de DocTypes en orden de dependencias
    # Child tables primero, luego los padres
    doctypes = [
        # Child Tables (no tienen dependencias)
        "WhatsApp Session User",
        "WhatsApp Message Media",
        "WhatsApp Group Participant",
        "WhatsApp AI Conversation Log",

        # DocTypes principales (en orden de dependencias)
        "WhatsApp Settings",          # Single, sin dependencias
        "WhatsApp Label",              # Sin dependencias
        "WhatsApp Session",            # Depende de Session User (child)
        "WhatsApp Contact",            # Depende de Session
        "WhatsApp Group",              # Depende de Session y Group Participant (child)
        "WhatsApp Conversation",       # Depende de Session, Contact, Group
        "WhatsApp Message",            # Depende de Conversation, Message Media (child)
        "WhatsApp Media File",         # Depende de Message
        "WhatsApp AI Agent",           # Depende de AI Conversation Log (child)
        "WhatsApp Analytics",          # Depende de Session
        "WhatsApp Activity Log",       # Depende de Session
        "WhatsApp Webhook Config",     # Sin dependencias fuertes
        "WhatsApp Webhook Log",        # Depende de Webhook Config
    ]

    print("\n" + "="*70)
    print("🚀 INSTALACIÓN DE DOCTYPES - XAPPIENS WHATSAPP")
    print("="*70)
    print(f"\nMódulo: {module_name}")
    print(f"App: {app_name}")
    print(f"Total DocTypes: {len(doctypes)}")
    print(f"Sitio: {frappe.local.site}")
    print("\n" + "-"*70)

    success_count = 0
    error_count = 0
    errors = []

    for idx, doctype in enumerate(doctypes, 1):
        try:
            print(f"\n[{idx}/{len(doctypes)}] Procesando: {doctype}...")

            # Convertir nombre de DocType a nombre de carpeta
            doctype_folder = doctype.lower().replace(" ", "_")

            # Usar reload_doc para cargar el DocType
            # Esto lee el JSON, actualiza/crea el DocType y sincroniza la tabla
            frappe.reload_doc(
                module=module_name,   # Nombre del módulo Frappe
                dt="doctype",         # Tipo de documento (siempre "doctype")
                dn=doctype_folder,    # Nombre de la carpeta del DocType
                force=True            # Forzar recarga incluso si existe
            )

            # Verificar que se creó
            if frappe.db.exists("DocType", doctype):
                print(f"   ✅ {doctype} - Creado exitosamente")

                # Verificar si la tabla existe
                table_name = f"tab{doctype}"
                if frappe.db.table_exists(table_name):
                    print(f"   ✅ Tabla '{table_name}' creada en la base de datos")
                else:
                    print(f"   ⚠️  Tabla '{table_name}' NO encontrada (puede ser normal para child tables)")

                success_count += 1
            else:
                print(f"   ❌ {doctype} - Error: DocType no encontrado después de reload")
                error_count += 1
                errors.append(f"{doctype}: DocType no encontrado")

        except Exception as e:
            print(f"   ❌ {doctype} - Error: {str(e)}")
            error_count += 1
            errors.append(f"{doctype}: {str(e)}")

    # Commit de cambios
    frappe.db.commit()

    # Resumen final
    print("\n" + "="*70)
    print("📊 RESUMEN DE INSTALACIÓN")
    print("="*70)
    print(f"\n✅ DocTypes instalados exitosamente: {success_count}/{len(doctypes)}")
    print(f"❌ Errores: {error_count}/{len(doctypes)}")

    if errors:
        print("\n⚠️  ERRORES DETALLADOS:")
        for error in errors:
            print(f"   - {error}")

    print("\n" + "="*70)

    if error_count == 0:
        print("🎉 ¡INSTALACIÓN COMPLETADA CON ÉXITO!")
        print("\nPróximos pasos:")
        print("1. Reiniciar bench: bench restart")
        print("2. Limpiar cache: bench --site [sitio] clear-cache")
        print("3. Acceder a Frappe y buscar 'Xappiens Whatsapp' en el menú")
    else:
        print("⚠️  INSTALACIÓN COMPLETADA CON ERRORES")
        print(f"\nSe instalaron {success_count} DocTypes correctamente.")
        print(f"Revisa los {error_count} errores listados arriba.")

    print("="*70 + "\n")

    return {
        "success": error_count == 0,
        "total": len(doctypes),
        "success_count": success_count,
        "error_count": error_count,
        "errors": errors,
        "site": frappe.local.site
    }


def verify_installation():
    """
    Verifica que todos los DocTypes estén correctamente instalados.

    Uso:
        bench --site [sitio] execute xappiens_whatsapp.install_doctypes.verify_installation
    """

    doctypes = [
        "WhatsApp Session User",
        "WhatsApp Message Media",
        "WhatsApp Group Participant",
        "WhatsApp AI Conversation Log",
        "WhatsApp Settings",
        "WhatsApp Label",
        "WhatsApp Session",
        "WhatsApp Contact",
        "WhatsApp Group",
        "WhatsApp Conversation",
        "WhatsApp Message",
        "WhatsApp Media File",
        "WhatsApp AI Agent",
        "WhatsApp Analytics",
        "WhatsApp Activity Log",
        "WhatsApp Webhook Config",
        "WhatsApp Webhook Log",
    ]

    print("\n" + "="*70)
    print("🔍 VERIFICACIÓN DE INSTALACIÓN - XAPPIENS WHATSAPP")
    print("="*70 + "\n")

    installed = 0
    missing = []

    for doctype in doctypes:
        exists = frappe.db.exists("DocType", doctype)
        table_name = f"tab{doctype}"
        table_exists = frappe.db.table_exists(table_name)

        if exists and table_exists:
            print(f"✅ {doctype:40} [DocType: ✓] [Tabla: ✓]")
            installed += 1
        elif exists:
            print(f"⚠️  {doctype:40} [DocType: ✓] [Tabla: ✗]")
            installed += 1
        else:
            print(f"❌ {doctype:40} [DocType: ✗] [Tabla: ✗]")
            missing.append(doctype)

    print("\n" + "="*70)
    print(f"📊 Resultado: {installed}/{len(doctypes)} DocTypes instalados")

    if missing:
        print(f"\n❌ DocTypes faltantes ({len(missing)}):")
        for dt in missing:
            print(f"   - {dt}")
    else:
        print("\n🎉 ¡Todos los DocTypes están correctamente instalados!")

    print("="*70 + "\n")

    return {
        "total": len(doctypes),
        "installed": installed,
        "missing": missing
    }


def uninstall_all_doctypes():
    """
    PELIGRO: Elimina todos los DocTypes de Xappiens WhatsApp.

    Esto eliminará:
    - Los DocTypes de la base de datos
    - Todas las tablas asociadas
    - TODOS LOS DATOS

    Uso:
        bench --site [sitio] execute xappiens_whatsapp.install_doctypes.uninstall_all_doctypes
    """

    print("\n" + "="*70)
    print("⚠️  ADVERTENCIA: DESINSTALACIÓN DE DOCTYPES")
    print("="*70)
    print("\n🚨 ESTA OPERACIÓN ELIMINARÁ TODOS LOS DATOS 🚨\n")

    # Lista en orden inverso para eliminar dependencias primero
    doctypes = [
        "WhatsApp Webhook Log",
        "WhatsApp Webhook Config",
        "WhatsApp Activity Log",
        "WhatsApp Analytics",
        "WhatsApp AI Agent",
        "WhatsApp Media File",
        "WhatsApp Message",
        "WhatsApp Conversation",
        "WhatsApp Group",
        "WhatsApp Contact",
        "WhatsApp Session",
        "WhatsApp Label",
        "WhatsApp Settings",
        "WhatsApp AI Conversation Log",
        "WhatsApp Group Participant",
        "WhatsApp Message Media",
        "WhatsApp Session User",
    ]

    deleted = 0
    errors = []

    for doctype in doctypes:
        try:
            if frappe.db.exists("DocType", doctype):
                print(f"🗑️  Eliminando: {doctype}...")
                frappe.delete_doc("DocType", doctype, force=True)
                deleted += 1
                print(f"   ✅ Eliminado")
            else:
                print(f"⏭️  {doctype} - No existe, saltando...")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            errors.append(f"{doctype}: {str(e)}")

    frappe.db.commit()

    print("\n" + "="*70)
    print(f"📊 DocTypes eliminados: {deleted}/{len(doctypes)}")
    if errors:
        print(f"❌ Errores: {len(errors)}")
        for error in errors:
            print(f"   - {error}")
    print("="*70 + "\n")

    return {"deleted": deleted, "errors": errors}

