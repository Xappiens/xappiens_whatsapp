#!/usr/bin/env python3
"""
Script para solucionar problemas de generación de QR
Implementa estrategias de recuperación y alternativas.
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

def clean_error_sessions():
    """Limpiar sesiones en estado de error"""
    print("="*80)
    print("🧹 LIMPIANDO SESIONES EN ERROR")
    print("="*80)

    try:
        # Obtener todas las sesiones
        response = requests.get(
            f"{API_BASE_URL}/api/sessions",
            headers=get_headers(),
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                sessions = result.get('data', {}).get('sessions', [])

                error_sessions = [s for s in sessions if s.get('status') in ['error', 'disconnected']]
                print(f"📊 Encontradas {len(error_sessions)} sesiones en error/desconectadas")

                # Intentar reconectar o eliminar sesiones problemáticas
                for session in error_sessions[:5]:  # Máximo 5 para no sobrecargar
                    session_id = session.get('id')
                    session_name = session.get('sessionId')

                    print(f"\n🔄 Procesando sesión {session_name} (ID: {session_id})")

                    # Intentar eliminar la sesión problemática
                    try:
                        delete_response = requests.delete(
                            f"{API_BASE_URL}/api/sessions/{session_id}",
                            headers=get_headers(),
                            timeout=10
                        )

                        if delete_response.status_code == 200:
                            print(f"   ✅ Sesión eliminada")
                        else:
                            print(f"   ⚠️  No se pudo eliminar: {delete_response.status_code}")

                    except Exception as e:
                        print(f"   ❌ Error eliminando: {str(e)}")

                    time.sleep(2)  # Pausa entre operaciones

                return len(error_sessions)

        return 0

    except Exception as e:
        print(f"❌ Error limpiando sesiones: {str(e)}")
        return 0

def create_session_with_retry(max_attempts=3):
    """Crear sesión con reintentos y diferentes estrategias"""
    print("\n" + "="*80)
    print("🆕 CREANDO SESIÓN CON ESTRATEGIAS DE RECUPERACIÓN")
    print("="*80)

    for attempt in range(max_attempts):
        print(f"\n🔄 Intento {attempt + 1}/{max_attempts}")

        timestamp = int(time.time()) + attempt  # ID único por intento
        session_id = f"recovery_session_{timestamp}"

        # Estrategia diferente por intento
        if attempt == 0:
            # Intento básico
            create_data = {
                "sessionId": session_id,
                "sessionName": f"Sesión Recuperación {timestamp}",
                "fromFrappe": True
            }
        elif attempt == 1:
            # Intento con configuración mínima
            create_data = {
                "sessionId": session_id,
                "sessionName": f"Sesión Mínima {timestamp}"
            }
        else:
            # Intento con configuración extendida
            create_data = {
                "sessionId": session_id,
                "sessionName": f"Sesión Extendida {timestamp}",
                "fromFrappe": True,
                "webhookEvents": ["message"],
                "autoReconnect": True
            }

        print(f"📄 Estrategia {attempt + 1}: {json.dumps(create_data, indent=2)}")

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

                    print(f"✅ Sesión creada exitosamente!")
                    print(f"   ID: {session_db_id}")
                    print(f"   SessionId: {session_id}")

                    return session_db_id, session_id
                else:
                    print(f"❌ Error en respuesta: {result.get('message')}")
            else:
                print(f"❌ Error HTTP: {response.status_code}")
                print(f"   Response: {response.text}")

        except Exception as e:
            print(f"❌ Excepción: {str(e)}")

        if attempt < max_attempts - 1:
            print("⏳ Esperando 10 segundos antes del siguiente intento...")
            time.sleep(10)

    print("❌ No se pudo crear sesión después de todos los intentos")
    return None, None

def connect_with_alternative_methods(session_db_id):
    """Intentar conexión con métodos alternativos"""
    print(f"\n" + "="*80)
    print(f"🔗 CONECTANDO CON MÉTODOS ALTERNATIVOS - SESIÓN {session_db_id}")
    print("="*80)

    methods = [
        {
            "name": "Método estándar",
            "url": f"{API_BASE_URL}/api/sessions/{session_db_id}/connect",
            "method": "POST",
            "body": {}
        },
        {
            "name": "Método con force",
            "url": f"{API_BASE_URL}/api/sessions/{session_db_id}/connect",
            "method": "POST",
            "body": {"force": True}
        },
        {
            "name": "Método con restart",
            "url": f"{API_BASE_URL}/api/sessions/{session_db_id}/restart",
            "method": "POST",
            "body": {}
        }
    ]

    for i, method in enumerate(methods):
        print(f"\n🔄 Probando {method['name']} ({i+1}/{len(methods)})")

        try:
            if method['method'] == 'POST':
                response = requests.post(
                    method['url'],
                    headers=get_headers(),
                    json=method['body'],
                    timeout=30
                )
            else:
                response = requests.get(
                    method['url'],
                    headers=get_headers(),
                    timeout=30
                )

            print(f"📊 Status Code: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print(f"📄 Response: {json.dumps(result, indent=2)[:300]}...")

                if result.get('success'):
                    print(f"✅ {method['name']} exitoso!")
                    return True
                else:
                    print(f"⚠️  {method['name']} - Respuesta: {result.get('message')}")
            elif response.status_code == 404:
                print(f"❌ Endpoint no encontrado para {method['name']}")
            else:
                print(f"❌ Error HTTP {response.status_code} en {method['name']}")

        except Exception as e:
            print(f"❌ Error en {method['name']}: {str(e)}")

        # Pausa entre métodos
        if i < len(methods) - 1:
            time.sleep(5)

    print("❌ Ningún método de conexión funcionó")
    return False

def wait_for_qr_with_polling(session_db_id, max_wait_time=120):
    """Esperar QR con polling inteligente"""
    print(f"\n" + "="*80)
    print(f"⏳ ESPERANDO QR CON POLLING - SESIÓN {session_db_id}")
    print("="*80)

    start_time = time.time()
    attempt = 0

    while time.time() - start_time < max_wait_time:
        attempt += 1
        elapsed = int(time.time() - start_time)

        print(f"\n🔍 Intento {attempt} (Transcurrido: {elapsed}s/{max_wait_time}s)")

        # Verificar estado de la sesión
        try:
            status_response = requests.get(
                f"{API_BASE_URL}/api/sessions/{session_db_id}/status",
                headers=get_headers(),
                timeout=10
            )

            if status_response.status_code == 200:
                status_result = status_response.json()
                if status_result.get('success'):
                    data = status_result.get('data', {})
                    status = data.get('status')
                    has_qr = data.get('hasQR')

                    print(f"   Estado: {status}, Tiene QR: {has_qr}")

                    if status == 'connected':
                        print("✅ Sesión ya conectada!")
                        return True
                    elif status in ['qr_code', 'pending'] or has_qr:
                        print("📱 QR disponible, intentando obtener...")

                        # Intentar obtener QR
                        qr_response = requests.get(
                            f"{API_BASE_URL}/api/sessions/{session_db_id}/qr",
                            headers=get_headers(),
                            timeout=10
                        )

                        if qr_response.status_code == 200:
                            qr_result = qr_response.json()
                            if qr_result.get('success'):
                                qr_data = qr_result.get('data', {})
                                qr_code = qr_data.get('qrCode')

                                if qr_code:
                                    print(f"✅ QR OBTENIDO EXITOSAMENTE!")
                                    print(f"   Longitud: {len(qr_code)} caracteres")
                                    print(f"   Expira: {qr_data.get('expiresAt')}")
                                    return qr_code
                                else:
                                    print("⚠️  QR vacío en respuesta")
                            else:
                                print(f"❌ Error obteniendo QR: {qr_result.get('message')}")
                        else:
                            print(f"❌ Error HTTP obteniendo QR: {qr_response.status_code}")

                    elif status == 'error':
                        print("❌ Sesión en error, abortando")
                        return False
                    else:
                        print(f"⏳ Estado: {status}, continuando...")
            else:
                print(f"❌ Error obteniendo estado: {status_response.status_code}")

        except Exception as e:
            print(f"❌ Error en polling: {str(e)}")

        # Pausa progresiva (más larga conforme pasa el tiempo)
        if attempt <= 5:
            sleep_time = 5
        elif attempt <= 10:
            sleep_time = 10
        else:
            sleep_time = 15

        print(f"⏳ Esperando {sleep_time} segundos...")
        time.sleep(sleep_time)

    print("⏰ Timeout esperando QR")
    return False

def main():
    """Proceso completo de recuperación de QR"""
    print("🚀 PROCESO DE RECUPERACIÓN DE CÓDIGO QR")
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Paso 1: Limpiar sesiones problemáticas
    cleaned_sessions = clean_error_sessions()
    if cleaned_sessions > 0:
        print(f"\n✅ Limpiadas {cleaned_sessions} sesiones problemáticas")
        time.sleep(10)  # Pausa después de la limpieza

    # Paso 2: Crear nueva sesión con reintentos
    session_db_id, session_id = create_session_with_retry()
    if not session_db_id:
        print("\n🚨 FALLO CRÍTICO: No se puede crear sesión")
        return

    # Paso 3: Conectar con métodos alternativos
    if not connect_with_alternative_methods(session_db_id):
        print("\n⚠️  No se pudo conectar, pero continuando con polling...")

    # Paso 4: Esperar QR con polling inteligente
    result = wait_for_qr_with_polling(session_db_id)

    if result:
        if isinstance(result, str):
            print(f"\n🎉 ÉXITO TOTAL: QR obtenido para sesión {session_id}")
            print(f"📱 Longitud del QR: {len(result)} caracteres")
            print(f"🔗 Sesión ID: {session_db_id}")
        else:
            print(f"\n✅ ÉXITO PARCIAL: Sesión {session_id} conectada directamente")
    else:
        print(f"\n❌ FALLO: No se pudo obtener QR para sesión {session_id}")

        print("\n🔍 ANÁLISIS FINAL:")
        print("El problema parece estar en el servidor Baileys:")
        print("1. Error 500 'Error conectando sesión' indica problema interno")
        print("2. Puede ser sobrecarga del servidor o configuración incorrecta")
        print("3. Recomendado contactar al administrador del servidor")

        print("\n💡 SOLUCIONES RECOMENDADAS:")
        print("1. Esperar 30-60 minutos y reintentar")
        print("2. Verificar configuración del servidor Baileys")
        print("3. Revisar logs del servidor para errores específicos")
        print("4. Considerar reiniciar el servicio Baileys")

if __name__ == "__main__":
    main()
