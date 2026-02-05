#!/usr/bin/env python3
"""
Análisis técnico del problema del servidor Baileys
Genera reporte detallado para el equipo técnico.
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

def analyze_server_status():
    """Análisis completo del estado del servidor"""
    print("="*80)
    print("🔍 ANÁLISIS TÉCNICO DEL SERVIDOR BAILEYS")
    print("="*80)

    analysis = {
        "timestamp": datetime.now().isoformat(),
        "server_url": API_BASE_URL,
        "api_key": API_KEY[:20] + "...",
        "tests": []
    }

    # Test 1: Health Check
    print("\n1️⃣ HEALTH CHECK")
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        health_test = {
            "test": "health_check",
            "status_code": response.status_code,
            "response": response.json() if response.text else None,
            "success": response.status_code == 200
        }
        analysis["tests"].append(health_test)

        if health_test["success"]:
            print(f"✅ Servidor accesible - Versión: {health_test['response'].get('version')}")
            print(f"   Entorno: {health_test['response'].get('environment')}")
        else:
            print(f"❌ Health check falló: {response.status_code}")

    except Exception as e:
        health_test = {"test": "health_check", "error": str(e), "success": False}
        analysis["tests"].append(health_test)
        print(f"❌ Error en health check: {str(e)}")

    # Test 2: Autenticación
    print("\n2️⃣ AUTENTICACIÓN")
    try:
        response = requests.get(f"{API_BASE_URL}/api/sessions", headers=get_headers(), timeout=10)
        auth_test = {
            "test": "authentication",
            "status_code": response.status_code,
            "success": response.status_code == 200
        }

        if response.status_code == 200:
            result = response.json()
            auth_test["sessions_count"] = len(result.get("data", {}).get("sessions", []))
            print(f"✅ Autenticación correcta - {auth_test['sessions_count']} sesiones")
        else:
            auth_test["error"] = response.text
            print(f"❌ Error de autenticación: {response.status_code}")

        analysis["tests"].append(auth_test)

    except Exception as e:
        auth_test = {"test": "authentication", "error": str(e), "success": False}
        analysis["tests"].append(auth_test)
        print(f"❌ Error en autenticación: {str(e)}")

    # Test 3: Crear sesión
    print("\n3️⃣ CREACIÓN DE SESIÓN")
    session_test = test_session_creation()
    analysis["tests"].append(session_test)

    if session_test.get("session_id"):
        # Test 4: Conectar sesión (aquí está el problema)
        print("\n4️⃣ CONEXIÓN DE SESIÓN (PROBLEMA IDENTIFICADO)")
        connect_test = test_session_connection(session_test["session_id"])
        analysis["tests"].append(connect_test)

        # Test 5: Obtener QR (depende de la conexión)
        print("\n5️⃣ OBTENCIÓN DE QR")
        qr_test = test_qr_generation(session_test["session_id"])
        analysis["tests"].append(qr_test)

    return analysis

def test_session_creation():
    """Test específico de creación de sesión"""
    timestamp = int(time.time())
    session_id = f"analysis_session_{timestamp}"

    create_data = {
        "sessionId": session_id,
        "sessionName": f"Análisis Técnico {timestamp}",
        "fromFrappe": True
    }

    try:
        response = requests.post(
            f"{API_BASE_URL}/api/sessions",
            json=create_data,
            headers=get_headers(),
            timeout=30
        )

        test_result = {
            "test": "session_creation",
            "status_code": response.status_code,
            "request_data": create_data,
            "success": response.status_code in [200, 201]
        }

        if test_result["success"]:
            result = response.json()
            if result.get('success'):
                session_data = result.get('data', {}).get('session', {})
                test_result["session_id"] = session_data.get('id')
                test_result["session_name"] = session_data.get('sessionId')
                test_result["initial_status"] = session_data.get('status')

                print(f"✅ Sesión creada: ID {test_result['session_id']}")
                print(f"   SessionId: {test_result['session_name']}")
                print(f"   Estado inicial: {test_result['initial_status']}")
            else:
                test_result["error"] = result.get('message')
                print(f"❌ Error en respuesta: {test_result['error']}")
        else:
            test_result["error"] = response.text
            print(f"❌ Error HTTP: {response.status_code}")

        return test_result

    except Exception as e:
        test_result = {
            "test": "session_creation",
            "error": str(e),
            "success": False
        }
        print(f"❌ Excepción: {str(e)}")
        return test_result

def test_session_connection(session_id):
    """Test específico de conexión de sesión - AQUÍ ESTÁ EL PROBLEMA"""
    print(f"🔗 Intentando conectar sesión ID: {session_id}")

    try:
        # Capturar request completo
        url = f"{API_BASE_URL}/api/sessions/{session_id}/connect"
        headers = get_headers()
        body = {}

        print(f"📡 POST {url}")
        print(f"📋 Headers: {json.dumps(headers, indent=2)}")
        print(f"📄 Body: {json.dumps(body, indent=2)}")

        response = requests.post(url, headers=headers, json=body, timeout=30)

        test_result = {
            "test": "session_connection",
            "session_id": session_id,
            "url": url,
            "headers": headers,
            "request_body": body,
            "status_code": response.status_code,
            "response_headers": dict(response.headers),
            "success": response.status_code == 200
        }

        # Capturar respuesta completa
        try:
            test_result["response_body"] = response.json()
        except:
            test_result["response_body"] = response.text

        print(f"📊 Status Code: {response.status_code}")
        print(f"📄 Response: {json.dumps(test_result['response_body'], indent=2)}")

        if response.status_code == 500:
            print("🚨 ERROR 500 CONFIRMADO - PROBLEMA EN EL SERVIDOR")
            test_result["issue_confirmed"] = True
            test_result["issue_type"] = "INTERNAL_SERVER_ERROR"

            # Analizar el error específico
            if isinstance(test_result["response_body"], dict):
                error_code = test_result["response_body"].get("code")
                error_message = test_result["response_body"].get("error")

                test_result["error_code"] = error_code
                test_result["error_message"] = error_message

                print(f"   Código de error: {error_code}")
                print(f"   Mensaje: {error_message}")

                # Diagnóstico específico
                if error_code == "CONNECTION_ERROR":
                    test_result["diagnosis"] = "Error interno del servidor Baileys al inicializar conexión WhatsApp"
                    test_result["likely_cause"] = "Problema con el proceso de inicialización de Baileys o configuración incorrecta"

        return test_result

    except Exception as e:
        test_result = {
            "test": "session_connection",
            "session_id": session_id,
            "error": str(e),
            "success": False
        }
        print(f"❌ Excepción: {str(e)}")
        return test_result

def test_qr_generation(session_id):
    """Test de generación de QR"""
    print(f"📱 Intentando obtener QR para sesión ID: {session_id}")

    try:
        response = requests.get(
            f"{API_BASE_URL}/api/sessions/{session_id}/qr",
            headers=get_headers(),
            timeout=30
        )

        test_result = {
            "test": "qr_generation",
            "session_id": session_id,
            "status_code": response.status_code,
            "success": response.status_code == 200
        }

        try:
            test_result["response_body"] = response.json()
        except:
            test_result["response_body"] = response.text

        print(f"📊 Status Code: {response.status_code}")

        if response.status_code == 500:
            print("🚨 ERROR 500 EN QR - CONSECUENCIA DEL PROBLEMA DE CONEXIÓN")
            test_result["related_to_connection_issue"] = True

        return test_result

    except Exception as e:
        test_result = {
            "test": "qr_generation",
            "session_id": session_id,
            "error": str(e),
            "success": False
        }
        print(f"❌ Excepción: {str(e)}")
        return test_result

def generate_baileys_report(analysis):
    """Generar reporte técnico para el equipo de Baileys"""
    print("\n" + "="*80)
    print("📋 REPORTE TÉCNICO PARA EQUIPO BAILEYS")
    print("="*80)

    report = {
        "issue_summary": "Error 500 'CONNECTION_ERROR' al intentar conectar sesiones WhatsApp",
        "severity": "HIGH - Impide el uso normal del servicio",
        "affected_endpoint": "/api/sessions/{id}/connect",
        "error_details": {},
        "environment": {
            "server_url": API_BASE_URL,
            "api_key": API_KEY[:20] + "...",
            "timestamp": analysis["timestamp"]
        },
        "reproduction_steps": [
            "1. Crear nueva sesión usando POST /api/sessions",
            "2. Intentar conectar usando POST /api/sessions/{id}/connect",
            "3. Servidor devuelve 500 con error 'CONNECTION_ERROR'"
        ],
        "technical_analysis": analysis
    }

    # Extraer detalles del error de conexión
    for test in analysis["tests"]:
        if test.get("test") == "session_connection" and test.get("issue_confirmed"):
            report["error_details"] = {
                "status_code": test.get("status_code"),
                "error_code": test.get("error_code"),
                "error_message": test.get("error_message"),
                "diagnosis": test.get("diagnosis"),
                "likely_cause": test.get("likely_cause")
            }
            break

    # Imprimir reporte
    print("🚨 PROBLEMA CONFIRMADO:")
    print(f"   Endpoint: {report['affected_endpoint']}")
    print(f"   Error: {report['error_details'].get('error_code')} - {report['error_details'].get('error_message')}")
    print(f"   Severidad: {report['severity']}")

    print("\n🔍 DIAGNÓSTICO TÉCNICO:")
    print(f"   {report['error_details'].get('diagnosis')}")
    print(f"   Causa probable: {report['error_details'].get('likely_cause')}")

    print("\n📋 PASOS PARA REPRODUCIR:")
    for step in report["reproduction_steps"]:
        print(f"   {step}")

    print("\n💡 RECOMENDACIONES PARA BAILEYS:")
    print("   1. Revisar logs del servidor en el momento del error")
    print("   2. Verificar configuración de inicialización de Baileys")
    print("   3. Comprobar permisos y recursos del servidor")
    print("   4. Validar configuración de WhatsApp Web")
    print("   5. Revisar límites de conexiones concurrentes")

    return report

def save_report_to_file(report):
    """Guardar reporte en archivo JSON"""
    filename = f"baileys_issue_report_{int(time.time())}.json"

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Reporte guardado en: {filename}")
    return filename

def main():
    """Análisis completo y generación de reporte"""
    print("🚀 ANÁLISIS TÉCNICO COMPLETO - PROBLEMA BAILEYS")
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Realizar análisis completo
    analysis = analyze_server_status()

    # Generar reporte para Baileys
    report = generate_baileys_report(analysis)

    # Guardar reporte
    filename = save_report_to_file(report)

    print("\n" + "="*80)
    print("📞 CONTACTAR AL EQUIPO DE BAILEYS")
    print("="*80)
    print("Enviar este reporte al equipo técnico de Baileys con:")
    print(f"1. El archivo JSON generado: {filename}")
    print("2. Este análisis técnico completo")
    print("3. Solicitud de revisión urgente del endpoint /connect")
    print("\n🎯 MENSAJE PARA BAILEYS:")
    print("'Error 500 CONNECTION_ERROR impide conectar sesiones WhatsApp.'")
    print("'Necesitamos revisión urgente del servidor y configuración.'")

if __name__ == "__main__":
    main()
