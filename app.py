"""
FrostAnalitic v2 — app.py
Flask + MySQL con sistema de aprendizaje por retroalimentación.
"""
import os
from flask import Flask, render_template, request, jsonify
from models.models import db, Equipo, Falla, Sesion, Correccion
import json

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def get_database_uri():
    """Resuelve la cadena de conexion a MySQL.
    - En Railway: usa DATABASE_URL (o MYSQL_URL) si Railway la provee,
      o las variables MYSQLHOST/MYSQLUSER/MYSQLPASSWORD/MYSQLDATABASE/MYSQLPORT
      que inyecta el plugin de MySQL.
    - En local: usa DATABASE_URL de tu archivo .env (ver .env.example),
      o LOCAL_DB_PASSWORD como fallback minimo.
    """
    url = os.environ.get('DATABASE_URL') or os.environ.get('MYSQL_URL')
    if url:
        if url.startswith('mysql://'):
            url = url.replace('mysql://', 'mysql+pymysql://', 1)
        return url

    host = os.environ.get('MYSQLHOST')
    if host:
        user = os.environ.get('MYSQLUSER', 'root')
        password = os.environ.get('MYSQLPASSWORD', '')
        port = os.environ.get('MYSQLPORT', '3306')
        database = os.environ.get('MYSQLDATABASE', 'railway')
        return f'mysql+pymysql://{user}:{password}@{host}:{port}/{database}'

    # Fallback SOLO para desarrollo local si no configuraste un .env.
    # Recomendado: copia .env.example a .env y pon ahi tu password real.
    local_password = os.environ.get('LOCAL_DB_PASSWORD', 'changeme')
    return f'mysql+pymysql://root:{local_password}@localhost/frostanalitic'


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# ── Árbol estático (fallback si BD no disponible) ────────────
TREE_STATIC = {
    "Refrigerador": {
        "pregunta": "¿Cuál es el síntoma principal?",
        "opciones": [
            {"texto": "No enfría o enfría poco", "icono": "🌡️",
             "siguiente": {
                 "pregunta": "¿El compresor arranca?",
                 "opciones": [
                     {"texto": "Sí arranca normalmente",
                      "siguiente": {
                          "pregunta": "¿El evaporador tiene escarcha excesiva?",
                          "opciones": [
                              {"texto": "Sí, mucha escarcha",
                               "siguiente": {
                                   "pregunta": "¿El ventilador del evaporador funciona?",
                                   "opciones": [
                                       {"texto": "Sí funciona",
                                        "resultado": {"falla": "Termostato o control de deshielo defectuoso", "prob": 82, "falla_id": 5, "rec": "Verificar ciclos de deshielo. Revisar termostato y calefactor.", "tags": ["Eléctrico","Control"]}},
                                       {"texto": "No funciona",
                                        "resultado": {"falla": "Motor del ventilador del evaporador dañado", "prob": 88, "falla_id": 6, "rec": "Revisar motor del ventilador. Comprobar rodamientos.", "tags": ["Mecánico","Ventilación"]}}
                                   ]
                               }},
                              {"texto": "No, poca o ninguna escarcha",
                               "siguiente": {
                                   "pregunta": "¿Se escucha burbujeo o sonido de gas?",
                                   "opciones": [
                                       {"texto": "Sí, sonido de burbujeo",
                                        "resultado": {"falla": "Fuga de refrigerante", "prob": 91, "falla_id": 1, "rec": "Prueba de presión con nitrógeno. Localizar fuga y recargar.", "tags": ["Refrigerante","Urgente"]}},
                                       {"texto": "No hay sonido",
                                        "resultado": {"falla": "Capilar obstruido o filtro secador saturado", "prob": 79, "falla_id": 2, "rec": "Sustituir filtro secador. Verificar capilar.", "tags": ["Hidráulico"]}}
                                   ]
                               }}
                          ]
                      }},
                     {"texto": "No arranca o intenta arrancar",
                      "siguiente": {
                          "pregunta": "¿Se escucha un clic repetitivo?",
                          "opciones": [
                              {"texto": "Sí, clic repetitivo",
                               "resultado": {"falla": "Relay de arranque o capacitor defectuoso", "prob": 87, "falla_id": 4, "rec": "Reemplazar relay PTC o capacitor de arranque.", "tags": ["Eléctrico","Arranque"]}},
                              {"texto": "No, silencio total",
                               "siguiente": {
                                   "pregunta": "¿Hay voltaje en el tomacorriente?",
                                   "opciones": [
                                       {"texto": "Sí hay voltaje",
                                        "resultado": {"falla": "Compresor defectuoso", "prob": 85, "falla_id": 3, "rec": "Medir devanados. Revisar protector térmico.", "tags": ["Eléctrico","Compresor"]}},
                                       {"texto": "No hay voltaje",
                                        "resultado": {"falla": "Falla eléctrica externa", "prob": 95, "falla_id": 17, "rec": "Revisar fusible y breaker del panel.", "tags": ["Eléctrico","Instalación"]}}
                                   ]
                               }}
                          ]
                      }}
                 ]
             }},
            {"texto": "Hace ruidos anormales", "icono": "🔊",
             "siguiente": {
                 "pregunta": "¿Cómo describe el ruido?",
                 "opciones": [
                     {"texto": "Vibración fuerte o golpeteo", "resultado": {"falla": "Compresor con vibración excesiva", "prob": 76, "falla_id": 3, "rec": "Verificar tornillos de montaje. Revisar aisladores.", "tags": ["Mecánico"]}},
                     {"texto": "Zumbido o quejido agudo", "resultado": {"falla": "Motor del ventilador con rodamientos desgastados", "prob": 83, "falla_id": 18, "rec": "Lubricar o reemplazar motor del ventilador.", "tags": ["Mecánico"]}},
                     {"texto": "Burbujeo o líquido", "resultado": {"falla": "Nivel de refrigerante bajo (fuga parcial)", "prob": 72, "falla_id": 1, "rec": "Verificar nivel de carga. Localizar microfuga.", "tags": ["Refrigerante"]}}
                 ]
             }},
            {"texto": "Forma hielo excesivo en la pared trasera", "icono": "❄️",
             "siguiente": {
                 "pregunta": "¿La puerta cierra perfectamente?",
                 "opciones": [
                     {"texto": "La puerta no sella bien", "resultado": {"falla": "Empaque de puerta deteriorado", "prob": 93, "falla_id": 10, "rec": "Reemplazar empaque de goma.", "tags": ["Sellado","Fácil"]}},
                     {"texto": "La puerta cierra bien", "resultado": {"falla": "Sistema de deshielo automático defectuoso", "prob": 86, "falla_id": 11, "rec": "Verificar resistencia de deshielo y temporizador.", "tags": ["Eléctrico","Deshielo"]}}
                 ]
             }},
            {"texto": "Gotea agua dentro o fuera", "icono": "💧",
             "resultado": {"falla": "Drenaje de deshielo obstruido", "prob": 89, "falla_id": 9, "rec": "Limpiar orificio de drenaje del evaporador.", "tags": ["Hidráulico","Limpieza"]}}
        ]
    },
    "Congelador": {
        "pregunta": "¿Cuál es el síntoma principal?",
        "opciones": [
            {"texto": "No congela o congela poco", "icono": "🌡️",
             "siguiente": {
                 "pregunta": "¿El compresor está funcionando?",
                 "opciones": [
                     {"texto": "Sí, se siente caliente y funciona",
                      "siguiente": {
                          "pregunta": "¿Cuál es la temperatura actual?",
                          "opciones": [
                              {"texto": "Entre 0°C y -10°C", "resultado": {"falla": "Carga baja de refrigerante / fuga parcial", "prob": 84, "falla_id": 1, "rec": "Revisar presiones. Localizar y reparar fuga.", "tags": ["Refrigerante"]}},
                              {"texto": "Más de 0°C (no congela nada)", "resultado": {"falla": "Pérdida total de refrigerante o compresor ineficiente", "prob": 88, "falla_id": 3, "rec": "Diagnóstico completo del sistema.", "tags": ["Sistema","Urgente"]}}
                          ]
                      }},
                     {"texto": "No funciona / no arranca", "resultado": {"falla": "Relay, capacitor o compresor defectuoso", "prob": 86, "falla_id": 4, "rec": "Diagnóstico eléctrico completo.", "tags": ["Eléctrico"]}}
                 ]
             }},
            {"texto": "Se forman bloques de hielo anormales", "icono": "🧊",
             "siguiente": {
                 "pregunta": "¿Dónde se acumula el hielo?",
                 "opciones": [
                     {"texto": "En el evaporador (pared trasera)", "resultado": {"falla": "Sistema de deshielo defectuoso", "prob": 91, "falla_id": 11, "rec": "Reemplazar resistencia de deshielo.", "tags": ["Deshielo"]}},
                     {"texto": "En la tapa o bordes", "resultado": {"falla": "Empaque de puerta deteriorado", "prob": 87, "falla_id": 10, "rec": "Reemplazar empaque. Verificar sellado.", "tags": ["Sellado"]}}
                 ]
             }},
            {"texto": "Consume mucha energía", "icono": "⚡", "resultado": {"falla": "Condensador sucio o ventilación obstruida", "prob": 78, "falla_id": 8, "rec": "Limpiar condensador con compresor de aire.", "tags": ["Limpieza","Eficiencia"]}}
        ]
    },
    "Aire Acondicionado": {
        "pregunta": "¿Cuál es el síntoma principal?",
        "opciones": [
            {"texto": "No enfría", "icono": "🌡️",
             "siguiente": {
                 "pregunta": "¿La unidad exterior enciende?",
                 "opciones": [
                     {"texto": "Sí enciende",
                      "siguiente": {
                          "pregunta": "¿Los filtros están limpios?",
                          "opciones": [
                              {"texto": "Sí están limpios",
                               "siguiente": {
                                   "pregunta": "¿La presión del gas es correcta?",
                                   "opciones": [
                                       {"texto": "Presión baja (con manómetro)", "resultado": {"falla": "Fuga de gas refrigerante", "prob": 90, "falla_id": 1, "rec": "Localizar fuga y recargar R-410A/R-22.", "tags": ["Refrigerante","Urgente"]}},
                                       {"texto": "Presión normal", "resultado": {"falla": "Compresor de baja eficiencia", "prob": 75, "falla_id": 3, "rec": "Revisar eficiencia del compresor.", "tags": ["Compresor"]}}
                                   ]
                               }},
                              {"texto": "No, están sucios", "resultado": {"falla": "Filtros obstruidos", "prob": 97, "falla_id": 13, "rec": "Limpiar o reemplazar filtros.", "tags": ["Limpieza","Fácil"]}}
                          ]
                      }},
                     {"texto": "No enciende",
                      "siguiente": {
                          "pregunta": "¿El control remoto funciona?",
                          "opciones": [
                              {"texto": "Sí funciona", "resultado": {"falla": "Capacitor o compresor exterior dañado", "prob": 82, "falla_id": 4, "rec": "Revisar capacitor del compresor y contactor.", "tags": ["Eléctrico"]}},
                              {"texto": "No responde", "resultado": {"falla": "Tarjeta de control o PCB defectuosa", "prob": 79, "falla_id": 12, "rec": "Reemplazar baterías. Si persiste, revisar PCB.", "tags": ["Electrónico"]}}
                          ]
                      }}
                 ]
             }},
            {"texto": "Gotea agua hacia adentro", "icono": "💧",
             "siguiente": {
                 "pregunta": "¿La instalación tiene más de 3 años?",
                 "opciones": [
                     {"texto": "Sí, instalación antigua", "resultado": {"falla": "Drenaje obstruido por algas/suciedad", "prob": 94, "falla_id": 9, "rec": "Limpiar tubería de drenaje con agua a presión.", "tags": ["Limpieza"]}},
                     {"texto": "No, instalación nueva", "resultado": {"falla": "Instalación incorrecta del drenaje", "prob": 88, "falla_id": 9, "rec": "Verificar pendiente mínima del 2%.", "tags": ["Instalación"]}}
                 ]
             }},
            {"texto": "Hace mucho ruido", "icono": "🔊",
             "siguiente": {
                 "pregunta": "¿El ruido viene de la unidad interior o exterior?",
                 "opciones": [
                     {"texto": "Unidad interior", "resultado": {"falla": "Rodamientos del ventilador interior desgastados", "prob": 80, "falla_id": 18, "rec": "Lubricar o reemplazar motor del ventilador.", "tags": ["Mecánico"]}},
                     {"texto": "Unidad exterior", "resultado": {"falla": "Compresor con vibración o anclaje suelto", "prob": 76, "falla_id": 3, "rec": "Revisar montaje y tornillos del compresor.", "tags": ["Mecánico"]}}
                 ]
             }},
            {"texto": "Display muestra código de error", "icono": "💻",
             "resultado": {"falla": "Error en sensor, tarjeta o comunicación", "prob": 85, "falla_id": 12, "rec": "Anotar código. E1-E5: sensores. F-codes: ventiladores.", "tags": ["Electrónico"]}}
        ]
    },
    "Enfriador Comercial": {
        "pregunta": "¿Cuál es el problema del enfriador?",
        "opciones": [
            {"texto": "No mantiene temperatura", "icono": "🌡️",
             "siguiente": {
                 "pregunta": "¿El compresor funciona?",
                 "opciones": [
                     {"texto": "Sí funciona",
                      "siguiente": {
                          "pregunta": "¿El condensador está limpio?",
                          "opciones": [
                              {"texto": "Sí, limpio", "resultado": {"falla": "Carga de refrigerante baja o fuga", "prob": 83, "falla_id": 1, "rec": "Verificar presiones y recargar sistema.", "tags": ["Refrigerante"]}},
                              {"texto": "No, obstruido", "resultado": {"falla": "Condensador obstruido", "prob": 91, "falla_id": 8, "rec": "Limpiar condensador con aire comprimido.", "tags": ["Limpieza","Urgente"]}}
                          ]
                      }},
                     {"texto": "No funciona", "resultado": {"falla": "Falla eléctrica en compresor o control", "prob": 87, "falla_id": 3, "rec": "Revisar panel, termostato y relay de compresor.", "tags": ["Eléctrico"]}}
                 ]
             }},
            {"texto": "Cristales con mucha humedad", "icono": "💧",
             "siguiente": {
                 "pregunta": "¿Hay resistencias calefactoras en los cristales?",
                 "opciones": [
                     {"texto": "Sí pero no calientan", "resultado": {"falla": "Resistencia anti-vaho defectuosa", "prob": 89, "falla_id": 16, "rec": "Verificar continuidad de resistencias.", "tags": ["Eléctrico"]}},
                     {"texto": "No hay resistencias", "resultado": {"falla": "Falta de resistencias anti-condensación", "prob": 80, "falla_id": 16, "rec": "Instalar resistencias anti-condensación.", "tags": ["Instalación"]}}
                 ]
             }},
            {"texto": "Puertas no sellan bien", "icono": "🚪",
             "resultado": {"falla": "Empaques deteriorados o puerta mal alineada", "prob": 95, "falla_id": 10, "rec": "Reemplazar empaques. Verificar alineación.", "tags": ["Sellado","Fácil"]}}
        ]
    },
    "Cuarto Frío": {
        "pregunta": "¿Cuál es el síntoma del cuarto frío?",
        "opciones": [
            {"texto": "No alcanza temperatura de diseño", "icono": "🌡️",
             "siguiente": {
                 "pregunta": "¿El sistema trabaja continuamente sin parar?",
                 "opciones": [
                     {"texto": "Sí, trabaja sin parar",
                      "siguiente": {
                          "pregunta": "¿Hay filtraciones de aire o paredes dañadas?",
                          "opciones": [
                              {"texto": "Sí hay filtraciones", "resultado": {"falla": "Pérdida de aislamiento térmico", "prob": 88, "falla_id": 14, "rec": "Sellar juntas y reparar paneles de aislamiento.", "tags": ["Aislamiento","Urgente"]}},
                              {"texto": "No, aislamiento parece bien", "resultado": {"falla": "Sistema subdimensionado o carga excesiva", "prob": 76, "falla_id": 1, "rec": "Verificar carga térmica vs capacidad instalada.", "tags": ["Sistema"]}}
                          ]
                      }},
                     {"texto": "Cicla normalmente pero no baja",
                      "siguiente": {
                          "pregunta": "¿El evaporador tiene escarcha excesiva?",
                          "opciones": [
                              {"texto": "Sí, evaporador cubierto de hielo", "resultado": {"falla": "Sistema de deshielo defectuoso", "prob": 92, "falla_id": 11, "rec": "Descongelar manualmente. Revisar resistencias de deshielo.", "tags": ["Deshielo","Urgente"]}},
                              {"texto": "No, evaporador normal", "resultado": {"falla": "Carga insuficiente de refrigerante", "prob": 84, "falla_id": 1, "rec": "Medir presiones. Detectar posible fuga.", "tags": ["Refrigerante"]}}
                          ]
                      }}
                 ]
             }},
            {"texto": "Alto consumo de energía", "icono": "⚡",
             "siguiente": {
                 "pregunta": "¿Cuándo fue la última limpieza del condensador?",
                 "opciones": [
                     {"texto": "Hace más de 6 meses", "resultado": {"falla": "Condensador sucio — alta presión de condensación", "prob": 90, "falla_id": 8, "rec": "Limpiar condensador. Programar mantenimiento trimestral.", "tags": ["Limpieza","Eficiencia"]}},
                     {"texto": "Limpieza reciente", "resultado": {"falla": "Compresor ineficiente o fuga parcial", "prob": 77, "falla_id": 3, "rec": "Medir amperaje del compresor. Verificar presiones.", "tags": ["Compresor"]}}
                 ]
             }},
            {"texto": "Alarmas de temperatura", "icono": "🔔",
             "resultado": {"falla": "Sensor de temperatura defectuoso o mal configurado", "prob": 82, "falla_id": 15, "rec": "Calibrar sensor con termómetro de referencia.", "tags": ["Control"]}}
        ]
    }
}

