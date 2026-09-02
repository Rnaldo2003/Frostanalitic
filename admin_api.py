"""
admin_api.py — FrostAnalitic
Panel de administración: CRUD del árbol dinámico (nodos/opciones) y
gestión de usuarios/roles. Todas las rutas requieren rol 'admin'.
"""
from flask import Blueprint, request, jsonify
from models.models import db, Equipo, Falla, Nodo, Opcion, Usuario, Sesion, Correccion, Solucion
from auth import admin_required, current_user
from tree_service import build_tree_from_db

admin_bp = Blueprint('admin_api', __name__, url_prefix='/api/admin')


# ── Equipos ──────────────────────────────────────────────────
@admin_bp.route('/equipos')
@admin_required
def admin_equipos():
    return jsonify([{'id': e.id, 'nombre': e.nombre, 'icono': e.icono} for e in Equipo.query.all()])


@admin_bp.route('/equipos', methods=['POST'])
@admin_required
def crear_equipo():
    data = request.get_json(silent=True) or {}
    nombre = (data.get('nombre') or '').strip()
    if not nombre:
        return jsonify({'error': 'El nombre del equipo es obligatorio.'}), 400
    if Equipo.query.filter_by(nombre=nombre).first():
        return jsonify({'error': 'Ya existe un equipo con ese nombre.'}), 409
    equipo = Equipo(nombre=nombre, icono=(data.get('icono') or '🔧').strip()[:10] or '🔧')
    db.session.add(equipo)
    db.session.commit()
    return jsonify({'id': equipo.id}), 201


@admin_bp.route('/equipos/<int:equipo_id>', methods=['PUT'])
@admin_required
def editar_equipo(equipo_id):
    equipo = db.session.get(Equipo, equipo_id)
    if not equipo:
        return jsonify({'error': 'Equipo no encontrado.'}), 404
    data = request.get_json(silent=True) or {}
    if 'nombre' in data:
        nombre = (data.get('nombre') or '').strip()
        if not nombre:
            return jsonify({'error': 'El nombre no puede quedar vacío.'}), 400
        equipo.nombre = nombre
    if 'icono' in data:
        equipo.icono = (data.get('icono') or '🔧').strip()[:10] or '🔧'
    db.session.commit()
    return jsonify({'ok': True})


@admin_bp.route('/equipos/<int:equipo_id>', methods=['DELETE'])
@admin_required
def eliminar_equipo(equipo_id):
    equipo = db.session.get(Equipo, equipo_id)
    if not equipo:
        return jsonify({'error': 'Equipo no encontrado.'}), 404
    if Nodo.query.filter_by(equipo_id=equipo_id).first() or Sesion.query.filter_by(equipo_id=equipo_id).first():
        return jsonify({'error': 'No se puede borrar: este equipo ya tiene árbol y/o diagnósticos registrados.'}), 409
    db.session.delete(equipo)
    db.session.commit()
    return jsonify({'ok': True})


# ── Fallas ───────────────────────────────────────────────────
@admin_bp.route('/fallas')
@admin_required
def admin_fallas():
    fallas = Falla.query.order_by(Falla.nombre).all()
    return jsonify([{
        'id': f.id, 'nombre': f.nombre, 'descripcion': f.descripcion,
        'severidad': f.severidad, 'equipos_tag': f.equipos_tag,
        'veces_diagnosticada': f.veces_diagnosticada, 'veces_correcta': f.veces_correcta,
    } for f in fallas])


@admin_bp.route('/fallas', methods=['POST'])
@admin_required
def crear_falla():
    data = request.get_json(silent=True) or {}
    nombre = (data.get('nombre') or '').strip()
    if not nombre:
        return jsonify({'error': 'El nombre de la falla es obligatorio.'}), 400
    if data.get('severidad') not in ('baja', 'media', 'alta'):
        return jsonify({'error': 'Severidad inválida (usa baja, media o alta).'}), 400
    falla = Falla(
        nombre=nombre, descripcion=data.get('descripcion'),
        severidad=data.get('severidad'), equipos_tag=data.get('equipos_tag'),
    )
    db.session.add(falla)
    db.session.commit()
    return jsonify({'id': falla.id}), 201


@admin_bp.route('/fallas/<int:falla_id>', methods=['PUT'])
@admin_required
def editar_falla(falla_id):
    falla = db.session.get(Falla, falla_id)
    if not falla:
        return jsonify({'error': 'Falla no encontrada.'}), 404
    data = request.get_json(silent=True) or {}
    if 'nombre' in data:
        nombre = (data.get('nombre') or '').strip()
        if not nombre:
            return jsonify({'error': 'El nombre no puede quedar vacío.'}), 400
        falla.nombre = nombre
    if 'severidad' in data:
        if data['severidad'] not in ('baja', 'media', 'alta'):
            return jsonify({'error': 'Severidad inválida.'}), 400
        falla.severidad = data['severidad']
    for campo in ('descripcion', 'equipos_tag'):
        if campo in data:
            setattr(falla, campo, data[campo])
    db.session.commit()
    return jsonify({'ok': True})


