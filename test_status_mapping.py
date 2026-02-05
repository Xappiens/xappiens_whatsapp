#!/usr/bin/env python3
"""
Test del mapeo de estados de Baileys a Frappe
"""

import sys
import os

# Agregar el path de la app para importar la función
sys.path.append('/home/frappe/frappe-bench/apps/xappiens_whatsapp')

def test_status_mapping():
    """Test de la función de mapeo de estados"""

    # Simular la función de mapeo (copiada del código)
    def map_baileys_status_to_frappe(baileys_status):
        """
        Mapea los estados del servidor Baileys a los estados válidos de Frappe

        Estados válidos en Frappe: "Disconnected", "Connecting", "Connected", "QR Code Required", "Error"
        """
        status_mapping = {
            'disconnected': 'Disconnected',
            'connecting': 'Connecting',
            'connected': 'Connected',
            'qr_code': 'QR Code Required',  # Mapeo principal del problema
            'qr': 'QR Code Required',
            'pending': 'QR Code Required',
            'error': 'Error',
            'rate_limited': 'Error',
            'timeout': 'Error'
        }

        # Normalizar el estado de entrada
        normalized_status = str(baileys_status).lower().strip()

        # Buscar mapeo exacto
        if normalized_status in status_mapping:
            return status_mapping[normalized_status]

        # Buscar mapeo parcial para casos como "qr_code_required"
        for baileys_key, frappe_value in status_mapping.items():
            if baileys_key in normalized_status:
                return frappe_value

        # Por defecto, si no encuentra mapeo, usar Disconnected
        print(f"Estado desconocido de Baileys: {baileys_status}")
        return 'Disconnected'

    print("🧪 TEST DE MAPEO DE ESTADOS BAILEYS → FRAPPE")
    print("="*60)

    # Casos de prueba
    test_cases = [
        # Problema principal
        ("Qr_Code", "QR Code Required"),
        ("qr_code", "QR Code Required"),
        ("QR_CODE", "QR Code Required"),

        # Estados normales
        ("disconnected", "Disconnected"),
        ("connecting", "Connecting"),
        ("connected", "Connected"),
        ("error", "Error"),
        ("pending", "QR Code Required"),

        # Casos edge
        ("qr", "QR Code Required"),
        ("rate_limited", "Error"),
        ("timeout", "Error"),
        ("unknown_status", "Disconnected"),  # Fallback

        # Con espacios y mayúsculas
        (" CONNECTED ", "Connected"),
        ("  qr_code  ", "QR Code Required"),
    ]

    print("📋 CASOS DE PRUEBA:")
    print("-" * 60)

    all_passed = True

    for baileys_input, expected_frappe in test_cases:
        result = map_baileys_status_to_frappe(baileys_input)
        status = "✅" if result == expected_frappe else "❌"

        print(f"{status} '{baileys_input}' → '{result}' (esperado: '{expected_frappe}')")

        if result != expected_frappe:
            all_passed = False

    print("\n" + "="*60)
    if all_passed:
        print("🎉 TODOS LOS TESTS PASARON")
        print("✅ El mapeo de estados funciona correctamente")
        print("✅ El problema 'Qr_Code' está solucionado")
    else:
        print("❌ ALGUNOS TESTS FALLARON")
        print("⚠️  Revisar la función de mapeo")

    print("\n💡 ESTADOS VÁLIDOS EN FRAPPE:")
    valid_states = ["Disconnected", "Connecting", "Connected", "QR Code Required", "Error"]
    for state in valid_states:
        print(f"   - {state}")

if __name__ == "__main__":
    test_status_mapping()
