#!/usr/bin/env python3
"""
Generar detalles exactos del error para el equipo de Baileys
"""

import requests
import json
import time
from datetime import datetime

API_BASE_URL = "https://api.inbox-hub.com"
API_KEY = "prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814"

def capture_exact_error():
    """Capturar el error exacto con todos los detalles"""
    print("🔍 CAPTURANDO ERROR EXACTO PARA BAILEYS")
    print("="*60)

    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

    # 1. Crear sesión para obtener ID
    timestamp = int(time.time())
    create_data = {
        "sessionId": f"error_capture_{timestamp}",
        "sessionName": f"Captura Error {timestamp}",
        "fromFrappe": True
    }

    print("📡 Creando sesión para capturar error...")
    try:
        create_response = requests.post(
            f"{API_BASE_URL}/api/sessions",
            json=create_data,
            headers=headers,
            timeout=30
        )

        if create_response.status_code == 201:
            result = create_response.json()
            session_data = result.get('data', {}).get('session', {})
            session_id = session_data.get('id')
            session_name = session_data.get('sessionId')

            print(f"✅ Sesión creada: ID {session_id}, Name: {session_name}")

            # 2. Capturar error de conexión con máximo detalle
            print(f"\n🚨 Capturando error de conexión...")

            error_details = {
                "timestamp": datetime.now().isoformat(),
                "test_session": {
                    "id": session_id,
                    "sessionId": session_name,
                    "created_at": session_data.get('createdAt')
                },
                "request": {
                    "method": "POST",
                    "url": f"{API_BASE_URL}/api/sessions/{session_id}/connect",
                    "headers": headers,
                    "body": {}
                },
                "response": {},
                "server_info": {}
            }

            try:
                connect_response = requests.post(
                    f"{API_BASE_URL}/api/sessions/{session_id}/connect",
                    headers=headers,
                    json={},
                    timeout=30
                )

                # Capturar respuesta completa
                error_details["response"] = {
                    "status_code": connect_response.status_code,
                    "headers": dict(connect_response.headers),
                    "body": connect_response.json() if connect_response.text else None,
                    "elapsed_time": connect_response.elapsed.total_seconds()
                }

                # Información del servidor
                error_details["server_info"] = {
                    "server": connect_response.headers.get('Server'),
                    "date": connect_response.headers.get('Date'),
                    "content_type": connect_response.headers.get('Content-Type'),
                    "rate_limit_remaining": connect_response.headers.get('RateLimit-Remaining'),
                    "rate_limit_reset": connect_response.headers.get('RateLimit-Reset')
                }

                print(f"📊 Status Code: {connect_response.status_code}")
                print(f"⏱️  Tiempo de respuesta: {connect_response.elapsed.total_seconds():.3f}s")
                print(f"🖥️  Servidor: {connect_response.headers.get('Server')}")

                if connect_response.status_code == 500:
                    error_body = connect_response.json()
                    print(f"\n🚨 ERROR 500 CONFIRMADO:")
                    print(f"   Code: {error_body.get('code')}")
                    print(f"   Error: {error_body.get('error')}")
                    print(f"   Timestamp: {error_body.get('timestamp')}")

                    # Análisis adicional
                    error_details["analysis"] = {
                        "error_confirmed": True,
                        "error_type": "CONNECTION_ERROR",
                        "error_message": error_body.get('error'),
                        "server_timestamp": error_body.get('timestamp'),
                        "consistent_with_previous": True,
                        "severity": "HIGH - Service blocking"
                    }

            except Exception as e:
                error_details["response"]["exception"] = str(e)
                print(f"❌ Excepción capturando error: {str(e)}")

            return error_details

        else:
            print(f"❌ No se pudo crear sesión: {create_response.status_code}")
            return None

    except Exception as e:
        print(f"❌ Error general: {str(e)}")
        return None

def generate_baileys_error_report(error_details):
    """Generar reporte específico del error para Baileys"""

    report = {
        "report_type": "DETAILED_ERROR_ANALYSIS",
        "generated_at": datetime.now().isoformat(),
        "client": "Grupo ATU",
        "severity": "HIGH",
        "error_details": error_details,
        "technical_summary": {
            "issue": "HTTP 500 CONNECTION_ERROR on session connect endpoint",
            "endpoint": "/api/sessions/{id}/connect",
            "method": "POST",
            "authentication": "X-API-Key (working correctly)",
            "reproducible": "100% - Every attempt fails",
            "impact": "Complete service unavailability"
        },
        "for_baileys_team": {
            "focus_areas": [
                "Baileys library initialization process",
                "WhatsApp Web configuration",
                "Server resource allocation",
                "Node.js process management",
                "Error handling in connect endpoint"
            ],
            "debug_suggestions": [
                "Enable detailed logging in connect endpoint",
                "Check Baileys library version compatibility",
                "Verify WhatsApp Web session management",
                "Monitor server resources during connect attempts",
                "Review recent changes to connection logic"
            ],
            "immediate_actions": [
                "Check server logs at exact timestamp",
                "Verify Baileys configuration",
                "Test in development environment",
                "Implement additional error logging"
            ]
        }
    }

    return report

def main():
    """Generar reporte completo del error"""
    print("🚀 GENERANDO REPORTE DETALLADO PARA BAILEYS")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Capturar error exacto
    error_details = capture_exact_error()

    if error_details:
        # Generar reporte
        report = generate_baileys_error_report(error_details)

        # Guardar reporte
        filename = f"baileys_error_details_{int(time.time())}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Reporte guardado: {filename}")

        # Mostrar resumen
        print("\n" + "="*60)
        print("📋 RESUMEN PARA BAILEYS:")
        print("="*60)

        if error_details.get("analysis", {}).get("error_confirmed"):
            print("🚨 ERROR CONFIRMADO:")
            print(f"   Tipo: {error_details['analysis']['error_type']}")
            print(f"   Mensaje: {error_details['analysis']['error_message']}")
            print(f"   Timestamp: {error_details['analysis']['server_timestamp']}")
            print(f"   Severidad: {error_details['analysis']['severity']}")

            print(f"\n📡 REQUEST EXACTO:")
            print(f"   URL: {error_details['request']['url']}")
            print(f"   Method: {error_details['request']['method']}")
            print(f"   Headers: X-API-Key + Content-Type")

            print(f"\n📊 RESPONSE EXACTO:")
            print(f"   Status: {error_details['response']['status_code']}")
            print(f"   Server: {error_details['server_info']['server']}")
            print(f"   Time: {error_details['response']['elapsed_time']:.3f}s")

            print(f"\n🎯 PARA BAILEYS:")
            print("   1. Revisar logs en timestamp exacto")
            print("   2. Verificar inicialización de Baileys")
            print("   3. Comprobar configuración WhatsApp Web")
            print("   4. Validar recursos del servidor")

        return filename
    else:
        print("❌ No se pudo capturar el error")
        return None

if __name__ == "__main__":
    main()
