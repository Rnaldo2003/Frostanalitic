"""
migrate_tree.py — FrostAnalitic
Migra el árbol de decisiones "de fábrica" (tree_static.TREE_STATIC) hacia
las tablas dinámicas `nodos` / `opciones` de la base de datos, para que el
panel de administración pueda editarlo sin tocar código Python.

Es SEGURO ejecutarlo varias veces: si un equipo ya tiene un nodo raíz
migrado, se omite (no duplica datos). Para forzar una remigración de un
equipo, borra primero sus nodos desde el panel admin (o la BD) y vuelve a
correr este script.

Uso:
    python migrate_tree.py
"""
from app import app
from models.models import db, Equipo, Nodo, Opcion
from tree_static import TREE_STATIC


def _crear_nodo(equipo_id, especificacion, es_raiz=False):
    nodo = Nodo(
        equipo_id=equipo_id if es_raiz else None,
        pregunta=especificacion['pregunta'],
        es_raiz=es_raiz,
        activo=True,
    )
    db.session.add(nodo)
    db.session.flush()  # asigna nodo.id sin hacer commit todavía

    for orden, opcion_data in enumerate(especificacion.get('opciones', [])):
        opcion = Opcion(
            nodo_id=nodo.id,
            texto=opcion_data['texto'],
            icono=opcion_data.get('icono'),
            orden=orden,
        )
        if 'resultado' in opcion_data:
            r = opcion_data['resultado']
            opcion.falla_id = r.get('falla_id')
            opcion.prob_experto = r.get('prob')
            opcion.rec_text = r.get('rec')
        db.session.add(opcion)
        db.session.flush()

        if 'siguiente' in opcion_data:
            sub_nodo = _crear_nodo(equipo_id, opcion_data['siguiente'], es_raiz=False)
            opcion.siguiente_nodo = sub_nodo.id

    return nodo


def migrar():
    with app.app_context():
        migrados, omitidos = [], []
        for nombre_equipo, arbol in TREE_STATIC.items():
            equipo = Equipo.query.filter_by(nombre=nombre_equipo).first()
            if not equipo:
                print(f'  ⚠  Equipo "{nombre_equipo}" no existe en la tabla equipos. Se omite.')
                continue

            ya_migrado = Nodo.query.filter_by(equipo_id=equipo.id, es_raiz=True).first()
            if ya_migrado:
                omitidos.append(nombre_equipo)
                continue

            _crear_nodo(equipo.id, arbol, es_raiz=True)
            db.session.commit()
            migrados.append(nombre_equipo)

        print('=' * 50)
        print('  Migración de árbol estático -> tablas nodos/opciones')
        print('=' * 50)
        if migrados:
            print('Migrados:', ', '.join(migrados))
        if omitidos:
            print('Ya existían (omitidos):', ', '.join(omitidos))
        if not migrados and not omitidos:
            print('Nada que migrar (¿tree_static.py está vacío?).')
        print('\nListo. /api/tree/<equipo> ahora servirá desde la base de datos')
        print('para los equipos migrados, y usará el árbol estático de respaldo')
        print('para los demás.')


if __name__ == '__main__':
    migrar()
