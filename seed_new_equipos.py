"""
seed_new_equipos.py — FrostAnalitic
Agrega máquinas/equipos nuevos con su propio árbol de decisiones ya
construido (preguntas + resultados), además de crearlos desde el panel
admin. El admin puede seguir editando estos árboles normalmente desde
Admin → Árbol una vez creados aquí (quedan en las tablas nodos/opciones,
igual que cualquier árbol migrado o creado a mano).

Es SEGURO ejecutarlo varias veces: si un equipo ya existe (por nombre) o ya
tiene un nodo raíz, se omite en vez de duplicar.

Uso:
    python seed_new_equipos.py
"""
from app import app
from models.models import db, Equipo, Falla, Nodo, Opcion


# ── Fallas nuevas que necesitan estos árboles y que el catálogo de 18
#    fallas "de fábrica" no cubre todavía ────────────────────────────
FALLAS_NUEVAS = [
    {
        'nombre': 'Bomba de agua obstruida o dañada',
        'descripcion': 'La bomba que recircula el agua hacia el evaporador de la máquina de hielo está obstruida por sarro/impurezas o dañada mecánicamente.',
        'severidad': 'media',
        'equipos_tag': 'Máquina de Hielo',
    },
    {
        'nombre': 'Filtro de agua saturado o falta de mantenimiento',
        'descripcion': 'El filtro de entrada de agua está saturado, produciendo hielo con sabor u olor extraño.',
        'severidad': 'baja',
        'equipos_tag': 'Máquina de Hielo',
    },
]

# ── Equipos nuevos con su árbol completo ─────────────────────────────
# Los falla_id "fijos" (1,2,3,4,5,6,7,10,16,17) reutilizan el catálogo de
# 18 fallas ya existente (ver schema.sql); los que dicen 'nueva:<nombre>'
# se resuelven contra FALLAS_NUEVAS al momento de sembrar.
EQUIPOS_NUEVOS = [
    {
        'nombre': 'Vitrina Refrigerada',
        'icono': '🥤',
        'arbol': {
            'pregunta': '¿Cuál es el síntoma principal?',
            'opciones': [
                {'texto': 'No enfría lo suficiente', 'icono': '🌡️',
                 'siguiente': {
                     'pregunta': '¿El compresor enciende?',
                     'opciones': [
                         {'texto': 'Sí enciende',
                          'siguiente': {
                              'pregunta': '¿Hay hielo o escarcha excesiva en el evaporador?',
                              'opciones': [
                                  {'texto': 'Sí, bastante escarcha',
                                   'resultado': {'falla_id': 5, 'prob': 80, 'rec': 'Revisar ciclos de deshielo y el termostato de control.', 'tags': ['Eléctrico', 'Control']}},
                                  {'texto': 'No, poca o ninguna',
                                   'resultado': {'falla_id': 1, 'prob': 85, 'rec': 'Prueba de presión y localización de fuga de refrigerante.', 'tags': ['Refrigerante', 'Urgente']}},
                              ],
                          }},
                         {'texto': 'No enciende',
                          'resultado': {'falla_id': 4, 'prob': 84, 'rec': 'Reemplazar relay de arranque o capacitor del compresor.', 'tags': ['Eléctrico', 'Arranque']}},
                     ],
                 }},
                {'texto': 'Las luces LED no encienden', 'icono': '💡',
                 'resultado': {'falla_id': 17, 'prob': 90, 'rec': 'Revisar el circuito de iluminación y el breaker asignado.', 'tags': ['Eléctrico', 'Instalación']}},
                {'texto': 'El vidrio se empaña o suda', 'icono': '💦',
                 'resultado': {'falla_id': 16, 'prob': 88, 'rec': 'Revisar resistencias anti-vaho del marco del vidrio.', 'tags': ['Eléctrico', 'Confort visual']}},
                {'texto': 'Hace ruido fuerte', 'icono': '🔊',
                 'siguiente': {
                     'pregunta': '¿El ruido viene del motor del ventilador?',
                     'opciones': [
                         {'texto': 'Sí, del ventilador',
                          'resultado': {'falla_id': 6, 'prob': 82, 'rec': 'Revisar rodamientos y aspas del motor del ventilador del evaporador.', 'tags': ['Mecánico', 'Ventilación']}},
                         {'texto': 'No, parece el compresor',
                          'resultado': {'falla_id': 3, 'prob': 78, 'rec': 'Revisar montaje y aisladores del compresor. Medir devanados.', 'tags': ['Mecánico', 'Compresor']}},
                     ],
                 }},
            ],
        },
    },
    {
        'nombre': 'Máquina de Hielo',
        'icono': '❄️',
        'arbol': {
            'pregunta': '¿Cuál es el problema principal?',
            'opciones': [
                {'texto': 'No produce hielo', 'icono': '🚫',
                 'siguiente': {
                     'pregunta': '¿El compresor arranca?',
                     'opciones': [
                         {'texto': 'Sí arranca',
                          'siguiente': {
                              'pregunta': '¿Hay flujo de agua hacia el evaporador?',
                              'opciones': [
                                  {'texto': 'Sí hay flujo',
                                   'resultado': {'falla_id': 2, 'prob': 80, 'rec': 'Verificar capilar y filtro secador del circuito de refrigerante.', 'tags': ['Hidráulico']}},
                                  {'texto': 'No hay flujo o es muy débil',
                                   'resultado': {'falla_id': 'nueva:Bomba de agua obstruida o dañada', 'prob': 86, 'rec': 'Limpiar o reemplazar la bomba de recirculación de agua. Revisar sarro.', 'tags': ['Hidráulico', 'Mantenimiento']}},
                              ],
                          }},
                         {'texto': 'No arranca',
                          'resultado': {'falla_id': 4, 'prob': 85, 'rec': 'Reemplazar relay de arranque o capacitor del compresor.', 'tags': ['Eléctrico', 'Arranque']}},
                     ],
                 }},
                {'texto': 'Produce hielo blando o incompleto', 'icono': '🧊',
                 'resultado': {'falla_id': 1, 'prob': 75, 'rec': 'Revisar nivel de carga de refrigerante y buscar microfugas.', 'tags': ['Refrigerante']}},
                {'texto': 'El hielo sale con mal sabor u olor', 'icono': '👃',
                 'resultado': {'falla_id': 'nueva:Filtro de agua saturado o falta de mantenimiento', 'prob': 90, 'rec': 'Reemplazar el filtro de entrada de agua y sanitizar el circuito.', 'tags': ['Mantenimiento', 'Fácil']}},
                {'texto': 'Hace ruido o vibra fuerte', 'icono': '🔊',
                 'resultado': {'falla_id': 7, 'prob': 80, 'rec': 'Revisar motor y aspas del ventilador del condensador.', 'tags': ['Mecánico', 'Ventilación']}},
            ],
        },
    },
]


