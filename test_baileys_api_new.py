#!/usr/bin/env python3
"""
Script de prueba ACTUALIZADO para la API de Baileys/Inbox Hub
Usa SOLO API Key según la nueva documentación (Octubre 2025)
"""

import requests
import json
from datetime import datetime

# Configuración desde WhatsApp Settings
def get_whatsapp_config():
    """Obtiene la configuración desde WhatsApp Settings de Frappe"""
    try:
        import frappe
        frappe.init(site='crm.grupoatu.com')
        frappe.connect()

        settings = frappe.get_single("WhatsApp Settings")
        config = {
            'api_base_url': settings.api_base_url or "https://api.inbox-hub.com",
            'api_key': settings.get_password("api_key"),
        }

        frappe.destroy()
        return config
    except Exception as e:
        print(f"⚠️  No se pudo obtener config desde Frappe: {e}")
        print("🔄 Usando configuración por defecto de la documentación...")
        return {
            'api_base_url': "https://api.inbox-hub.com",
            'api_key': "prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814",
        }

# Obtener configuración
config = get_whatsapp_config()
API_BASE_URL = config['api_base_url']
API_KEY = config['api_key']

def get_headers():
    """
    Headers simplificados según nueva documentación.
    SOLO API Key, NO JWT Token.
    """
    return {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

def test_connection():
    """
    Paso 1: Probar conectividad básica
    """
    print("="*80)
    print("🔗 PASO 1: TEST DE CONECTIVIDAD")
    print("="*80)

    url = f"{API_BASE_URL}/health"
    print(f"📡 GET {url}")

    try:
        response = requests.get(url, timeout=10)
        print(f"📊 Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"📄 Response: {json.dumps(data, indent=2)}")
            print("✅ Servidor accesible")
            return True
        else:
            print(f"❌ Error HTTP {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Error de conexión: {str(e)}")
        return False

def get_sessions():
    """
    Paso 2: Obtener lista de sesiones (SOLO API KEY)
    """
    print("\n" + "="*80)
    print("📱 PASO 2: OBTENER SESIONES (SOLO API KEY)")
    print("="*80)

    url = f"{API_BASE_URL}/api/sessions"
    headers = get_headers()

    print(f"📡 GET {url}")
    print(f"📋 Headers SIMPLIFICADOS:")
    print(f"   - X-API-Key: {API_KEY[:30]}...")
    print(f"   - Content-Type: application/json")
    print("⚠️  NOTA: Ya NO se usa Authorization Bearer según nueva documentación")

    try:
        response = requests.get(url, headers=headers, timeout=30)
        print(f"📊 Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"📄 Response: {json.dumps(data, indent=2)[:500]}...")

            if data.get("success"):
                sessions = data.get("data", {}).get("sessions", [])
                print(f"\n✅ Se encontraron {len(sessions)} sesiones")

                # Mostrar sesiones conectadas
                connected_sessions = [s for s in sessions if s.get("status") == "connected"]
                print(f"🟢 Sesiones conectadas: {len(connected_sessions)}")

                for session in sessions:
                    status_emoji = "🟢" if session.get("status") == "connected" else "🔴"
                    print(f"   {status_emoji} {session.get('sessionId', 'N/A')} - {session.get('status', 'N/A')}")

                return sessions
            else:
                print(f"❌ Error en respuesta: {data.get('message', 'Unknown error')}")
                return None
        else:
            print(f"❌ Error HTTP {response.status_code}")
            try:
                error_data = response.json()
                print(f"📄 Error Response: {json.dumps(error_data, indent=2)}")
            except:
                print(f"📄 Error Text: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Excepción: {str(e)}")
        return None

def get_session_status(session_id):
    """
    Paso 3: Obtener estado específico de una sesión
    """
    print(f"\n" + "="*80)
    print(f"🔍 PASO 3: ESTADO DE SESIÓN {session_id}")
    print("="*80)

    # Probar ambos endpoints según documentación
    endpoints = [
        f"/api/sessions/{session_id}/status",  # Por sessionId string
        f"/api/sessions/29/status"  # Por ID numérico (si conocemos el ID)
    ]

    headers = get_headers()

    for endpoint in endpoints:
        url = f"{API_BASE_URL}{endpoint}"
        print(f"📡 GET {url}")

        try:
            response = requests.get(url, headers=headers, timeout=30)
            print(f"📊 Status Code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"📄 Response: {json.dumps(data, indent=2)}")

                if data.get("success"):
                    session_data = data.get("data", {})
                    status = session_data.get("status", "unknown")
                    is_connected = session_data.get("isConnected", False)
                    phone = session_data.get("phoneNumber", "N/A")

                    print(f"✅ Estado: {status}")
                    print(f"📞 Teléfono: {phone}")
                    print(f"🔗 Conectado: {'Sí' if is_connected else 'No'}")
                    return session_data
                else:
                    print(f"❌ Error: {data.get('message', 'Unknown error')}")
            else:
                print(f"❌ Error HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"📄 Error: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"📄 Error Text: {response.text}")

        except Exception as e:
            print(f"❌ Excepción: {str(e)}")

        print()  # Separador entre endpoints

    return None

def get_contacts(session_id, limit=5):
    """
    Paso 4: Obtener contactos de una sesión
    """
    print(f"\n" + "="*80)
    print(f"👥 PASO 4: CONTACTOS DE SESIÓN {session_id}")
    print("="*80)

    url = f"{API_BASE_URL}/api/contacts/{session_id}"
    headers = get_headers()
    params = {"page": 1, "limit": limit}

    print(f"📡 GET {url}")
    print(f"📋 Params: {params}")

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        print(f"📊 Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"📄 Response: {json.dumps(data, indent=2)[:800]}...")

            if data.get("success"):
                contacts_data = data.get("data", {})
                contacts = contacts_data.get("contacts", [])
                total = contacts_data.get("pagination", {}).get("total", len(contacts))

                print(f"✅ Se encontraron {len(contacts)} contactos (de {total} totales)")

                for contact in contacts[:3]:  # Mostrar solo los primeros 3
                    name = contact.get("name") or contact.get("verifiedName", "Sin nombre")
                    phone = contact.get("id", "N/A")
                    print(f"   📞 {name} - {phone}")

                return contacts
            else:
                print(f"❌ Error: {data.get('message', 'Unknown error')}")
                return None
        else:
            print(f"❌ Error HTTP {response.status_code}")
            try:
                error_data = response.json()
                print(f"📄 Error: {json.dumps(error_data, indent=2)}")
            except:
                print(f"📄 Error Text: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Excepción: {str(e)}")
        return None

def send_test_message(session_id, to_number, message="Mensaje de prueba desde API"):
    """
    Paso 5: Enviar mensaje de prueba
    """
    print(f"\n" + "="*80)
    print(f"💬 PASO 5: ENVIAR MENSAJE DE PRUEBA")
    print("="*80)

    url = f"{API_BASE_URL}/api/messages/{session_id}/send"
    headers = get_headers()
    payload = {
        "to": to_number,
        "message": message,
        "type": "text"
    }

    print(f"📡 POST {url}")
    print(f"📦 Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f"📊 Status Code: {response.status_code}")

        if response.status_code in [200, 201]:
            data = response.json()
            print(f"📄 Response: {json.dumps(data, indent=2)}")

            if data.get("success"):
                message_data = data.get("data", {})
                message_id = message_data.get("messageId", "N/A")
                status = message_data.get("status", "N/A")

                print(f"✅ Mensaje enviado exitosamente")
                print(f"🆔 Message ID: {message_id}")
                print(f"📊 Status: {status}")
                return message_data
            else:
                print(f"❌ Error: {data.get('message', 'Unknown error')}")
                return None
        else:
            print(f"❌ Error HTTP {response.status_code}")
            try:
                error_data = response.json()
                print(f"📄 Error: {json.dumps(error_data, indent=2)}")
            except:
                print(f"📄 Error Text: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Excepción: {str(e)}")
        return None

def main():
    """
    Ejecutar todas las pruebas
    """
    print("🚀 PRUEBA COMPLETA DE API BAILEYS - NUEVA DOCUMENTACIÓN")
    print("📅 Fecha:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("🔑 Usando SOLO API Key (sin JWT Token)")
    print()

    # Paso 1: Test de conectividad
    if not test_connection():
        print("❌ No se puede conectar al servidor. Abortando pruebas.")
        return

    # Paso 2: Obtener sesiones
    sessions = get_sessions()
    if not sessions:
        print("❌ No se pudieron obtener sesiones. Abortando pruebas.")
        return

    # Buscar sesión activa
    active_session = None
    for session in sessions:
        if session.get("status") == "connected":
            active_session = session
            break

    if not active_session:
        print("⚠️  No hay sesiones conectadas. Usando la primera sesión disponible.")
        active_session = sessions[0] if sessions else None

    if not active_session:
        print("❌ No hay sesiones disponibles para probar.")
        return

    session_id = active_session.get("sessionId")
    print(f"\n🎯 Usando sesión: {session_id}")

    # Paso 3: Estado de la sesión
    session_status = get_session_status(session_id)

    # Paso 4: Contactos (solo si está conectada)
    if session_status and session_status.get("isConnected"):
        contacts = get_contacts(session_id, limit=5)

        # Paso 5: Enviar mensaje de prueba (comentado por seguridad)
        # DESCOMENTA SOLO SI QUIERES ENVIAR UN MENSAJE REAL
        # if contacts and len(contacts) > 0:
        #     first_contact = contacts[0]
        #     contact_id = first_contact.get("id", "")
        #     if contact_id and "@" in contact_id:
        #         phone_number = contact_id.split("@")[0]
        #         send_test_message(session_id, phone_number, "Prueba de API - Ignorar")
    else:
        print("⚠️  Sesión no conectada. Saltando pruebas de contactos y mensajes.")

    print("\n" + "="*80)
    print("🏁 PRUEBAS COMPLETADAS")
    print("="*80)
    print("✅ API Key funciona correctamente")
    print("✅ No se requiere JWT Token para rutas de WhatsApp")
    print("📚 Documentación actualizada confirmada")

if __name__ == "__main__":
    main()
