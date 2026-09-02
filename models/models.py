from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Equipo(db.Model):
    __tablename__ = 'equipos'
    id     = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    icono  = db.Column(db.String(10), default='🔧')

class Falla(db.Model):
    __tablename__ = 'fallas'
    id          = db.Column(db.Integer, primary_key=True)
    nombre      = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.Text)
    severidad   = db.Column(db.Enum('baja','media','alta'), default='media')
    equipos_tag = db.Column(db.String(200))
    veces_diagnosticada = db.Column(db.Integer, default=0)
    veces_correcta      = db.Column(db.Integer, default=0)

class Solucion(db.Model):
    __tablename__ = 'soluciones'
    id          = db.Column(db.Integer, primary_key=True)
    descripcion = db.Column(db.Text)
    falla_id    = db.Column(db.Integer, db.ForeignKey('fallas.id'))
    tags        = db.Column(db.String(200))

class Sesion(db.Model):
    __tablename__ = 'sesiones'
    id            = db.Column(db.Integer, primary_key=True)
    equipo_id     = db.Column(db.Integer, db.ForeignKey('equipos.id'))
    falla_id      = db.Column(db.Integer, db.ForeignKey('fallas.id'))
    usuario_id    = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    probabilidad  = db.Column(db.Integer)
    camino_json   = db.Column(db.JSON)
    fue_correcto  = db.Column(db.Boolean, default=None)
    falla_real_id = db.Column(db.Integer)
    nota_usuario  = db.Column(db.Text)
    nivel_usuario = db.Column(db.Enum('tecnico','normal'), default='normal')
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

class Correccion(db.Model):
    __tablename__ = 'correcciones'
    id                = db.Column(db.Integer, primary_key=True)
    sesion_id         = db.Column(db.Integer, db.ForeignKey('sesiones.id'))
    falla_correcta_id = db.Column(db.Integer)
    descripcion_libre = db.Column(db.Text)
    nivel_usuario     = db.Column(db.Enum('tecnico','normal'), default='normal')
    revisado          = db.Column(db.Boolean, default=False)
    created_at        = db.Column(db.DateTime, default=datetime.utcnow)

class Nodo(db.Model):
    __tablename__ = 'nodos'
    id         = db.Column(db.Integer, primary_key=True)
    equipo_id  = db.Column(db.Integer, db.ForeignKey('equipos.id'))
    pregunta   = db.Column(db.String(400), nullable=False)
    es_raiz    = db.Column(db.Boolean, default=False)
    activo     = db.Column(db.Boolean, default=True)

class Opcion(db.Model):
    __tablename__ = 'opciones'
    id             = db.Column(db.Integer, primary_key=True)
    nodo_id        = db.Column(db.Integer, db.ForeignKey('nodos.id'))
    texto          = db.Column(db.String(300), nullable=False)
    icono          = db.Column(db.String(10))
    siguiente_nodo = db.Column(db.Integer, db.ForeignKey('nodos.id'))
    falla_id       = db.Column(db.Integer, db.ForeignKey('fallas.id'))
    orden          = db.Column(db.Integer, default=0)
    prob_experto   = db.Column(db.Integer, nullable=True)   # % estimado por el experto para este resultado
    rec_text       = db.Column(db.Text, nullable=True)      # recomendación específica de este camino del árbol


class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id            = db.Column(db.Integer, primary_key=True)
    nombre        = db.Column(db.String(120), nullable=False)
    email         = db.Column(db.String(180), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    rol           = db.Column(db.Enum('admin','tecnico','normal'), default='normal', nullable=False)
    activo        = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def to_public_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'email': self.email,
            'rol': self.rol,
        }
