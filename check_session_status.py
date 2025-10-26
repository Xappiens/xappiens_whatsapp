#!/usr/bin/env python3
"""Verificar estado de una sesión específica"""

import requests
import json

API_BASE_URL = "https://api.inbox-hub.com"
API_EMAIL = "apiwhatsapp@grupoatu.com"
API_PASSWORD = "GrupoATU2025!WhatsApp"
API_KEY = "prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814"

# Sesión específica del usuario
SESSION_TO_CHECK = "prueba1_mgrgocue_vxkn2u"

print("🔍 Verificando estado de sesión:", SESSION_TO_CHECK)
print("="*80)

# Autenticar
response = requests.post(
    f"{API_BASE_URL}/api/auth/login",
    json={"identifier": API_EMAIL, "password": API_PASSWORD}
)
jwt_token = response.json()["data"]["accessToken"]
print("✅ Autenticado")

# Obtener sesiones
headers = {
    "Authorization": f"Bearer {jwt_token}",
    "X-API-Key": API_KEY
}

response = requests.get(f"{API_BASE_URL}/api/sessions", headers=headers)
sessions = response.json()["data"]["sessions"]

print(f"\n📱 Total de sesiones: {len(sessions)}\n")

for session in sessions:
    session_id = session.get("sessionId")
    status = session.get("status")
    phone = session.get("phoneNumber")

    marker = "🎯" if session_id == SESSION_TO_CHECK else "  "
    status_emoji = "🟢" if status == "connected" else "🔴"

    print(f"{marker} {status_emoji} {session_id}")
    print(f"   📞 Teléfono: {phone}")
    print(f"   📊 Estado: {status}")

    if session_id == SESSION_TO_CHECK:
        print(f"\n{'='*80}")
        print("🎯 SESIÓN OBJETIVO ENCONTRADA")
        print(f"{'='*80}")
        print(json.dumps(session, indent=2))

    print()

