#!/usr/bin/env python3
"""
Script de prueba para simular un escaneo de QR
y enviarlo al servidor REP como si fuera la app del teléfono.
"""

import requests
from datetime import datetime
import hashlib
import secrets

# Debe apuntar al mismo servidor donde corre server_rep.py
SERVER_URL = "http://localhost:5000"   # si prefieres, puedes usar "http://192.168.5.53:5000"

# Misma clave secreta que usa desktop_app.py y server_rep.py
QR_SECRET_KEY = "REP_CODELPA_2025_SEGURO"


def generate_secure_qr_code(qr_type: str, identifier: str) -> str:
    """
    Genera un código QR seguro SOLO COMO TEXTO (no imagen),
    usando exactamente el mismo formato que la Desktop App.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = secrets.token_hex(8)

    # Parte central del QR
    qr_content = f"{qr_type}_{identifier}_{timestamp}_{unique_id}"

    # Hash de seguridad
    security_hash = hashlib.sha256(
        f"{qr_content}_{QR_SECRET_KEY}".encode()
    ).hexdigest()[:16]

    # Formato final esperado por el servidor:
    # REP_TYPE_IDENTIFIER_TIMESTAMP_UNIQUE_HASH
    final_qr_code = f"REP_{qr_content}_{security_hash}"
    return final_qr_code


def main():
    # 👇 Cambia esto por el "nombre" del cliente que quieras probar
    user_name = "Cliente Demo"

    # Datos internos del QR (no importan para los puntos, solo para validación)
    qr_type = "TERCEROS"      # o "CODELPA"
    identifier = "LOTE_DEMO"  # identificación del balde/lote

    # Generar QR válido
    qr_code = generate_secure_qr_code(qr_type, identifier)
    print("QR generado (texto):")
    print(qr_code)
    print()

    # Construir payload igual que la app del celular
    payload = {
        "qr_code": qr_code,
        "user_name": user_name
    }

    # 1) Enviar al endpoint /scan
    print("Enviando POST /scan ...")
    r = requests.post(f"{SERVER_URL}/scan", json=payload)
    print("Respuesta /scan:", r.status_code, r.json())
    print()

    # 2) Consultar puntos del mismo usuario
    print(f"Consultando puntos para: {user_name}")
    r2 = requests.get(f"{SERVER_URL}/user/{user_name}")
    print("Respuesta /user:", r2.status_code, r2.json())


if __name__ == "__main__":
    main()
