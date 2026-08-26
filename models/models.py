from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

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
