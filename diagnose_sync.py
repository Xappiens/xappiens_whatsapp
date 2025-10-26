#!/usr/bin/env python3
"""
Script de diagnóstico para entender qué pasa durante la sincronización
"""

import requests
import json
import time

API_BASE_URL = "https://api.inbox-hub.com"
API_EMAIL = "apiwhatsapp@grupoatu.com"
API_PASSWORD = "GrupoATU2025!WhatsApp"
API_KEY = "prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814"
SESSION_ID = "prueba1_mgrgocue_vxkn2u"

def check_status(jwt_token, step_name):
    """Verifica el estado de la sesión"""
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "X-API-Key": API_KEY
    }

    response = requests.get(f"{API_BASE_URL}/api/sessions", headers=headers)
    sessions = response.json()["data"]["sessions"]

    for session in sessions:
        if session.get("sessionId") == SESSION_ID:
            status = session.get("status")
            print(f"  [{step_name}] Estado: {status}")
            return status

    return "NOT_FOUND"

print("="*80)
print("🔍 DIAGNÓSTICO DE SINCRONIZACIÓN")
print("="*80)
print(f"Sesión: {SESSION_ID}\n")

# Autenticar
print("1️⃣ Autenticando...")
response = requests.post(
    f"{API_BASE_URL}/api/auth/login",
    json={"identifier": API_EMAIL, "password": API_PASSWORD}
)
jwt_token = response.json()["data"]["accessToken"]
print("   ✅ Autenticado\n")

# Estado inicial
print("2️⃣ Estado ANTES de cualquier operación:")
initial_status = check_status(jwt_token, "INICIAL")
print()

# Preparar headers
headers = {
    "Authorization": f"Bearer {jwt_token}",
    "X-API-Key": API_KEY
}

# Simular el flujo de sincronización
print("3️⃣ Simulando flujo de sincronización:\n")

# Paso 1: get_sessions (verificación)
print("   🔍 Llamando a GET /api/sessions (verificación)...")
response = requests.get(f"{API_BASE_URL}/api/sessions", headers=headers)
time.sleep(0.5)
check_status(jwt_token, "Después de get_sessions")
print()

# Paso 2: get_session_contacts
print("   👥 Llamando a GET /api/contacts/{sessionId} (5 contactos)...")
try:
    response = requests.get(
        f"{API_BASE_URL}/api/contacts/{SESSION_ID}",
        headers=headers,
        params={"page": 1, "limit": 5}
    )
    print(f"   Response: {response.status_code}")
    if response.status_code != 200:
        print(f"   Error: {response.text[:200]}")
except Exception as e:
    print(f"   Error: {e}")

time.sleep(0.5)
check_status(jwt_token, "Después de get_contacts")
print()

# Paso 3: get_session_chats
print("   💬 Llamando a GET /api/messages/{sessionId}/chats (5 chats)...")
try:
    response = requests.get(
        f"{API_BASE_URL}/api/messages/{SESSION_ID}/chats",
        headers=headers,
        params={"page": 1, "limit": 5}
    )
    print(f"   Response: {response.status_code}")
    if response.status_code != 200:
        print(f"   Error: {response.text[:200]}")
except Exception as e:
    print(f"   Error: {e}")

time.sleep(0.5)
check_status(jwt_token, "Después de get_chats")
print()

# Paso 4: get_chat_messages (solo 1 chat)
print("   📨 Llamando a GET /api/messages/{sessionId}/{chatId} (mensajes de 1 chat)...")
try:
    # Primero necesitamos un chatId
    response = requests.get(
        f"{API_BASE_URL}/api/messages/{SESSION_ID}/chats",
        headers=headers,
        params={"page": 1, "limit": 1}
    )

    if response.status_code == 200:
        chats = response.json().get("data", {}).get("chats", [])
        if chats:
            chat_id = chats[0].get("chatId")
            print(f"   Obteniendo mensajes de chat: {chat_id}")

            response = requests.get(
                f"{API_BASE_URL}/api/messages/{SESSION_ID}/{chat_id}",
                headers=headers,
                params={"page": 1, "limit": 5}
            )
            print(f"   Response: {response.status_code}")
            if response.status_code != 200:
                print(f"   Error: {response.text[:200]}")
        else:
            print("   No hay chats disponibles")
    else:
        print(f"   No se pudieron obtener chats: {response.status_code}")

except Exception as e:
    print(f"   Error: {e}")

time.sleep(0.5)
final_status = check_status(jwt_token, "Después de get_messages")
print()

# Resumen
print("="*80)
print("📊 RESUMEN")
print("="*80)
print(f"Estado inicial:  {initial_status}")
print(f"Estado final:    {final_status}")
print()

if initial_status != final_status:
    print("⚠️  EL ESTADO CAMBIÓ DURANTE LAS OPERACIONES")
    print("   Esto explica por qué la sesión aparece como 'connecting' después")
else:
    print("✅ El estado NO cambió durante las operaciones")
    print("   El problema debe estar en otro lado")

print("="*80)