# ── Rutas ────────────────────────────────────────────────────
@app.route('/')
def home():
    try:
        te = Equipo.query.count()
        tf = Falla.query.count()
        ts = Sesion.query.count()
        ok = Sesion.query.filter_by(fue_correcto=1).count()
        prec = round(ok/ts*100,1) if ts else 0
    except:
        te=tf=ts=prec=0
    return render_template('index.html',
        total_equipos=te, total_fallas=tf,
        total_sesiones=ts, precision=prec)

@app.route('/api/tree/<equipo>')
def api_tree(equipo):
    return jsonify(TREE_STATIC.get(equipo, {}))

@app.route('/api/equipos')
def api_equipos():
    try:
        return jsonify([{'id':e.id,'nombre':e.nombre,'icono':e.icono} for e in Equipo.query.all()])
    except:
        return jsonify([
            {'id':1,'nombre':'Refrigerador','icono':'🧊'},
            {'id':2,'nombre':'Congelador','icono':'🥶'},
            {'id':3,'nombre':'Aire Acondicionado','icono':'💨'},
            {'id':4,'nombre':'Enfriador Comercial','icono':'🏪'},
            {'id':5,'nombre':'Cuarto Frío','icono':'🏭'}
        ])

@app.route('/api/fallas')
def api_fallas():
    try:
        fallas = Falla.query.all()
        return jsonify([{
            'id':f.id,'nombre':f.nombre,'descripcion':f.descripcion,
            'severidad':f.severidad,'equipos_tag':f.equipos_tag,
            'veces':f.veces_diagnosticada,
            'precision': round(f.veces_correcta/f.veces_diagnosticada*100,1) if f.veces_diagnosticada else None
        } for f in fallas])
    except Exception as e:
        return jsonify({'error':str(e)}),500

