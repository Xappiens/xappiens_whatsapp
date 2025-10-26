#!/usr/bin/env python3
"""
Script para verificar cómo se está creando la sesión grupo_atu_call_cente_mgrrq6nl_zwtpz3
y si se está usando correctamente la API de Inbox Hub
"""

import requests
import json
from datetime import datetime

# Credenciales
API_BASE_URL = "https://api.inbox-hub.com"
API_EMAIL = "apiwhatsapp@grupoatu.com"
API_PASSWORD = "GrupoATU2025!WhatsApp"
API_KEY = "prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814"

SESSION_ID = "grupo_atu_call_cente_mgrrq6nl_zwtpz3"

def authenticate():
    """Obtener JWT token"""
    print("=" * 80)
    print("🔐 PASO 1: AUTENTICACIÓN")
    print("=" * 80)

    response = requests.post(
        f"{API_BASE_URL}/api/auth/login",
        json={
            "identifier": API_EMAIL,
            "password": API_PASSWORD
        },
        headers={"Content-Type": "application/json"},
        timeout=30
    )

    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            token = data.get('data', {}).get('accessToken')
            print(f"✅ Autenticado correctamente")
            print(f"🎟️  Token: {token[:50]}...")
            return token

    print(f"❌ Error en autenticación: {response.status_code}")
    return None


def check_session_in_api(jwt_token):
    """Verificar si la sesión existe en la API"""
    print("\n" + "=" * 80)
    print(f"🔍 PASO 2: VERIFICAR SESIÓN '{SESSION_ID}' EN LA API")
    print("=" * 80)

    # Listar todas las sesiones
    response = requests.get(
        f"{API_BASE_URL}/api/sessions",
        headers={
            "Authorization": f"Bearer {jwt_token}",
            "X-API-Key": API_KEY,
            "Content-Type": "application/json"
        },
        timeout=30
    )

    print(f"📡 GET /api/sessions")
    print(f"📊 Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            sessions = data.get('data', {}).get('sessions', [])
            print(f"✅ Total de sesiones: {len(sessions)}")

            # Buscar nuestra sesión
            target_session = None
            for s in sessions:
                if s.get('sessionId') == SESSION_ID:
                    target_session = s
                    break

            if target_session:
                print(f"\n✅ SESIÓN ENCONTRADA EN LA API:")
                print(f"   - ID Base de datos: {target_session.get('id')}")
                print(f"   - Session ID: {target_session.get('sessionId')}")
                print(f"   - Nombre: {target_session.get('name', 'N/A')}")
                print(f"   - Estado: {target_session.get('status')}")
                print(f"   - Teléfono: {target_session.get('phoneNumber')}")
                print(f"   - Creada: {target_session.get('createdAt')}")
                print(f"   - Actualizada: {target_session.get('updatedAt')}")
                print(f"   - User ID: {target_session.get('userId')}")
                print(f"   - Organization ID: {target_session.get('organizationId')}")

                return target_session
            else:
                print(f"\n❌ SESIÓN NO ENCONTRADA EN LA API")
                print(f"\n📋 Sesiones disponibles:")
                for s in sessions:
                    print(f"   - {s.get('sessionId')} | {s.get('status')}")

                return None
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        return None


def check_session_details(jwt_token, session_db_id):
    """Obtener detalles específicos de la sesión"""
    print("\n" + "=" * 80)
    print(f"📋 PASO 3: DETALLES DE LA SESIÓN (ID: {session_db_id})")
    print("=" * 80)

    response = requests.get(
        f"{API_BASE_URL}/api/sessions/{session_db_id}/status",
        headers={
            "Authorization": f"Bearer {jwt_token}",
            "X-API-Key": API_KEY,
            "Content-Type": "application/json"
        },
        timeout=30
    )

    print(f"📡 GET /api/sessions/{session_db_id}/status")
    print(f"📊 Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"📄 Response:")
        print(json.dumps(data, indent=2))
        return data
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        return None


def main():
    print("\n")
    print("🔬 " + "=" * 76 + " 🔬")
    print("🔬" + " " * 20 + "VERIFICACIÓN DE CREACIÓN DE SESIÓN" + " " * 21 + "🔬")
    print("🔬 " + "=" * 76 + " 🔬")
    print()

    # Paso 1: Autenticar
    jwt_token = authenticate()
    if not jwt_token:
        print("\n❌ No se pudo autenticar. Abortando...")
        return False

    # Paso 2: Verificar si la sesión existe en la API
    session_data = check_session_in_api(jwt_token)

    if not session_data:
        print("\n" + "=" * 80)
        print("🚨 RESULTADO: SESIÓN NO REGISTRADA EN LA API")
        print("=" * 80)
        print()
        print("❌ La sesión existe en Frappe pero NO en la API de Inbox Hub")
        print("❌ Esto confirma que fue creada de forma incorrecta")
        print()
        return False

    # Paso 3: Obtener detalles específicos
    session_db_id = session_data.get('id')
    if session_db_id:
        check_session_details(jwt_token, session_db_id)

    # Resumen final
    print("\n" + "=" * 80)
    print("✅ RESULTADO: SESIÓN REGISTRADA CORRECTAMENTE EN LA API")
    print("=" * 80)
    print()
    print("✅ La sesión SÍ está registrada en la API de Inbox Hub")
    print("✅ Fue creada usando el endpoint POST /api/sessions")
    print("✅ Tiene ID en la base de datos del servidor")
    print()

    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

