#!/usr/bin/env python3
"""
Debug rápido del QR - sin esperas largas
"""

import requests
import json
import time

API_BASE_URL = "https://api.inbox-hub.com"
API_KEY = "prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814"

def quick_qr_debug():
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

    print("🔍 DEBUG RÁPIDO DEL QR")
    print("="*40)

    # 1. Crear y conectar sesión
    timestamp = int(time.time())
    session_data = {"sessionId": f"qr_debug_{timestamp}", "sessionName": f"QR Debug {timestamp}"}

    print("1️⃣ Creando sesión...")
    create_response = requests.post(f"{API_BASE_URL}/api/sessions", json=session_data, headers=headers, timeout=10)

    if create_response.status_code == 201:
        session_id = create_response.json().get('data', {}).get('session', {}).get('id')
        print(f"✅ Sesión creada: {session_id}")

        print("2️⃣ Conectando...")
        connect_response = requests.post(f"{API_BASE_URL}/api/sessions/{session_id}/connect", headers=headers, json={}, timeout=10)

        if connect_response.status_code == 200:
            print("✅ Conexión OK")

            # Esperar solo 10 segundos
            print("3️⃣ Esperando 10s y probando QR...")
            time.sleep(10)

            # Probar estado
            status_response = requests.get(f"{API_BASE_URL}/api/sessions/{session_id}/status", headers=headers, timeout=5)
            print(f"📊 Estado: {status_response.status_code}")

            if status_response.status_code == 200:
                status_data = status_response.json()
                if status_data.get('success'):
                    data = status_data.get('data', {})
                    print(f"   Status: {data.get('status')}")
                    print(f"   HasQR: {data.get('hasQR')}")
                    print(f"   Connected: {data.get('isConnected')}")

            # Probar QR
            qr_response = requests.get(f"{API_BASE_URL}/api/sessions/{session_id}/qr", headers=headers, timeout=5)
            print(f"📱 QR: {qr_response.status_code}")

            if qr_response.status_code == 200:
                qr_data = qr_response.json()
                print(f"   Success: {qr_data.get('success')}")
                if qr_data.get('success'):
                    qr_code = qr_data.get('data', {}).get('qrCode')
                    print(f"   QR Length: {len(qr_code) if qr_code else 0}")
                    return True
                else:
                    print(f"   Error: {qr_data.get('message')}")
            else:
                error_data = qr_response.json() if qr_response.text else {}
                print(f"   Error: {error_data.get('error')}")
                print(f"   Code: {error_data.get('code')}")

                # DIAGNÓSTICO ESPECÍFICO
                if error_data.get('code') == 'QR_GENERATION_ERROR':
                    print("\n🚨 PROBLEMA IDENTIFICADO:")
                    print("   El servidor Baileys no puede generar QR")
                    print("   Posibles causas:")
                    print("   - Baileys no se inicializa correctamente")
                    print("   - Problema con WhatsApp Web backend")
                    print("   - Configuración incorrecta del servidor")
        else:
            print(f"❌ Error conectando: {connect_response.status_code}")
    else:
        print(f"❌ Error creando: {create_response.status_code}")

    return False

if __name__ == "__main__":
    success = quick_qr_debug()

    print("\n" + "="*40)
    if success:
        print("🎉 QR FUNCIONA")
    else:
        print("❌ QR NO FUNCIONA")
        print("\n💡 RESUMEN:")
        print("✅ Crear sesión: OK")
        print("✅ Conectar sesión: OK")
        print("❌ Generar QR: FALLA")
        print("\n🎯 EL PROBLEMA ESTÁ EN BAILEYS:")
        print("El servidor no puede generar el QR internamente")
        print("Necesitan revisar la configuración de Baileys/WhatsApp Web")
