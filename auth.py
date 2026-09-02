"""
auth.py — FrostAnalitic
Autenticación y autorización basada en sesión de Flask (cookie firmada
con SECRET_KEY). Tres roles: admin, tecnico, normal.

- 'normal'  → puede diagnosticar y dar retroalimentación (igual que antes,
              incluso sin iniciar sesión).
- 'tecnico' → además puede ver estadísticas detalladas / exportar reportes.
- 'admin'   → además puede editar el árbol de decisiones (panel admin) y
              gestionar usuarios.

No se usa JWT ni tablas de tokens: para el alcance de una tesis, la sesión
de Flask (server-side, cookie httponly) es suficiente y mucho más simple
de mantener.
"""
import os
from functools import wraps
from flask import Blueprint, request, jsonify, session
from models.models import db, Usuario

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

ROLES_VALIDOS = ('admin', 'tecnico', 'normal')


def current_user():
    """Devuelve el Usuario autenticado en la sesión actual, o None."""
    uid = session.get('user_id')
    if not uid:
        return None
    return db.session.get(Usuario, uid)


def login_required(f):
    """Requiere una sesión activa (cualquier rol)."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            return jsonify({'error': 'Necesitas iniciar sesión para esta acción.'}), 401
        return f(*args, **kwargs)
    return wrapper


def roles_required(*roles):
    """Requiere una sesión activa cuyo rol esté en `roles`."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                return jsonify({'error': 'Necesitas iniciar sesión para esta acción.'}), 401
            if user.rol not in roles:
                return jsonify({'error': 'No tienes permiso para esta acción.'}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator


def admin_required(f):
    return roles_required('admin')(f)


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    nombre = (data.get('nombre') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not nombre or not email or not password:
        return jsonify({'error': 'Nombre, email y contraseña son obligatorios.'}), 400
    if len(password) < 6:
        return jsonify({'error': 'La contraseña debe tener al menos 6 caracteres.'}), 400
    if '@' not in email:
        return jsonify({'error': 'Ingresa un email válido.'}), 400
    if Usuario.query.filter_by(email=email).first():
        return jsonify({'error': 'Ese email ya está registrado.'}), 409

    # El autoregistro público siempre crea cuentas 'normal'. Un admin puede
    # luego promover a 'tecnico' o 'admin' desde el panel de administración.
    usuario = Usuario(nombre=nombre, email=email, rol='normal')
    usuario.set_password(password)
    db.session.add(usuario)
    db.session.commit()

    session.clear()
    session['user_id'] = usuario.id
    session.permanent = True
    return jsonify({'usuario': usuario.to_public_dict()}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    usuario = Usuario.query.filter_by(email=email).first()
    if not usuario or not usuario.check_password(password):
        return jsonify({'error': 'Email o contraseña incorrectos.'}), 401
    if not usuario.activo:
        return jsonify({'error': 'Esta cuenta está deshabilitada. Contacta a un administrador.'}), 403

    session.clear()
    session['user_id'] = usuario.id
    session.permanent = True
    return jsonify({'usuario': usuario.to_public_dict()})


@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'ok': True})


@auth_bp.route('/me')
def me():
    usuario = current_user()
    return jsonify({'usuario': usuario.to_public_dict() if usuario else None})


def seed_default_admin():
    """Crea un usuario admin inicial si la tabla 'usuarios' está vacía.
    Se ejecuta una vez al arrancar la app (ver app.py). No hace nada si ya
    existe al menos un usuario, así que es seguro llamarla en cada arranque.
    """
    try:
        if Usuario.query.count() > 0:
            return
    except Exception:
        return  # la tabla todavía no existe (db.create_all la crea antes de esto)

    email = os.environ.get('ADMIN_EMAIL', 'admin@frostanalitic.local')
    password = os.environ.get('ADMIN_PASSWORD', 'admin123')
    admin = Usuario(nombre='Administrador', email=email, rol='admin')
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    print(f'[FrostAnalitic] Usuario admin inicial creado: {email} '
          f'(contraseña definida por la variable de entorno ADMIN_PASSWORD)')
