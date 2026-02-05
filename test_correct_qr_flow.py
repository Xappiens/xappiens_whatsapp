#!/usr/bin/env python3
"""
Test del flujo correcto de QR según la documentación actualizada
"""

import requests
import json
import time
from datetime import datetime

# Configuración según documentación
API_BASE_URL = "https://api.inbox-hub.com"
API_KEY = "prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814"

def test_correct_qr_flow():
    """Test siguiendo el flujo exacto de la documentación"""
    print("🚀 TEST DEL FLUJO CORRECTO DE QR")
    print("📋 Siguiendo documentación actualizada")
    print("="*60)

    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

    # PASO 1: Crear Sesión (Solo API Key)
    print("1️⃣ CREAR SESIÓN")
    print("-" * 30)

    timestamp = int(time.time())
    session_data = {
        "sessionId": f"test_qr_flow_{timestamp}",
        "sessionName": f"Test QR Flow {timestamp}",
        "webhookUrl": "https://crm.grupoatu.com/api/method/xappiens_whatsapp.api.webhook.receive_webhook"
    }

    print(f"📡 POST {API_BASE_URL}/api/sessions")
    print(f"📋 Headers: X-API-Key (SOLO API Key)")
    print(f"📄 Body: {json.dumps(session_data, indent=2)}")

    try:
        create_response = requests.post(
            f"{API_BASE_URL}/api/sessions",
            json=session_data,
            headers=headers,
            timeout=30
        )

        print(f"📊 Status: {create_response.status_code}")

        if create_response.status_code == 201:
            create_result = create_response.json()
            session_info = create_result.get('data', {}).get('session', {})
            session_id = session_info.get('id')  # ID NUMÉRICO
            session_name = session_info.get('sessionId')  # String ID

            print(f"✅ Sesión creada exitosamente:")
            print(f"   ID numérico: {session_id}")
            print(f"   Session ID: {session_name}")
            print(f"   Estado inicial: {session_info.get('status')}")

            # PASO 2: Conectar Sesión (Solo API Key)
            print(f"\n2️⃣ CONECTAR SESIÓN")
            print("-" * 30)

            connect_url = f"{API_BASE_URL}/api/sessions/{session_id}/connect"
            print(f"📡 POST {connect_url}")
            print(f"📋 Headers: X-API-Key (SOLO API Key)")
            print(f"📄 Body: {{}}")

            connect_response = requests.post(
                connect_url,
                json={},
                headers=headers,
                timeout=30
            )

            print(f"📊 Status: {connect_response.status_code}")

            if connect_response.status_code == 200:
                connect_result = connect_response.json()
                print(f"✅ Conexión iniciada:")
                print(f"   Mensaje: {connect_result.get('message')}")
                print(f"   Estado: {connect_result.get('data', {}).get('status')}")

                # PASO CRÍTICO: Esperar 2-3 segundos
                print(f"\n⏳ ESPERANDO 3 SEGUNDOS (según documentación)")
                print("   El sistema necesita este tiempo para generar el QR...")
                time.sleep(3)

                # PASO 3: Obtener QR en Base64 (Solo API Key)
                print(f"\n3️⃣ OBTENER QR EN BASE64")
                print("-" * 30)

                qr_url = f"{API_BASE_URL}/api/sessions/{session_id}/qr"
                print(f"📡 GET {qr_url}")
                print(f"📋 Headers: X-API-Key (SOLO API Key)")

                qr_response = requests.get(
                    qr_url,
                    headers=headers,
                    timeout=30
                )

                print(f"📊 Status: {qr_response.status_code}")

                if qr_response.status_code == 200:
                    qr_result = qr_response.json()
                    print(f"📄 Response: {json.dumps(qr_result, indent=2)[:300]}...")

                    if qr_result.get('success'):
                        qr_data = qr_result.get('data', {})
                        qr_code = qr_data.get('qrCode')

                        if qr_code:
                            print(f"\n🎉 ¡QR OBTENIDO EXITOSAMENTE!")
                            print(f"   📏 Longitud: {len(qr_code)} caracteres")
                            print(f"   📱 Formato: {'Data URL' if qr_code.startswith('data:') else 'Base64'}")
                            print(f"   ⏰ Expira: {qr_data.get('expiresAt')}")
                            print(f"   📊 Estado: {qr_data.get('status')}")
                            print(f"   🆔 Session ID: {qr_data.get('sessionId')}")

                            # Mostrar preview del QR
                            if qr_code.startswith('data:image'):
                                print(f"   🖼️  Preview: {qr_code[:50]}...")
                            else:
                                print(f"   🖼️  Preview: data:image/png;base64,{qr_code[:50]}...")

                            return {
                                'success': True,
                                'session_id': session_id,
                                'session_name': session_name,
                                'qr_code': qr_code,
                                'expires_at': qr_data.get('expiresAt')
                            }
                        else:
                            print(f"\n⚠️  QR vacío en respuesta")
                            return {'success': False, 'error': 'QR vacío'}
                    else:
                        error_msg = qr_result.get('message', 'Error desconocido')
                        print(f"\n❌ Error obteniendo QR: {error_msg}")
                        return {'success': False, 'error': error_msg}
                else:
                    qr_error = qr_response.json() if qr_response.text else {}
                    error_msg = qr_error.get('error', 'Error HTTP')
                    error_code = qr_error.get('code', 'Unknown')

                    print(f"\n❌ Error HTTP {qr_response.status_code}:")
                    print(f"   Error: {error_msg}")
                    print(f"   Code: {error_code}")

                    return {'success': False, 'error': f"{error_code}: {error_msg}"}
            else:
                connect_error = connect_response.json() if connect_response.text else {}
                error_msg = connect_error.get('error', 'Error HTTP')

                print(f"\n❌ Error conectando: {error_msg}")
                return {'success': False, 'error': f"Connect error: {error_msg}"}
        else:
            create_error = create_response.json() if create_response.text else {}
            error_msg = create_error.get('error', 'Error HTTP')

            print(f"\n❌ Error creando sesión: {error_msg}")
            return {'success': False, 'error': f"Create error: {error_msg}"}

    except Exception as e:
        print(f"\n❌ Excepción: {str(e)}")
        return {'success': False, 'error': f"Exception: {str(e)}"}

