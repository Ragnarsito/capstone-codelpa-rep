#!/usr/bin/env python3
"""
SERVIDOR REP OPTIMIZADO
Versión limpia para Scanner App y Desktop App
"""

from flask import Flask, request, jsonify, render_template_string, Response
import sqlite3
from datetime import datetime
import os
import hashlib
import csv
import io



app = Flask(__name__)

# Configuración
DATABASE = 'rep_database.db'
QR_SECRET_KEY = "REP_CODELPA_2025_SEGURO"  # Misma clave que Desktop App

POINTS_PER_SCAN = 100  # Por ejemplo: 100 puntos por balde escaneado
SCANS_FOR_REWARD = 7         # escaneos necesarios para beneficio
DISCOUNT_PERCENT = 15        # porcentaje de descuento

def init_database():
    """Inicializa la base de datos"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS qr_scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            qr_code TEXT NOT NULL,
            user_name TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

@app.route('/')
def index():
    """Página principal con estadísticas"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Obtener estadísticas básicas
    cursor.execute('SELECT COUNT(*) FROM qr_scans')
    total_scans = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(DISTINCT user_name) FROM qr_scans')
    total_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT qr_code, user_name, timestamp FROM qr_scans ORDER BY timestamp DESC LIMIT 10')
    recent_scans = cursor.fetchall()
    
    conn.close()
    
    # Template HTML simple
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sistema REP</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 1000px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }
            .header { color: #2E7D32; text-align: center; margin-bottom: 30px; }
            .stats { display: flex; justify-content: space-around; margin: 20px 0; }
            .stat-box { background: #E8F5E8; padding: 20px; border-radius: 8px; text-align: center; min-width: 200px; }
            .stat-number { font-size: 2em; font-weight: bold; color: #2E7D32; }
            .recent-scans { margin-top: 20px; }
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background: #2E7D32; color: white; }
            .export-bar { text-align: right; margin: 10px 0 20px 0; }
            .export-link {
                background:#1565C0;
                color:white;
                padding:8px 14px;
                border-radius:6px;
                text-decoration:none;
                font-size:14px;
                font-weight:bold;
            }
            .export-link:hover { background:#0D47A1; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🌱 Sistema REP</h1>
                <p>Servidor funcionando correctamente</p>
            </div>
            
            <div class="stats">
                <div class="stat-box">
                    <div class="stat-number">{{ total_scans }}</div>
                    <div>QRs Escaneados</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">{{ total_users }}</div>
                    <div>Usuarios Activos</div>
                </div>
            </div>

            <!-- Barra para exportar CSV -->
            <div class="export-bar">
                <a href="/export.csv" class="export-link">
                    ⬇️ Descargar datos (CSV)
                </a>
            </div>
            
            <div class="recent-scans">
                <h3>📱 Escaneos Recientes</h3>
                <table>
                    <tr>
                        <th>Código QR</th>
                        <th>Usuario</th>
                        <th>Fecha</th>
                    </tr>
                    {% for scan in recent_scans %}
                    <tr>
                        <td>{{ scan[0] }}</td>
                        <td>{{ scan[1] }}</td>
                        <td>{{ scan[2] }}</td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
        </div>
    </body>
    </html>
    '''
    
    return render_template_string(html, 
                                total_scans=total_scans, 
                                total_users=total_users, 
                                recent_scans=recent_scans)


def validate_qr_security(qr_code):
    """Validar si el QR es auténtico (generado por Desktop App)"""
    try:
        # Verificar formato REP_
        if not qr_code.startswith("REP_"):
            return False, "QR no generado por sistema autorizado"
            
        # Extraer partes del QR
        parts = qr_code.split("_")
        if len(parts) < 6:  # REP_TYPE_ID_TIMESTAMP_UNIQUE_HASH
            return False, "Formato de QR inválido"
            
        # Extraer hash de seguridad (último elemento)
        provided_hash = parts[-1]
        
        # Reconstruir contenido original sin hash
        content_parts = parts[1:-1]  # Sin "REP_" y sin hash final
        original_content = "_".join(content_parts)
        
        # Recalcular hash esperado
        expected_hash = hashlib.sha256(
            f"{original_content}_{QR_SECRET_KEY}".encode()
        ).hexdigest()[:16]
        
        # Comparar hashes
        if provided_hash == expected_hash:
            qr_type = parts[1]
            identifier = parts[2]
            timestamp = parts[3]
            return True, f"QR válido - {qr_type}: {identifier} ({timestamp})"
        else:
            return False, "QR no autorizado - Hash de seguridad inválido"
            
    except Exception as e:
        return False, f"Error al validar QR: {str(e)}"

@app.route('/scan', methods=['POST'])
def process_scan():
    """Endpoint principal para recibir datos de QR escaneados con validación"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data received"}), 400
        
        qr_code = data.get('qr_code')
        user_name = data.get('user_name')
        
        if not qr_code or not user_name:
            return jsonify({"error": "Missing qr_code or user_name"}), 400
        
        # VALIDAR QR DE SEGURIDAD
        is_valid, validation_message = validate_qr_security(qr_code)
        
        if not is_valid:
            print(f"❌ QR rechazado - Usuario: {user_name}, Razón: {validation_message}")
            return jsonify({
                "error": "QR no autorizado",
                "message": validation_message,
                "status": "rejected"
            }), 403
        
        # Guardar en base de datos (solo QRs válidos)
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO qr_scans (qr_code, user_name, ip_address)
            VALUES (?, ?, ?)
        ''', (qr_code, user_name, request.remote_addr))
        
        scan_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"✅ QR válido escaneado - ID: {scan_id}, Usuario: {user_name}")
        print(f"📋 Validación: {validation_message}")
        
        return jsonify({
            "status": "success",
            "message": "QR code procesado exitosamente",
            "scan_id": scan_id,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/stats')
def stats():
    """API de estadísticas"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM qr_scans')
    total_scans = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(DISTINCT user_name) FROM qr_scans')
    total_users = cursor.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        "total_scans": total_scans,
        "total_users": total_users,
        "server_status": "running"
    })

@app.route('/users')
def users():
    """Lista de usuarios con sus escaneos"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT user_name, COUNT(*) as scan_count, MAX(timestamp) as last_scan
        FROM qr_scans 
        GROUP BY user_name 
        ORDER BY scan_count DESC
    ''')
    
    users = []
    for row in cursor.fetchall():
        users.append({
            "name": row[0],
            "scan_count": row[1],
            "last_scan": row[2]
        })
    
    conn.close()
    return jsonify(users)


@app.route('/user/<user_name>')
def user_detail(user_name):
    """Detalles de un usuario específico + puntos acumulados"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT qr_code, timestamp FROM qr_scans 
        WHERE user_name = ? 
        ORDER BY timestamp DESC
    ''', (user_name,))
    
    scans = []
    for row in cursor.fetchall():
        scans.append({
            "qr_code": row[0],
            "timestamp": row[1]
        })
    
    conn.close()
    
    total_scans = len(scans)
    total_points = total_scans * POINTS_PER_SCAN  # 👈 conversión a puntos
    
    return jsonify({
        "user_name": user_name,
        "total_scans": total_scans,
        "points": total_points,
        "scans": scans
    })

@app.route('/mis-puntos')
def mis_puntos():
    """Página para que el cliente vea sus puntos"""
    html = '''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="utf-8">
        <title>Mis puntos - Sistema REP</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background: #f5f5f5;
                margin: 0;
                padding: 0;
            }
            .container {
                max-width: 700px;
                margin: 40px auto;
                background: white;
                padding: 30px;
                border-radius: 12px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.08);
            }
            h1 {
                text-align: center;
                color: #2E7D32;
                margin-bottom: 10px;
            }
            .subtitle {
                text-align: center;
                color: #555;
                margin-bottom: 25px;
            }
            label {
                font-weight: bold;
                display: block;
                margin-bottom: 8px;
            }
            input[type="text"] {
                width: 100%;
                padding: 10px 12px;
                font-size: 14px;
                border: 1px solid #ccc;
                border-radius: 6px;
                box-sizing: border-box;
            }
            button {
                margin-top: 20px;
                width: 100%;
                padding: 12px;
                font-size: 16px;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                background: #2E7D32;
                color: white;
                cursor: pointer;
            }
            button:hover {
                background: #256628;
            }
            .result-card {
                margin-top: 25px;
                background: #E8F5E8;
                border-radius: 8px;
                padding: 18px 20px;
            }
            .result-card p {
                margin: 4px 0;
            }
            .result-title {
                font-weight: bold;
                margin-bottom: 8px;
            }
            .reward-message {
                margin-top: 10px;
                font-weight: bold;
                color: #1B5E20;
            }
            .thanks-message {
                margin-top: 10px;
                color: #2E7D32;
            }
            .small-info {
                font-size: 13px;
                color: #666;
                margin-top: 6px;
            }
            .error {
                margin-top: 10px;
                color: #c62828;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Mis puntos</h1>
            <p class="subtitle">
                Ingresa tu identificador (el mismo que se usa como <b>nombre de usuario</b>
                al registrar el retorno en tienda).
            </p>

            <form id="pointsForm">
                <label for="clientName">Nombre de cliente:</label>
                <input type="text" id="clientName" placeholder="Ejemplo: Martín Demo" />
                <button type="submit">Ver mis puntos</button>
            </form>

            <div id="errorBox" class="error" style="display:none;"></div>

            <div id="resultCard" class="result-card" style="display:none;">
                <p class="result-title">Resumen de tu participación</p>
                <p><strong>Cliente:</strong> <span id="resClient"></span></p>
                <p><strong>Escaneos realizados:</strong> <span id="resScans"></span></p>
                <p><strong>Puntos acumulados:</strong> <span id="resPoints"></span></p>
                <p><strong>Último escaneo:</strong> <span id="resLastScan"></span></p>

                <p class="reward-message" id="resRewardMsg"></p>
                <p class="thanks-message">
                    Gracias por devolver tus baldes, ¡estás ayudando a reciclar!
                </p>
                <p class="small-info">
                    Cada escaneo suma {{ points_per_scan }} puntos. Con {{ scans_for_reward }} escaneos obtienes un {{ discount_percent }}% de descuento.
                </p>
            </div>
        </div>

        <script>
            const POINTS_PER_SCAN = {{ points_per_scan }};
            const SCANS_FOR_REWARD = {{ scans_for_reward }};
            const DISCOUNT_PERCENT = {{ discount_percent }};

            async function fetchUserData(name) {
                const response = await fetch('/user/' + encodeURIComponent(name));
                if (!response.ok) {
                    throw new Error('Error al consultar el servidor');
                }
                return await response.json();
            }

            function buildRewardMessage(totalScans) {
                if (totalScans === 0) {
                    return `Aún no tienes escaneos registrados. Con ${SCANS_FOR_REWARD} escaneos obtienes un ${DISCOUNT_PERCENT}% de descuento.`;
                }
                if (totalScans < SCANS_FOR_REWARD) {
                    const remaining = SCANS_FOR_REWARD - totalScans;
                    const palabra = remaining === 1 ? 'escaneo' : 'escaneos';
                    return `Te faltan ${remaining} ${palabra} para obtener un ${DISCOUNT_PERCENT}% de descuento.`;
                }
                return `🎉 ¡Felicitaciones! Ya alcanzaste el objetivo de ${SCANS_FOR_REWARD} escaneos. Puedes acceder a un ${DISCOUNT_PERCENT}% de descuento.`;
            }

            document.getElementById('pointsForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const nameInput = document.getElementById('clientName');
                const errorBox = document.getElementById('errorBox');
                const resultCard = document.getElementById('resultCard');

                const clientName = nameInput.value.trim();
                if (!clientName) {
                    errorBox.textContent = 'Por favor ingresa un nombre de cliente.';
                    errorBox.style.display = 'block';
                    resultCard.style.display = 'none';
                    return;
                }

                errorBox.style.display = 'none';

                try {
                    const data = await fetchUserData(clientName);

                    const totalScans = data.total_scans || 0;
                    const points = totalScans * POINTS_PER_SCAN;
                    let lastScan = 'Sin escaneos registrados todavía';

                    if (data.scans && data.scans.length > 0) {
                        lastScan = data.scans[0].timestamp;
                    }

                    document.getElementById('resClient').textContent = clientName;
                    document.getElementById('resScans').textContent = totalScans;
                    document.getElementById('resPoints').textContent = points;
                    document.getElementById('resLastScan').textContent = lastScan;
                    document.getElementById('resRewardMsg').textContent = buildRewardMessage(totalScans);

                    resultCard.style.display = 'block';
                } catch (err) {
                    console.error(err);
                    errorBox.textContent = 'No se pudo obtener la información. Inténtalo nuevamente.';
                    errorBox.style.display = 'block';
                    resultCard.style.display = 'none';
                }
            });
        </script>
    </body>
    </html>
    '''

    return render_template_string(
        html,
        points_per_scan=POINTS_PER_SCAN,
        scans_for_reward=SCANS_FOR_REWARD,
        discount_percent=DISCOUNT_PERCENT
    )


@app.route('/export.csv')
def export_csv():
    """Descargar todos los escaneos en formato CSV"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, qr_code, user_name, timestamp, ip_address
        FROM qr_scans
        ORDER BY timestamp DESC
    ''')
    rows = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)

    # encabezados
    writer.writerow(['id', 'qr_code', 'user_name', 'timestamp', 'ip_address'])
    # datos
    writer.writerows(rows)

    csv_data = output.getvalue()

    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=rep_scans.csv'}
    )



if __name__ == '__main__':
    print("🚀 Iniciando Servidor REP...")
    init_database()
    print("✅ Base de datos inicializada")
    print("🌐 Servidor disponible en puerto 5000 (ej: http://localhost:5000)")
    app.run(host='0.0.0.0', port=5000, debug=True)
