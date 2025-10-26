#!/usr/bin/env python3
"""
Script de prueba para la API de Baileys/Inbox Hub
Prueba la autenticación y obtención de contactos directamente
"""

import requests
import json
from datetime import datetime, timedelta

# Credenciales de WhatsApp Settings (crm.grupoatu.com)
API_BASE_URL = "https://api.inbox-hub.com"  # URL REAL del sistema
API_EMAIL = "apiwhatsapp@grupoatu.com"
API_PASSWORD = "GrupoATU2025!WhatsApp"
API_KEY = "prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814"

# Variable para cachear el token
_cached_token = None
_token_expiry = None


def authenticate():
    """
    Paso 1: Autenticación JWT
    """
    print("="*80)
    print("🔐 PASO 1: AUTENTICACIÓN JWT")
    print("="*80)

    url = f"{API_BASE_URL}/api/auth/login"
    payload = {
        "identifier": API_EMAIL,
        "password": API_PASSWORD
    }

    print(f"📡 POST {url}")
    print(f"📦 Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"📊 Status Code: {response.status_code}")
        print(f"📄 Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                token = data.get("data", {}).get("accessToken")  # CORRECCIÓN: es accessToken, no token
                print(f"\n✅ Autenticación exitosa!")
                print(f"🎟️  JWT Token: {token[:50] if token else 'ERROR: Token no encontrado'}...")

                global _cached_token, _token_expiry
                _cached_token = token
                _token_expiry = datetime.now() + timedelta(hours=1)

                return token
            else:
                print(f"\n❌ Error: {data.get('error', 'Unknown error')}")
                return None
        else:
            print(f"\n❌ Error HTTP {response.status_code}")
            return None

    except Exception as e:
        print(f"\n❌ Excepción: {str(e)}")
        return None


def get_sessions(jwt_token):
    """
    Paso 2: Obtener lista de sesiones
    """
    print("\n" + "="*80)
    print("📱 PASO 2: OBTENER SESIONES")
    print("="*80)

    url = f"{API_BASE_URL}/api/sessions"
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

    print(f"📡 GET {url}")
    print(f"📋 Headers:")
    print(f"   - Authorization: Bearer {jwt_token[:30]}...")
    print(f"   - X-API-Key: {API_KEY[:30]}...")

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
                connected_sessions = [s for s in sessions if s.get("status") == "CONNECTED"]
                print(f"🟢 Sesiones conectadas: {len(connected_sessions)}")

                if connected_sessions:
                    print("\n📋 Sesiones disponibles:")
                    for session in connected_sessions[:3]:  # Mostrar solo las primeras 3
                        print(f"   - ID: {session.get('sessionId')}")
                        print(f"     Nombre: {session.get('name', 'Sin nombre')}")
                        print(f"     Teléfono: {session.get('phoneNumber', 'N/A')}")
                        print(f"     Estado: {session.get('status')}")
                        print()

                    return connected_sessions[0].get('sessionId')  # Retornar la primera
                else:
                    print("⚠️  No hay sesiones conectadas")
                    return None
            else:
                print(f"\n❌ Error: {data.get('error', 'Unknown error')}")
                return None
        else:
            print(f"📄 Response: {response.text[:500]}")
            print(f"\n❌ Error HTTP {response.status_code}")
            return None

    except Exception as e:
        print(f"\n❌ Excepción: {str(e)}")
        return None


def get_contacts(jwt_token, session_id):
    """
    Paso 3: Obtener contactos de una sesión
    """
    print("\n" + "="*80)
    print("👥 PASO 3: OBTENER CONTACTOS")
    print("="*80)

    url = f"{API_BASE_URL}/api/contacts/{session_id}"
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    params = {
        "page": 1,
        "limit": 10  # Solo 10 para prueba
    }

    print(f"📡 GET {url}")
    print(f"🔑 Session ID: {session_id}")
    print(f"📋 Headers:")
    print(f"   - Authorization: Bearer {jwt_token[:30]}...")
    print(f"   - X-API-Key: {API_KEY[:30]}...")
    print(f"📊 Params: {params}")

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        print(f"📊 Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"📄 Response (primeros 1000 chars):")
            print(json.dumps(data, indent=2)[:1000])

            if data.get("success"):
                contacts = data.get("data", {}).get("contacts", [])
                print(f"\n✅ Se encontraron {len(contacts)} contactos")

                if contacts:
                    print("\n📋 Primeros 5 contactos:")
                    for contact in contacts[:5]:
                        print(f"   - Teléfono: {contact.get('phoneNumber', 'N/A')}")
                        print(f"     Nombre: {contact.get('name', 'Sin nombre')}")
                        print(f"     Push Name: {contact.get('pushName', 'N/A')}")
                        print()

                    return contacts
                else:
                    print("⚠️  No hay contactos en esta sesión")
                    return []
            else:
                print(f"\n❌ Error: {data.get('error', 'Unknown error')}")
                return None
        else:
            print(f"📄 Response Text: {response.text[:500]}")
            print(f"\n❌ Error HTTP {response.status_code}")
            return None

    except Exception as e:
        print(f"\n❌ Excepción: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """
    Función principal para probar toda la cadena
    """
    print("\n")
    print("🚀 " + "="*76 + " 🚀")
    print("🚀" + " "*30 + "TEST API BAILEYS" + " "*31 + "🚀")
    print("🚀 " + "="*76 + " 🚀")
    print()

    # Paso 1: Autenticar
    jwt_token = authenticate()
    if not jwt_token:
        print("\n❌ FALLO EN AUTENTICACIÓN. Abortando...")
        return False

    # Paso 2: Obtener sesiones
    session_id = get_sessions(jwt_token)
    if not session_id:
        print("\n❌ NO SE ENCONTRARON SESIONES CONECTADAS. Abortando...")
        return False

    # Paso 3: Obtener contactos
    contacts = get_contacts(jwt_token, session_id)
    if contacts is None:
        print("\n❌ ERROR OBTENIENDO CONTACTOS")
        return False

    # Resumen final
    print("\n" + "="*80)
    print("📊 RESUMEN FINAL")
    print("="*80)
    print(f"✅ Autenticación: OK")
    print(f"✅ Sesión encontrada: {session_id}")
    print(f"✅ Contactos obtenidos: {len(contacts) if contacts else 0}")
    print()
    print("🎉 ¡PRUEBA COMPLETADA CON ÉXITO!")
    print("="*80)

    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

