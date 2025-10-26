#!/usr/bin/env python3
"""
Script para enviar un mensaje de WhatsApp de prueba
"""

import requests
import json

# Configuración
API_BASE_URL = "https://api.inbox-hub.com"
API_EMAIL = "apiwhatsapp@grupoatu.com"
API_PASSWORD = "GrupoATU2025!WhatsApp"
API_KEY = "prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814"

# Datos del mensaje
SESSION_ID = "prueba2_mgri15c2_9aa6i1"  # La sesión conectada
TO_NUMBER = "34657032985"  # Número destino
MESSAGE_TEXT = "🧪 Mensaje de prueba desde el API de Inbox Hub - Python Script"

print("="*80)
print("📱 ENVÍO DE MENSAJE DE WHATSAPP")
print("="*80)
print(f"Sesión: {SESSION_ID}")
print(f"Destino: {TO_NUMBER}")
print(f"Mensaje: {MESSAGE_TEXT}")
print()

# Paso 1: Autenticar
print("1️⃣ Autenticando...")
try:
    response = requests.post(
        f"{API_BASE_URL}/api/auth/login",
        json={
            "identifier": API_EMAIL,
            "password": API_PASSWORD
        },
        timeout=30
    )

    if response.status_code != 200:
        print(f"❌ Error en autenticación: {response.status_code}")
        print(response.text)
        exit(1)

    jwt_token = response.json()["data"]["accessToken"]
    print(f"✅ Autenticado correctamente")
    print(f"   Token: {jwt_token[:50]}...")
    print()

except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

# Paso 2: Verificar estado de la sesión
print("2️⃣ Verificando estado de la sesión...")
try:
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

    response = requests.get(
        f"{API_BASE_URL}/api/sessions",
        headers=headers,
        timeout=30
    )

    if response.status_code != 200:
        print(f"❌ Error obteniendo sesiones: {response.status_code}")
        print(response.text)
        exit(1)

    sessions = response.json()["data"]["sessions"]
    current_session = None

    for session in sessions:
        if session["sessionId"] == SESSION_ID:
            current_session = session
            break

    if not current_session:
        print(f"❌ Sesión {SESSION_ID} no encontrada")
        exit(1)

    status = current_session["status"]
    phone = current_session.get("phoneNumber")

    print(f"✅ Sesión encontrada")
    print(f"   Estado: {status}")
    print(f"   Teléfono: {phone}")
    print()

    if status != "connected":
        print(f"⚠️  ADVERTENCIA: La sesión no está conectada (estado: {status})")
        print("   El mensaje podría no enviarse correctamente")
        print()

except Exception as e:
    print(f"❌ Error verificando sesión: {e}")
    exit(1)

# Paso 3: Enviar mensaje
print("3️⃣ Enviando mensaje de WhatsApp...")
try:
    # Intentar con formato completo de WhatsApp
    # El número puede necesitar el sufijo @s.whatsapp.net
    to_formatted = f"{TO_NUMBER}@s.whatsapp.net"

    # Según la documentación (línea 453-483)
    payload = {
        "to": to_formatted,
        "message": MESSAGE_TEXT,
        "type": "text"
    }

    print(f"📤 POST {API_BASE_URL}/api/messages/{SESSION_ID}/send")
    print(f"📦 Payload: {json.dumps(payload, indent=2)}")
    print()

    response = requests.post(
        f"{API_BASE_URL}/api/messages/{SESSION_ID}/send",
        headers=headers,
        json=payload,
        timeout=30
    )

    print(f"📊 Status Code: {response.status_code}")
    print(f"📄 Response:")
    print(json.dumps(response.json(), indent=2))
    print()

    if response.status_code in [200, 201]:
        data = response.json()
        if data.get("success"):
            print("="*80)
            print("🎉 ¡MENSAJE ENVIADO EXITOSAMENTE!")
            print("="*80)
            print(f"📱 ID del mensaje: {data['data'].get('messageId')}")
            print(f"✅ Estado: {data['data'].get('status')}")
            print(f"⏰ Timestamp: {data['data'].get('timestamp')}")
            print("="*80)
        else:
            print("❌ El servidor respondió pero el mensaje no se envió:")
            print(f"   Error: {data.get('error')}")
    else:
        print("❌ ERROR AL ENVIAR MENSAJE")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:500]}")

except Exception as e:
    print(f"❌ Excepción al enviar mensaje: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print()
print("="*80)
print("FIN DEL TEST")
print("="*80)