@app.route('/api/sesion', methods=['POST'])
def api_guardar_sesion():
    data = request.get_json()
    try:
        sesion = Sesion(
            equipo_id=data.get('equipo_id'),
            falla_id=data.get('falla_id'),
            probabilidad=data.get('probabilidad'),
            camino_json=data.get('camino'),
            nivel_usuario=data.get('nivel_usuario','normal')
        )
        db.session.add(sesion)
        f = Falla.query.get(data.get('falla_id'))
        if f: f.veces_diagnosticada += 1
        db.session.commit()
        return jsonify({'sesion_id':sesion.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error':str(e)}),500

@app.route('/api/feedback', methods=['POST'])
def api_feedback():
    data = request.get_json()
    try:
        sesion = Sesion.query.get(data.get('sesion_id'))
        if not sesion: return jsonify({'error':'Sesión no encontrada'}),404
        sesion.fue_correcto = data.get('fue_correcto')
        sesion.falla_real_id = data.get('falla_real_id')
        sesion.nota_usuario = data.get('descripcion_libre')
        if data.get('fue_correcto') and sesion.falla_id:
            f = Falla.query.get(sesion.falla_id)
            if f: f.veces_correcta += 1
        if not data.get('fue_correcto'):
            db.session.add(Correccion(
                sesion_id=data.get('sesion_id'),
                falla_correcta_id=data.get('falla_real_id'),
                descripcion_libre=data.get('descripcion_libre'),
                nivel_usuario=data.get('nivel_usuario','normal')
            ))
        db.session.commit()
        return jsonify({'ok':True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error':str(e)}),500

@app.route('/api/stats')
def api_stats():
    try:
        ts = Sesion.query.count()
        ok = Sesion.query.filter_by(fue_correcto=1).count()
        nok = Sesion.query.filter_by(fue_correcto=0).count()
        fallas = Falla.query.order_by(Falla.veces_diagnosticada.desc()).limit(8).all()
        return jsonify({
            'total_sesiones':ts,'correctas':ok,'incorrectas':nok,
            'sin_feedback':ts-ok-nok,
            'precision_global': round(ok/ts*100,1) if ts else 0,
            'top_fallas':[{
                'nombre':f.nombre,'veces':f.veces_diagnosticada,
                'precision': round(f.veces_correcta/f.veces_diagnosticada*100,1) if f.veces_diagnosticada else 0
            } for f in fallas]
        })
    except Exception as e:
        return jsonify({'error':str(e)}),500

@app.route('/static/graficas/<path:filename>')
def graficas(filename):
    """Sirve las gráficas generadas por ml_model.py desde ds/output/"""
    import os
    from flask import send_from_directory
    graficas_dir = os.path.join(os.path.dirname(__file__), 'ds', 'output')
    return send_from_directory(graficas_dir, filename)

with app.app_context():
    try: db.create_all()
    except: pass

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