@admin_bp.route('/fallas/<int:falla_id>', methods=['DELETE'])
@admin_required
def eliminar_falla(falla_id):
    falla = db.session.get(Falla, falla_id)
    if not falla:
        return jsonify({'error': 'Falla no encontrada.'}), 404
    en_uso = (Opcion.query.filter_by(falla_id=falla_id).first()
              or Sesion.query.filter_by(falla_id=falla_id).first()
              or Solucion.query.filter_by(falla_id=falla_id).first())
    if en_uso:
        return jsonify({'error': 'No se puede borrar: esta falla ya está en uso en el árbol, soluciones o diagnósticos.'}), 409
    db.session.delete(falla)
    db.session.commit()
    return jsonify({'ok': True})


# ── Árbol: nodos ────────────────────────────────────────────────
@admin_bp.route('/nodos')
@admin_required
def listar_nodos():
    """Lista todos los nodos de un equipo (?equipo_id=) junto con sus
    opciones, para poblar el editor del panel admin."""
    equipo_id = request.args.get('equipo_id', type=int)
    q = Nodo.query
    if equipo_id:
        # Un equipo puede tener nodos "hijos" con equipo_id NULL (solo la
        # raíz guarda equipo_id), así que traemos todos y filtramos luego
        # por alcanzabilidad desde la raíz de ese equipo.
        raiz = Nodo.query.filter_by(equipo_id=equipo_id, es_raiz=True).first()
        if not raiz:
            return jsonify([])
        ids_alcanzables = _ids_alcanzables_desde(raiz.id)
        q = Nodo.query.filter(Nodo.id.in_(ids_alcanzables))
    nodos = q.order_by(Nodo.id).all()
    resultado = []
    for n in nodos:
        opciones = Opcion.query.filter_by(nodo_id=n.id).order_by(Opcion.orden, Opcion.id).all()
        resultado.append({
            'id': n.id, 'equipo_id': n.equipo_id, 'pregunta': n.pregunta,
            'es_raiz': bool(n.es_raiz), 'activo': bool(n.activo),
            'opciones': [_opcion_dict(o) for o in opciones],
        })
    return jsonify(resultado)


def _ids_alcanzables_desde(raiz_id):
    vistos, pendientes = set(), [raiz_id]
    while pendientes:
        actual = pendientes.pop()
        if actual in vistos:
            continue
        vistos.add(actual)
        for op in Opcion.query.filter_by(nodo_id=actual).all():
            if op.siguiente_nodo and op.siguiente_nodo not in vistos:
                pendientes.append(op.siguiente_nodo)
    return list(vistos)


def _opcion_dict(o):
    return {
        'id': o.id, 'nodo_id': o.nodo_id, 'texto': o.texto, 'icono': o.icono,
        'siguiente_nodo': o.siguiente_nodo, 'falla_id': o.falla_id,
        'orden': o.orden, 'prob_experto': o.prob_experto, 'rec_text': o.rec_text,
    }


@admin_bp.route('/nodos', methods=['POST'])
@admin_required
def crear_nodo():
    data = request.get_json(silent=True) or {}
    pregunta = (data.get('pregunta') or '').strip()
    if not pregunta:
        return jsonify({'error': 'La pregunta es obligatoria.'}), 400
    es_raiz = bool(data.get('es_raiz'))
    equipo_id = data.get('equipo_id') if es_raiz else None
    if es_raiz and not equipo_id:
        return jsonify({'error': 'Un nodo raíz necesita un equipo_id.'}), 400
    if es_raiz and Nodo.query.filter_by(equipo_id=equipo_id, es_raiz=True).first():
        return jsonify({'error': 'Ese equipo ya tiene un nodo raíz. Desactívalo o edítalo en vez de crear otro.'}), 409

    nodo = Nodo(equipo_id=equipo_id, pregunta=pregunta, es_raiz=es_raiz, activo=True)
    db.session.add(nodo)
    db.session.commit()
    return jsonify({'id': nodo.id}), 201


@admin_bp.route('/nodos/<int:nodo_id>', methods=['PUT'])
@admin_required
def editar_nodo(nodo_id):
    nodo = db.session.get(Nodo, nodo_id)
    if not nodo:
        return jsonify({'error': 'Nodo no encontrado.'}), 404
    data = request.get_json(silent=True) or {}
    if 'pregunta' in data:
        pregunta = (data.get('pregunta') or '').strip()
        if not pregunta:
            return jsonify({'error': 'La pregunta no puede quedar vacía.'}), 400
        nodo.pregunta = pregunta
    if 'activo' in data:
        nodo.activo = bool(data['activo'])
    db.session.commit()
    return jsonify({'ok': True})