def main():
    """Ejecutar test completo"""
    print("🚀 TEST DEL FLUJO CORRECTO DE QR SEGÚN DOCUMENTACIÓN")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Servidor: {API_BASE_URL}")
    print(f"🔑 API Key: {API_KEY[:20]}...")

    result = test_correct_qr_flow()

    print("\n" + "="*60)
    print("🎯 RESULTADO FINAL")
    print("="*60)

    if result.get('success'):
        print("🎉 ¡FLUJO COMPLETO EXITOSO!")
        print("✅ Crear sesión: OK")
        print("✅ Conectar sesión: OK")
        print("✅ Esperar 3 segundos: OK")
        print("✅ Obtener QR Base64: OK")

        print(f"\n📱 INFORMACIÓN DEL QR:")
        print(f"   Session ID: {result.get('session_name')}")
        print(f"   QR Length: {len(result.get('qr_code', ''))} chars")
        print(f"   Expires: {result.get('expires_at')}")

        print(f"\n🚀 EL FLUJO FUNCIONA CORRECTAMENTE")
        print(f"💡 Clave: Esperar 3 segundos después de conectar")

    else:
        print("❌ FLUJO FALLÓ")
        print(f"   Error: {result.get('error')}")

        print(f"\n🔍 DIAGNÓSTICO:")
        if "QR_GENERATION_ERROR" in str(result.get('error', '')):
            print("   El servidor aún tiene problemas generando QR")
            print("   Necesita más tiempo o configuración adicional")
        elif "Connect error" in str(result.get('error', '')):
            print("   Problema en la conexión de sesión")
        else:
            print("   Error inesperado en el flujo")

if __name__ == "__main__":
    main()