def _crear_nodo(equipo_id, especificacion, es_raiz=False):
    nodo = Nodo(
        equipo_id=equipo_id if es_raiz else None,
        pregunta=especificacion['pregunta'],
        es_raiz=es_raiz,
        activo=True,
    )
    db.session.add(nodo)
    db.session.flush()

    for orden, opcion_data in enumerate(especificacion.get('opciones', [])):
        opcion = Opcion(
            nodo_id=nodo.id,
            texto=opcion_data['texto'],
            icono=opcion_data.get('icono'),
            orden=orden,
        )
        if 'resultado' in opcion_data:
            r = opcion_data['resultado']
            falla_id = r.get('falla_id')
            if isinstance(falla_id, str) and falla_id.startswith('nueva:'):
                nombre_falla = falla_id.split('nueva:', 1)[1]
                falla = Falla.query.filter_by(nombre=nombre_falla).first()
                falla_id = falla.id if falla else None
            opcion.falla_id = falla_id
            opcion.prob_experto = r.get('prob')
            opcion.rec_text = r.get('rec')
        db.session.add(opcion)
        db.session.flush()

        if 'siguiente' in opcion_data:
            sub_nodo = _crear_nodo(equipo_id, opcion_data['siguiente'], es_raiz=False)
            opcion.siguiente_nodo = sub_nodo.id

    return nodo


def sembrar():
    with app.app_context():
        # 1) Fallas nuevas (idempotente: se omite si ya existe por nombre)
        fallas_creadas = []
        for spec in FALLAS_NUEVAS:
            if Falla.query.filter_by(nombre=spec['nombre']).first():
                continue
            falla = Falla(**spec)
            db.session.add(falla)
            fallas_creadas.append(spec['nombre'])
        db.session.commit()

        # 2) Equipos nuevos + su árbol
        equipos_creados, arboles_creados, omitidos = [], [], []
        for spec in EQUIPOS_NUEVOS:
            equipo = Equipo.query.filter_by(nombre=spec['nombre']).first()
            if not equipo:
                equipo = Equipo(nombre=spec['nombre'], icono=spec['icono'])
                db.session.add(equipo)
                db.session.commit()
                equipos_creados.append(spec['nombre'])

            ya_tiene_raiz = Nodo.query.filter_by(equipo_id=equipo.id, es_raiz=True).first()
            if ya_tiene_raiz:
                omitidos.append(spec['nombre'])
                continue

            _crear_nodo(equipo.id, spec['arbol'], es_raiz=True)
            db.session.commit()
            arboles_creados.append(spec['nombre'])

        print('=' * 55)
        print('  Siembra de equipos nuevos con árbol propio')
        print('=' * 55)
        if fallas_creadas:
            print('Fallas nuevas agregadas:', ', '.join(fallas_creadas))
        if equipos_creados:
            print('Equipos nuevos agregados:', ', '.join(equipos_creados))
        if arboles_creados:
            print('Árboles creados para:', ', '.join(arboles_creados))
        if omitidos:
            print('Ya tenían árbol (omitidos):', ', '.join(omitidos))
        print('\nListo. Estos equipos ya aparecen en /api/equipos y se pueden')
        print('seguir editando desde Admin → Árbol.')


if __name__ == '__main__':
    sembrar()
