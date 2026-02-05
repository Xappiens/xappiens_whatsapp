#!/usr/bin/env python3
"""
Debug específico del problema de generación de QR
"""

import requests
import json
import time
from datetime import datetime

API_BASE_URL = "https://api.inbox-hub.com"
API_KEY = "prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814"

def debug_qr_generation():
    """Debug completo del proceso de generación de QR"""
    print("🔍 DEBUG: ¿POR QUÉ NO SE GENERA EL QR?")
    print("="*60)

    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

    # 1. Crear sesión
    timestamp = int(time.time())
    session_data = {
        "sessionId": f"debug_qr_{timestamp}",
        "sessionName": f"Debug QR {timestamp}",
        "fromFrappe": True
    }

    print("1️⃣ Creando sesión...")
    try:
        create_response = requests.post(f"{API_BASE_URL}/api/sessions", json=session_data, headers=headers, timeout=30)

        if create_response.status_code == 201:
            result = create_response.json()
            session_info = result.get('data', {}).get('session', {})
            session_id = session_info.get('id')
            session_name = session_info.get('sessionId')
            initial_status = session_info.get('status')

            print(f"✅ Sesión creada:")
            print(f"   ID: {session_id}")
            print(f"   Name: {session_name}")
            print(f"   Estado inicial: {initial_status}")

            # 2. Conectar sesión
            print(f"\n2️⃣ Conectando sesión {session_id}...")
            connect_response = requests.post(f"{API_BASE_URL}/api/sessions/{session_id}/connect", headers=headers, json={}, timeout=30)

            print(f"📊 Status de conexión: {connect_response.status_code}")

            if connect_response.status_code == 200:
                connect_result = connect_response.json()
                print(f"✅ Conexión iniciada:")
                print(f"   Mensaje: {connect_result.get('message')}")
                print(f"   Estado: {connect_result.get('data', {}).get('status')}")

                # 3. Monitorear estado y QR durante 2 minutos
                print(f"\n3️⃣ Monitoreando estado y QR (2 minutos)...")

                for attempt in range(24):  # 24 intentos de 5 segundos = 2 minutos
                    time.sleep(5)
                    elapsed = (attempt + 1) * 5

                    print(f"\n🔍 Minuto {elapsed//60}:{elapsed%60:02d} (Intento {attempt + 1}/24)")

                    # Verificar estado
                    try:
                        status_response = requests.get(f"{API_BASE_URL}/api/sessions/{session_id}/status", headers=headers, timeout=10)

                        if status_response.status_code == 200:
                            status_result = status_response.json()
                            if status_result.get('success'):
                                status_data = status_result.get('data', {})
                                current_status = status_data.get('status')
                                is_connected = status_data.get('isConnected')
                                has_qr = status_data.get('hasQR')
                                phone = status_data.get('phoneNumber')

                                print(f"   📊 Estado: {current_status}")
                                print(f"   🔗 Conectado: {is_connected}")
                                print(f"   📱 Tiene QR: {has_qr}")
                                print(f"   📞 Teléfono: {phone}")

                                # Si ya está conectado, terminar
                                if current_status == 'connected':
                                    print(f"\n🎉 ¡SESIÓN CONECTADA! No necesita QR")
                                    return True

                                # Si tiene QR disponible, intentar obtenerlo
                                if has_qr or current_status in ['qr_code', 'pending']:
                                    print(f"   📱 QR debería estar disponible, intentando obtener...")

                                    qr_response = requests.get(f"{API_BASE_URL}/api/sessions/{session_id}/qr", headers=headers, timeout=10)
                                    print(f"   📊 QR Response: {qr_response.status_code}")

                                    if qr_response.status_code == 200:
                                        qr_result = qr_response.json()
                                        print(f"   📄 QR Result: {json.dumps(qr_result, indent=6)[:300]}...")

                                        if qr_result.get('success'):
                                            qr_data = qr_result.get('data', {})
                                            qr_code = qr_data.get('qrCode')

                                            if qr_code:
                                                print(f"\n🎉 ¡QR OBTENIDO!")
                                                print(f"   📏 Longitud: {len(qr_code)} caracteres")
                                                print(f"   ⏰ Expira: {qr_data.get('expiresAt')}")
                                                print(f"   📱 Formato: {'Data URL' if qr_code.startswith('data:') else 'Base64'}")
                                                return True
                                            else:
                                                print(f"   ⚠️  QR vacío en respuesta")
                                        else:
                                            print(f"   ❌ Error en QR: {qr_result.get('message')}")
                                    else:
                                        qr_error = qr_response.json() if qr_response.text else {}
                                        print(f"   ❌ Error QR HTTP: {qr_error.get('error', 'Unknown')}")
                                        print(f"   📄 Error Code: {qr_error.get('code', 'Unknown')}")

                                        # Analizar el error específico
                                        if qr_error.get('code') == 'QR_GENERATION_ERROR':
                                            print(f"   🔍 DIAGNÓSTICO: Error interno generando QR")
                                            print(f"   💡 POSIBLE CAUSA: Baileys no puede generar QR para esta sesión")

                            else:
                                print(f"   ❌ Error obteniendo estado: {status_result.get('message')}")
                        else:
                            print(f"   ❌ Error HTTP estado: {status_response.status_code}")

                    except Exception as e:
                        print(f"   ❌ Excepción monitoreando: {str(e)}")

                print(f"\n⏰ Timeout después de 2 minutos")
                return False

            else:
                connect_error = connect_response.json() if connect_response.text else {}
                print(f"❌ Error conectando: {connect_error}")
                return False
        else:
            print(f"❌ Error creando sesión: {create_response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Error general: {str(e)}")
        return False

def analyze_qr_problem():
    """Análisis del problema de QR"""
    print("\n" + "="*60)
    print("🔍 ANÁLISIS DEL PROBLEMA DE QR")
    print("="*60)

    print("📋 FLUJO ESPERADO:")
    print("1. Crear sesión → ✅ FUNCIONA")
    print("2. Conectar sesión → ✅ FUNCIONA")
    print("3. Baileys inicia proceso WhatsApp Web → ❓")
    print("4. Baileys genera QR → ❌ FALLA")
    print("5. QR disponible via API → ❌ NO DISPONIBLE")

    print("\n💡 POSIBLES CAUSAS:")
    print("1. 🔧 Configuración de Baileys incorrecta")
    print("2. 📱 Problema con WhatsApp Web backend")
    print("3. 🌐 Conectividad con servidores de WhatsApp")
    print("4. ⚙️  Recursos insuficientes del servidor")
    print("5. 📦 Versión incompatible de Baileys")
    print("6. 🔐 Problemas de autenticación con WhatsApp")

    print("\n🎯 RECOMENDACIONES PARA BAILEYS:")
    print("1. Revisar logs de Baileys durante generación QR")
    print("2. Verificar configuración de WhatsApp Web")
    print("3. Comprobar conectividad con wa.me")
    print("4. Validar recursos del servidor (memoria/CPU)")
    print("5. Probar con sesión manual en entorno dev")

if __name__ == "__main__":
    print("🚀 DEBUG COMPLETO - PROBLEMA DE QR")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    success = debug_qr_generation()

    if not success:
        analyze_qr_problem()

        print(f"\n📞 MENSAJE PARA BAILEYS:")
        print("El endpoint /connect funciona, pero el QR nunca se genera.")
        print("La sesión se queda en estado 'connecting' indefinidamente.")
        print("Necesitan revisar el proceso interno de generación de QR.")
