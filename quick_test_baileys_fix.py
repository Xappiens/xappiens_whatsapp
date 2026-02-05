#!/usr/bin/env python3
"""
Test rápido para verificar si Baileys ha solucionado el problema
"""

import requests
import json
import time
from datetime import datetime

API_BASE_URL = "https://api.inbox-hub.com"
API_KEY = "prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814"

def quick_test():
    print("🚀 TEST RÁPIDO - ¿HAN ARREGLADO BAILEYS?")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

    # 1. Crear sesión
    print("1️⃣ Creando sesión...")
    timestamp = int(time.time())
    create_data = {
        "sessionId": f"quick_test_{timestamp}",
        "sessionName": f"Test Rápido {timestamp}"
    }

    try:
        response = requests.post(f"{API_BASE_URL}/api/sessions", json=create_data, headers=headers, timeout=10)
        if response.status_code == 201:
            result = response.json()
            session_id = result.get('data', {}).get('session', {}).get('id')
            print(f"✅ Sesión creada: ID {session_id}")

            # 2. Intentar conectar
            print("2️⃣ Intentando conectar...")
            connect_response = requests.post(f"{API_BASE_URL}/api/sessions/{session_id}/connect", headers=headers, json={}, timeout=10)

            print(f"📊 Status: {connect_response.status_code}")

            if connect_response.status_code == 200:
                print("🎉 ¡ARREGLADO! La conexión funciona")

                # Probar QR
                time.sleep(2)
                qr_response = requests.get(f"{API_BASE_URL}/api/sessions/{session_id}/qr", headers=headers, timeout=10)
                if qr_response.status_code == 200:
                    qr_result = qr_response.json()
                    if qr_result.get('success') and qr_result.get('data', {}).get('qrCode'):
                        print("🎉 ¡QR TAMBIÉN FUNCIONA!")
                        return True
                    else:
                        print("⚠️  Conexión OK pero QR aún no disponible")
                        return True
                else:
                    print(f"⚠️  Conexión OK pero QR falla: {qr_response.status_code}")
                    return True
            else:
                error_data = connect_response.json() if connect_response.text else {}
                print(f"❌ SIGUE ROTO: {connect_response.status_code}")
                print(f"   Error: {error_data.get('error', 'Unknown')}")
                print(f"   Code: {error_data.get('code', 'Unknown')}")
                return False
        else:
            print(f"❌ No se pudo crear sesión: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    is_fixed = quick_test()

    print("\n" + "="*60)
    if is_fixed:
        print("🎉 RESULTADO: ¡BAILEYS HA SIDO ARREGLADO!")
        print("✅ Puedes proceder con la integración normal")
    else:
        print("❌ RESULTADO: BAILEYS SIGUE ROTO")
        print("🔄 Necesitas contactar de nuevo al equipo técnico")
        print("📞 El problema CONNECTION_ERROR persiste")
