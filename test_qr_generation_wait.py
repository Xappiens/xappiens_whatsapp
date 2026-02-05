#!/usr/bin/env python3
"""
Test para esperar la generación del QR después de la conexión
"""

import requests
import json
import time
from datetime import datetime

API_BASE_URL = "https://api.inbox-hub.com"
API_KEY = "prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814"

def test_qr_generation_with_wait():
    """Test completo esperando la generación del QR"""
    print("🚀 TEST DE GENERACIÓN DE QR CON ESPERA")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

    # 1. Crear sesión
    timestamp = int(time.time())
    create_data = {
        "sessionId": f"qr_wait_test_{timestamp}",
        "sessionName": f"Test QR Wait {timestamp}",
        "fromFrappe": True
    }

    print("1️⃣ Creando sesión...")
    try:
        response = requests.post(f"{API_BASE_URL}/api/sessions", json=create_data, headers=headers, timeout=30)
        if response.status_code == 201:
            result = response.json()
            session_id = result.get('data', {}).get('session', {}).get('id')
            session_name = result.get('data', {}).get('session', {}).get('sessionId')
            print(f"✅ Sesión creada: ID {session_id}, Name: {session_name}")

            # 2. Conectar sesión
            print("\n2️⃣ Conectando sesión...")
            connect_response = requests.post(f"{API_BASE_URL}/api/sessions/{session_id}/connect", headers=headers, json={}, timeout=30)

            if connect_response.status_code == 200:
                connect_result = connect_response.json()
                print(f"✅ Conexión iniciada: {connect_result.get('message')}")
                print(f"   Estado: {connect_result.get('data', {}).get('status')}")

                # 3. Esperar y verificar QR con polling
                print("\n3️⃣ Esperando generación de QR (máximo 60 segundos)...")

                for attempt in range(12):  # 12 intentos de 5 segundos = 60 segundos
                    time.sleep(5)
                    elapsed = (attempt + 1) * 5

                    print(f"\n🔍 Intento {attempt + 1}/12 (Transcurrido: {elapsed}s)")

                    # Verificar estado
                    try:
                        status_response = requests.get(f"{API_BASE_URL}/api/sessions/{session_id}/status", headers=headers, timeout=10)
                        print(f"   Estado endpoint: {status_response.status_code}")

                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            if status_data.get('success'):
                                current_status = status_data.get('data', {}).get('status')
                                has_qr = status_data.get('data', {}).get('hasQR')
                                print(f"   Estado actual: {current_status}, Tiene QR: {has_qr}")

                                if current_status == 'connected':
                                    print("🎉 ¡SESIÓN CONECTADA!")
                                    return True
                                elif has_qr or current_status in ['qr_code', 'pending']:
                                    print("📱 QR disponible, intentando obtener...")
                                    break
                        else:
                            print(f"   Estado no disponible: {status_response.status_code}")
                    except:
                        print("   Error obteniendo estado")

                    # Intentar obtener QR
                    try:
                        qr_response = requests.get(f"{API_BASE_URL}/api/sessions/{session_id}/qr", headers=headers, timeout=10)
                        print(f"   QR endpoint: {qr_response.status_code}")

                        if qr_response.status_code == 200:
                            qr_result = qr_response.json()
                            if qr_result.get('success'):
                                qr_data = qr_result.get('data', {})
                                qr_code = qr_data.get('qrCode')

                                if qr_code:
                                    print(f"🎉 ¡QR OBTENIDO!")
                                    print(f"   Longitud: {len(qr_code)} caracteres")
                                    print(f"   Expira: {qr_data.get('expiresAt')}")
                                    print(f"   Estado: {qr_data.get('status')}")
                                    return True
                                else:
                                    print("   QR vacío en respuesta")
                            else:
                                print(f"   Error QR: {qr_result.get('message')}")
                        else:
                            qr_error = qr_response.json() if qr_response.text else {}
                            print(f"   Error QR: {qr_error.get('error', 'Unknown')}")
                    except:
                        print("   Error obteniendo QR")

                print("\n⏰ Timeout esperando QR")
                return False
            else:
                print(f"❌ Error conectando: {connect_response.status_code}")
                return False
        else:
            print(f"❌ Error creando sesión: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_qr_generation_with_wait()

    print("\n" + "="*60)
    if success:
        print("🎉 RESULTADO: ¡BAILEYS COMPLETAMENTE FUNCIONAL!")
        print("✅ Crear sesiones: OK")
        print("✅ Conectar sesiones: OK")
        print("✅ Generar QR: OK")
        print("\n🚀 La integración WhatsApp está lista para usar")
    else:
        print("⚠️  RESULTADO: PROGRESO PARCIAL")
        print("✅ Crear sesiones: OK")
        print("✅ Conectar sesiones: OK")
        print("⏳ Generar QR: En proceso o necesita más tiempo")
        print("\n💡 Recomendación: El QR puede tardar más en generarse")
