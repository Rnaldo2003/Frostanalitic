"""
FrostAnalitic v3 — app.py
Flask + MySQL con sistema de aprendizaje por retroalimentación, árbol de
decisiones dinámico, autenticación con roles, integración de un modelo de
ML en vivo y exportación de reportes.
"""
import os
from flask import Flask, render_template, request, jsonify, session
from models.models import db, Equipo, Falla, Sesion, Correccion
from tree_static import TREE_STATIC
from tree_service import build_tree_from_db, probabilidad_ajustada

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

# ── Sesión / autenticación ───────────────────────────────────
# En producción define SECRET_KEY en las variables de entorno de Railway;
# el valor de aquí solo es un respaldo cómodo para desarrollo local.
app.secret_key = os.environ.get('SECRET_KEY', 'frostanalitic-dev-secret-cambia-esto')
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'

db.init_app(app)

# ── Blueprints ────────────────────────────────────────────────
from auth import auth_bp, current_user, seed_default_admin
from admin_api import admin_bp
from ml_api import ml_bp
from reports_api import reports_bp

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(ml_bp)
app.register_blueprint(reports_bp)


# ── Árbol: DB dinámica primero, TREE_STATIC como respaldo ────
def _ajustar_arbol_estatico(nodo_spec):
    """Reconstruye (sin mutar el original) un nodo de TREE_STATIC aplicando
    la probabilidad ajustada por retroalimentación real a cada resultado."""
    nuevo = {'pregunta': nodo_spec['pregunta'], 'opciones': []}
    for op in nodo_spec.get('opciones', []):
        nueva_op = {'texto': op['texto']}
        if 'icono' in op:
            nueva_op['icono'] = op['icono']
        if 'siguiente' in op:
            nueva_op['siguiente'] = _ajustar_arbol_estatico(op['siguiente'])
        elif 'resultado' in op:
            r = op['resultado']
            falla = Falla.query.get(r.get('falla_id')) if r.get('falla_id') else None
            nueva_op['resultado'] = {
                'falla': r.get('falla'),
                'falla_id': r.get('falla_id'),
                'prob': probabilidad_ajustada(r.get('prob'), falla),
                'prob_experto': r.get('prob'),
                'rec': r.get('rec'),
                'tags': r.get('tags', []),
            }
        nuevo['opciones'].append(nueva_op)
    return nuevo


def _arbol_para(equipo):
    try:
        arbol_db = build_tree_from_db(equipo)
        if arbol_db:
            return arbol_db
    except Exception:
        pass
    spec = TREE_STATIC.get(equipo)
    if not spec:
        return {}
    try:
        return _ajustar_arbol_estatico(spec)
    except Exception:
        return spec  # si la BD falla al calcular probabilidad, servir el árbol crudo


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
    return jsonify(_arbol_para(equipo))


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
        usuario = current_user()
        sesion = Sesion(
            equipo_id=data.get('equipo_id'),
            falla_id=data.get('falla_id'),
            usuario_id=usuario.id if usuario else None,
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

@app.route('/api/mis-sesiones')
def api_mis_sesiones():
    usuario = current_user()
    if not usuario:
        return jsonify({'error': 'Necesitas iniciar sesión para ver tu historial.'}), 401
    try:
        equipos = {e.id: e.nombre for e in Equipo.query.all()}
        fallas = {f.id: f.nombre for f in Falla.query.all()}
        sesiones = (Sesion.query
                    .filter_by(usuario_id=usuario.id)
                    .order_by(Sesion.id.desc())
                    .limit(50).all())
        return jsonify([{
            'id': s.id,
            'fecha': s.created_at.strftime('%Y-%m-%d %H:%M') if s.created_at else '',
            'equipo': equipos.get(s.equipo_id, '—'),
            'falla': fallas.get(s.falla_id, '—'),
            'probabilidad': s.probabilidad,
            'fue_correcto': s.fue_correcto,
        } for s in sesiones])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
    try:
        db.create_all()
        seed_default_admin()
    except Exception as e:
        print(f'[FrostAnalitic] Aviso al iniciar BD: {e}')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
