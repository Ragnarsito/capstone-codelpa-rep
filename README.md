# Ciclo Verde Codelpa – Sistema REP Optimizado

## 🌱 Descripción

Sistema simplificado de **Responsabilidad Extendida del Productor (REP)** para el piloto de retorno de baldes de pintura en Codelpa.

El sistema permite:

- Registrar retornos de baldes mediante **códigos QR únicos**.
- Otorgar **puntos y descuentos** a los clientes según sus escaneos.
- Visualizar en escritorio los **escaneos y usuarios activos**.
- Exportar los datos a **CSV** para análisis REP.

Está compuesto por tres módulos:

- **Scanner App Android**: escanea el QR del balde y envía los datos al servidor.
- **Desktop App**: genera QRs seguros para los baldes y muestra estadísticas.
- **Servidor REP (Flask)**: valida los QR, registra escaneos y expone la API + portal web.

---

## 📁 Estructura del proyecto

```text
├── server_rep.py              # Servidor Flask + API + portal web de puntos
├── rep_database.db            # Base de datos SQLite (se crea automáticamente)
├── desktop_app/
│   └── desktop_app.py         # Aplicación de escritorio (dashboard + generador de QR)
├── APP_SCAN/                  # Scanner App Android (Kotlin)
│   ├── app/src/main/java/     # Código Kotlin (CameraX + OkHttp)
│   └── build.gradle           # Configuración Android
├── INICIAR_SISTEMA.bat        # Script para iniciar servidor + desktop app
└── test_scan.py               # Script simple para probar el endpoint /scan
