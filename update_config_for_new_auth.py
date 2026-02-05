#!/usr/bin/env python3
"""
Script para actualizar la configuración de WhatsApp Settings
según la nueva documentación que solo requiere API Key
"""

import frappe

def update_whatsapp_settings():
    """
    Actualiza WhatsApp Settings para usar solo API Key
    """
    print("🔧 Actualizando configuración de WhatsApp Settings...")

    try:
        # Obtener configuración actual
        settings = frappe.get_single("WhatsApp Settings")

        print(f"📋 Configuración actual:")
        print(f"   - Enabled: {settings.enabled}")
        print(f"   - API Base URL: {settings.api_base_url}")
        print(f"   - API Key: {settings.get_password('api_key')[:30] if settings.get_password('api_key') else 'No configurada'}...")
        print(f"   - API Email: {settings.api_email}")

        # Verificar que tenemos la API Key
        api_key = settings.get_password('api_key')
        if not api_key:
            print("❌ Error: API Key no configurada")
            return False

        # Verificar que es la API Key correcta según nueva documentación
        expected_api_key = "prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814"
        if api_key != expected_api_key:
            print("⚠️  Actualizando API Key según nueva documentación...")
            settings.api_key = expected_api_key

        # Actualizar URL base si es necesario
        if settings.api_base_url != "https://api.inbox-hub.com":
            print("⚠️  Actualizando URL base...")
            settings.api_base_url = "https://api.inbox-hub.com"

        # Asegurar que está habilitado
        if not settings.enabled:
            print("⚠️  Habilitando módulo de WhatsApp...")
            settings.enabled = 1

        # Configurar timeouts optimizados
        settings.api_timeout = 30
        settings.api_retry_attempts = 3

        # Configurar webhooks
        settings.webhook_enabled = 1
        if not settings.webhook_secret:
            settings.webhook_secret = "whatsapp_webhook_secret_2025"
            print("⚠️  Configurando webhook secret...")

        # Eventos de webhook según nueva documentación
        new_webhook_events = "message.received,message.sent,message.ack,session.connected,session.disconnected,session.qr"
        if settings.webhook_events != new_webhook_events:
            print("⚠️  Actualizando eventos de webhook...")
            settings.webhook_events = new_webhook_events

        # Guardar cambios
        settings.save()
        frappe.db.commit()

        print("✅ Configuración actualizada exitosamente")
        print("\n📋 Nueva configuración:")
        print(f"   - Enabled: {settings.enabled}")
        print(f"   - API Base URL: {settings.api_base_url}")
        print(f"   - API Key: {settings.get_password('api_key')[:30]}...")
        print(f"   - Webhook Enabled: {settings.webhook_enabled}")
        print(f"   - Webhook Events: {settings.webhook_events}")
        print(f"   - API Timeout: {settings.api_timeout}s")
        print(f"   - Retry Attempts: {settings.api_retry_attempts}")

        return True

    except Exception as e:
        print(f"❌ Error actualizando configuración: {str(e)}")
        return False

def test_new_configuration():
    """
    Probar la nueva configuración usando solo API Key
    """
    print("\n🧪 Probando nueva configuración...")

    try:
        from xappiens_whatsapp.api.base import WhatsAppAPIClient

        # Crear cliente con nueva configuración
        client = WhatsAppAPIClient()

        print(f"📡 Probando conexión con API Key...")

        # Probar obtener sesiones (solo requiere API Key)
        response = client.get_sessions(limit=5)

        if response.get("success"):
            sessions = response.get("data", {}).get("sessions", [])
            print(f"✅ Prueba exitosa: {len(sessions)} sesiones encontradas")

            # Mostrar sesiones
            for session in sessions[:3]:
                status_emoji = "🟢" if session.get("status") == "connected" else "🔴"
                print(f"   {status_emoji} {session.get('sessionId', 'N/A')} - {session.get('status', 'N/A')}")

            return True
        else:
            print(f"❌ Error en prueba: {response.get('message', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"❌ Error en prueba: {str(e)}")
        return False

def main():
    """
    Función principal
    """
    print("🚀 ACTUALIZACIÓN DE CONFIGURACIÓN WHATSAPP")
    print("📅 Adaptando a nueva documentación (solo API Key)")
    print("="*60)

    # Actualizar configuración
    if update_whatsapp_settings():
        # Probar nueva configuración
        if test_new_configuration():
            print("\n🎉 ACTUALIZACIÓN COMPLETADA EXITOSAMENTE")
            print("✅ WhatsApp Settings configurado para usar solo API Key")
            print("✅ Configuración probada y funcionando")
            print("\n📚 Cambios realizados:")
            print("   - Eliminada dependencia de JWT Token")
            print("   - API Key actualizada según nueva documentación")
            print("   - Webhooks configurados correctamente")
            print("   - Timeouts optimizados")
        else:
            print("\n⚠️  Configuración actualizada pero falló la prueba")
            print("   Revisar conectividad con el servidor")
    else:
        print("\n❌ Error actualizando configuración")

if __name__ == "__main__":
    # Ejecutar en contexto de Frappe
    frappe.init(site="crm.grupoatu.com")
    frappe.connect()

    try:
        main()
    finally:
        frappe.destroy()
