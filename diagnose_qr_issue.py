#!/usr/bin/env python3
"""
Script de diagnóstico para problemas de generación de código QR
Analiza el flujo completo y proporciona soluciones.
"""

import requests
import json
import time
from datetime import datetime

# Configuración
API_BASE_URL = "https://api.inbox-hub.com"
API_KEY = "prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814"

def get_headers():
    return {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

def create_fresh_session():
    """Crear una nueva sesión completamente limpia"""
    print("="*80)
    print("🆕 CREANDO NUEVA SESIÓN LIMPIA")
    print("="*80)

    timestamp = int(time.time())
    session_id = f"qr_test_{timestamp}"

    create_data = {
        "sessionId": session_id,
        "sessionName": f"Prueba QR {timestamp}",
        "fromFrappe": True
    }

    print(f"📡 POST {API_BASE_URL}/api/sessions")
    print(f"📄 Body: {json.dumps(create_data, indent=2)}")

    try:
        response = requests.post(
            f"{API_BASE_URL}/api/sessions",
            json=create_data,
            headers=get_headers(),
            timeout=30
        )

        print(f"📊 Status Code: {response.status_code}")

        if response.status_code in [200, 201]:
            result = response.json()
            if result.get('success'):
                session_data = result.get('data', {}).get('session', {})
                session_db_id = session_data.get('id')

                print(f"✅ Sesión creada: ID {session_db_id}, SessionId: {session_id}")
                return session_db_id, session_id
            else:
                print(f"❌ Error: {result.get('message')}")
                return None, None
        else:
            print(f"❌ HTTP Error: {response.status_code} - {response.text}")
            return None, None

    except Exception as e:
        print(f"❌ Excepción: {str(e)}")
        return None, None

def connect_session_step_by_step(session_db_id):
    """Conectar sesión paso a paso con diagnóstico detallado"""
    print(f"\n" + "="*80)
    print(f"🔗 CONECTANDO SESIÓN {session_db_id} - PASO A PASO")
    print("="*80)

    # Paso 1: Verificar estado inicial
    print("📊 Paso 1: Estado inicial")
    status = get_session_status(session_db_id)
    if status:
        print(f"   Estado inicial: {status.get('status')}")
        print(f"   Conectado: {status.get('isConnected')}")
        print(f"   Tiene QR: {status.get('hasQR')}")

    # Paso 2: Iniciar conexión
    print("\n🔗 Paso 2: Iniciar conexión")
    connect_url = f"{API_BASE_URL}/api/sessions/{session_db_id}/connect"

    try:
        response = requests.post(
            connect_url,
            headers=get_headers(),
            json={},
            timeout=30
        )

        print(f"📊 Status Code: {response.status_code}")
        print(f"📄 Response: {response.text}")

        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ Conexión iniciada correctamente")
            else:
                print(f"⚠️  Respuesta: {result.get('message')}")
        else:
            print(f"❌ Error HTTP: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Error conectando: {str(e)}")
        return False

    # Paso 3: Esperar y verificar estado
    print("\n⏳ Paso 3: Esperando generación de QR (30 segundos)")
    for i in range(6):  # 6 intentos de 5 segundos
        time.sleep(5)
        print(f"   Intento {i+1}/6...")

        status = get_session_status(session_db_id)
        if status:
            current_status = status.get('status')
            has_qr = status.get('hasQR')

            print(f"   Estado: {current_status}, Tiene QR: {has_qr}")

            if current_status == 'qr_code' or has_qr:
                print("✅ QR disponible!")
                return True
            elif current_status == 'connected':
                print("✅ Ya conectado!")
                return True
            elif current_status == 'error':
                print("❌ Error en la sesión")
                return False

    print("⚠️  Timeout esperando QR")
    return False

def get_session_status(session_db_id):
    """Obtener estado detallado de la sesión"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/sessions/{session_db_id}/status",
            headers=get_headers(),
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                return result.get('data', {})

        return None

    except Exception as e:
        print(f"Error obteniendo estado: {str(e)}")
        return None

def get_qr_with_retry(session_db_id, max_attempts=5):
    """Obtener QR con reintentos y diagnóstico"""
    print(f"\n" + "="*80)
    print(f"📱 OBTENIENDO CÓDIGO QR - SESIÓN {session_db_id}")
    print("="*80)

    for attempt in range(max_attempts):
        print(f"\n🔄 Intento {attempt + 1}/{max_attempts}")

        try:
            response = requests.get(
                f"{API_BASE_URL}/api/sessions/{session_db_id}/qr",
                headers=get_headers(),
                timeout=30
            )

            print(f"📊 Status Code: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print(f"📄 Response: {json.dumps(result, indent=2)[:500]}...")

                if result.get('success'):
                    data = result.get('data', {})
                    qr_code = data.get('qrCode')

                    if qr_code:
                        print(f"✅ QR obtenido exitosamente!")
                        print(f"   Longitud: {len(qr_code)} caracteres")
                        print(f"   Expira: {data.get('expiresAt')}")
                        print(f"   Estado: {data.get('status')}")
                        return qr_code
                    else:
                        print("⚠️  QR vacío en la respuesta")
                else:
                    error_msg = result.get('message', 'Error desconocido')
                    print(f"❌ Error del servidor: {error_msg}")

                    # Diagnóstico específico por tipo de error
                    if 'not found' in error_msg.lower():
                        print("🔍 Diagnóstico: Sesión no encontrada")
                        return None
                    elif 'qr' in error_msg.lower():
                        print("🔍 Diagnóstico: Problema generando QR")
                    elif 'connection' in error_msg.lower():
                        print("🔍 Diagnóstico: Problema de conexión")

            elif response.status_code == 404:
                print("❌ Sesión no encontrada")
                return None
            elif response.status_code == 500:
                print("❌ Error interno del servidor")
                error_data = response.json() if response.text else {}
                print(f"   Error: {error_data.get('error', 'Unknown')}")
            else:
                print(f"❌ Error HTTP {response.status_code}: {response.text}")

        except Exception as e:
            print(f"❌ Excepción: {str(e)}")

        if attempt < max_attempts - 1:
            print("⏳ Esperando 10 segundos antes del siguiente intento...")
            time.sleep(10)

    print("❌ No se pudo obtener el QR después de todos los intentos")
    return None

def diagnose_server_issues():
    """Diagnosticar problemas del servidor"""
    print("\n" + "="*80)
    print("🔍 DIAGNÓSTICO DEL SERVIDOR")
    print("="*80)

    # 1. Verificar salud del servidor
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            print("✅ Servidor accesible")
        else:
            print(f"⚠️  Servidor responde con código {response.status_code}")
    except Exception as e:
        print(f"❌ Servidor no accesible: {str(e)}")
        return False

    # 2. Verificar autenticación
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/sessions",
            headers=get_headers(),
            timeout=10
        )
        if response.status_code == 200:
            print("✅ Autenticación correcta")
        elif response.status_code == 401:
            print("❌ Error de autenticación - API Key inválida")
            return False
        else:
            print(f"⚠️  Respuesta inesperada: {response.status_code}")
    except Exception as e:
        print(f"❌ Error verificando autenticación: {str(e)}")
        return False

    # 3. Verificar límites de rate
    print("🔍 Verificando límites de rate...")
    # Hacer varias peticiones rápidas para verificar rate limiting
    for i in range(3):
        try:
            response = requests.get(
                f"{API_BASE_URL}/api/sessions",
                headers=get_headers(),
                timeout=5
            )
            if response.status_code == 429:
                print("⚠️  Rate limit alcanzado")
                return False
        except:
            pass
        time.sleep(1)

    print("✅ No hay problemas de rate limiting")
    return True

def main():
    """Diagnóstico completo del problema de QR"""
    print("🚀 DIAGNÓSTICO COMPLETO - PROBLEMA DE CÓDIGO QR")
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Paso 1: Diagnosticar servidor
    if not diagnose_server_issues():
        print("\n🚨 PROBLEMA ENCONTRADO: Issues con el servidor")
        return

    # Paso 2: Crear sesión limpia
    session_db_id, session_id = create_fresh_session()
    if not session_db_id:
        print("\n🚨 PROBLEMA ENCONTRADO: No se puede crear sesión")
        return

    # Paso 3: Conectar paso a paso
    if not connect_session_step_by_step(session_db_id):
        print("\n🚨 PROBLEMA ENCONTRADO: No se puede conectar sesión")
        return

    # Paso 4: Obtener QR con diagnóstico
    qr_code = get_qr_with_retry(session_db_id)

    if qr_code:
        print(f"\n✅ ÉXITO: QR obtenido para sesión {session_id}")
        print(f"📱 Puedes usar este QR para conectar WhatsApp")
    else:
        print(f"\n❌ FALLO: No se pudo obtener QR para sesión {session_id}")

        # Diagnóstico final
        print("\n🔍 POSIBLES CAUSAS:")
        print("1. El servidor Baileys puede estar sobrecargado")
        print("2. Problemas de conectividad con WhatsApp")
        print("3. Límites de sesiones alcanzados")
        print("4. Configuración incorrecta del servidor")

        print("\n💡 SOLUCIONES RECOMENDADAS:")
        print("1. Esperar unos minutos y reintentar")
        print("2. Limpiar sesiones antiguas en error")
        print("3. Verificar configuración del servidor Baileys")
        print("4. Contactar al administrador del servidor")

if __name__ == "__main__":
    main()