@admin_bp.route('/nodos/<int:nodo_id>', methods=['DELETE'])
@admin_required
def eliminar_nodo(nodo_id):
    nodo = db.session.get(Nodo, nodo_id)
    if not nodo:
        return jsonify({'error': 'Nodo no encontrado.'}), 404
    if nodo.es_raiz:
        return jsonify({'error': 'No se puede borrar un nodo raíz. Desactívalo en su lugar.'}), 400
    # Evita romper el árbol: cualquier opción que apunte a este nodo como
    # "siguiente" queda sin siguiente (se convierte en hoja sin resultado,
    # el admin deberá reasignarla).
    Opcion.query.filter_by(siguiente_nodo=nodo.id).update({'siguiente_nodo': None})
    Opcion.query.filter_by(nodo_id=nodo.id).delete()
    db.session.delete(nodo)
    db.session.commit()
    return jsonify({'ok': True})


# ── Árbol: opciones ─────────────────────────────────────────────
@admin_bp.route('/opciones', methods=['POST'])
@admin_required
def crear_opcion():
    data = request.get_json(silent=True) or {}
    nodo_id = data.get('nodo_id')
    texto = (data.get('texto') or '').strip()
    if not nodo_id or not texto:
        return jsonify({'error': 'nodo_id y texto son obligatorios.'}), 400
    if not db.session.get(Nodo, nodo_id):
        return jsonify({'error': 'El nodo indicado no existe.'}), 404

    error = _validar_destino(data.get('siguiente_nodo'), data.get('falla_id'))
    if error:
        return jsonify({'error': error}), 400

    opcion = Opcion(
        nodo_id=nodo_id, texto=texto, icono=data.get('icono'),
        siguiente_nodo=data.get('siguiente_nodo'), falla_id=data.get('falla_id'),
        orden=data.get('orden', 0), prob_experto=data.get('prob_experto'),
        rec_text=data.get('rec_text'),
    )
    db.session.add(opcion)
    db.session.commit()
    return jsonify({'id': opcion.id}), 201


@admin_bp.route('/opciones/<int:opcion_id>', methods=['PUT'])
@admin_required
def editar_opcion(opcion_id):
    opcion = db.session.get(Opcion, opcion_id)
    if not opcion:
        return jsonify({'error': 'Opción no encontrada.'}), 404
    data = request.get_json(silent=True) or {}

    if 'siguiente_nodo' in data or 'falla_id' in data:
        nuevo_siguiente = data.get('siguiente_nodo', opcion.siguiente_nodo)
        nuevo_falla = data.get('falla_id', opcion.falla_id)
        error = _validar_destino(nuevo_siguiente, nuevo_falla)
        if error:
            return jsonify({'error': error}), 400
        opcion.siguiente_nodo = nuevo_siguiente
        opcion.falla_id = nuevo_falla

    for campo in ('texto', 'icono', 'orden', 'prob_experto', 'rec_text'):
        if campo in data:
            setattr(opcion, campo, data[campo])
    db.session.commit()
    return jsonify({'ok': True})


@admin_bp.route('/opciones/<int:opcion_id>', methods=['DELETE'])
@admin_required
def eliminar_opcion(opcion_id):
    opcion = db.session.get(Opcion, opcion_id)
    if not opcion:
        return jsonify({'error': 'Opción no encontrada.'}), 404
    db.session.delete(opcion)
    db.session.commit()
    return jsonify({'ok': True})


def _validar_destino(siguiente_nodo, falla_id):
    if siguiente_nodo and falla_id:
        return 'Una opción no puede tener a la vez un "siguiente nodo" y una "falla resultado". Elige uno.'
    if not siguiente_nodo and not falla_id:
        return 'Debes indicar un siguiente nodo (para seguir preguntando) o una falla (resultado final).'
    if siguiente_nodo and not db.session.get(Nodo, siguiente_nodo):
        return 'El nodo siguiente indicado no existe.'
    if falla_id and not db.session.get(Falla, falla_id):
        return 'La falla indicada no existe.'
    return None


@admin_bp.route('/preview/<equipo>')
@admin_required
def preview_arbol(equipo):
    """Devuelve el árbol tal como lo vería un usuario, para que el admin
    pueda revisar sus cambios sin salir del panel."""
    arbol = build_tree_from_db(equipo)
    return jsonify(arbol or {})


# ── Usuarios y roles ─────────────────────────────────────────────
@admin_bp.route('/usuarios')
@admin_required
def listar_usuarios():
    usuarios = Usuario.query.order_by(Usuario.id).all()
    return jsonify([{
        **u.to_public_dict(), 'activo': bool(u.activo),
    } for u in usuarios])


@admin_bp.route('/usuarios/<int:usuario_id>', methods=['PUT'])
@admin_required
def editar_usuario(usuario_id):
    usuario = db.session.get(Usuario, usuario_id)
    if not usuario:
        return jsonify({'error': 'Usuario no encontrado.'}), 404
    data = request.get_json(silent=True) or {}
    yo = current_user()
    if usuario.id == yo.id and ('rol' in data and data['rol'] != 'admin' or 'activo' in data and not data['activo']):
        return jsonify({'error': 'No puedes quitarte tu propio rol de admin ni desactivar tu propia cuenta.'}), 400
    if 'rol' in data:
        if data['rol'] not in ('admin', 'tecnico', 'normal'):
            return jsonify({'error': 'Rol inválido.'}), 400
        usuario.rol = data['rol']
    if 'activo' in data:
        usuario.activo = bool(data['activo'])
    db.session.commit()
    return jsonify({'ok': True})


@admin_bp.route('/usuarios/<int:usuario_id>', methods=['DELETE'])
@admin_required
def eliminar_usuario(usuario_id):
    usuario = db.session.get(Usuario, usuario_id)
    if not usuario:
        return jsonify({'error': 'Usuario no encontrado.'}), 404
    if usuario.id == current_user().id:
        return jsonify({'error': 'No puedes eliminar tu propia cuenta.'}), 400
    # No se borran sus diagnósticos anteriores, solo se desvincula el autor.
    Sesion.query.filter_by(usuario_id=usuario.id).update({'usuario_id': None})
    db.session.delete(usuario)
    db.session.commit()
    return jsonify({'ok': True})


# ── Correcciones: moderación de retroalimentación ───────────────
# Cuando un usuario dice "el diagnóstico estaba mal, la falla real era X",
# esa corrección NO se usa para reentrenar la IA en vivo hasta que un
# admin la aprueba aquí (ver ml_service._construir_dataset_real). Así
# evitamos que alguien "envenene" el aprendizaje con datos falsos.
@admin_bp.route('/correcciones')
@admin_required
def listar_correcciones():
    solo_pendientes = request.args.get('pendientes', '1') != '0'
    q = Correccion.query
    if solo_pendientes:
        q = q.filter_by(revisado=False)
    correcciones = q.order_by(Correccion.id.desc()).limit(100).all()

    sesion_ids = [c.sesion_id for c in correcciones]
    sesiones = {s.id: s for s in Sesion.query.filter(Sesion.id.in_(sesion_ids)).all()} if sesion_ids else {}
    fallas = {f.id: f.nombre for f in Falla.query.all()}
    equipos = {e.id: e.nombre for e in Equipo.query.all()}

    resultado = []
    for c in correcciones:
        s = sesiones.get(c.sesion_id)
        resultado.append({
            'id': c.id,
            'sesion_id': c.sesion_id,
            'revisado': bool(c.revisado),
            'equipo': equipos.get(s.equipo_id) if s else None,
            'falla_diagnosticada': fallas.get(s.falla_id) if s else None,
            'falla_correcta_id': c.falla_correcta_id,
            'falla_correcta': fallas.get(c.falla_correcta_id) if c.falla_correcta_id else None,
            'descripcion_libre': c.descripcion_libre,
            'nivel_usuario': c.nivel_usuario,
            'created_at': c.created_at.strftime('%Y-%m-%d %H:%M') if c.created_at else None,
        })
    return jsonify(resultado)


@admin_bp.route('/correcciones/<int:correccion_id>', methods=['PUT'])
@admin_required
def revisar_correccion(correccion_id):
    correccion = db.session.get(Correccion, correccion_id)
    if not correccion:
        return jsonify({'error': 'Corrección no encontrada.'}), 404
    data = request.get_json(silent=True) or {}
    aprobar = bool(data.get('aprobar'))

    ya_estaba_revisada = correccion.revisado
    correccion.revisado = True  # revisado = "ya pasó por un admin", apruebe o rechace

    if aprobar:
        if not ya_estaba_revisada and correccion.falla_correcta_id:
            falla_real = db.session.get(Falla, correccion.falla_correcta_id)
            if falla_real:
                falla_real.veces_diagnosticada = (falla_real.veces_diagnosticada or 0) + 1
                falla_real.veces_correcta = (falla_real.veces_correcta or 0) + 1
    else:
        # Rechazada: se limpia la falla sugerida para que
        # ml_service._construir_dataset_real() (que exige revisado=True
        # Y falla_correcta_id presente) nunca la use para entrenar la IA.
        # La descripción libre se conserva como registro de lo que dijo el usuario.
        correccion.falla_correcta_id = None

    db.session.commit()
    return jsonify({'ok': True, 'aprobada': aprobar})
