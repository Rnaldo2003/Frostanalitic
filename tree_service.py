"""
tree_service.py — FrostAnalitic
Construye el árbol de diagnóstico dinámico a partir de las tablas
`nodos` / `opciones` de la base de datos, y calcula la probabilidad
"real" de cada resultado combinando la estimación del experto con la
retroalimentación observada (aprendizaje real, no solo un contador).
"""
from models.models import db, Nodo, Opcion, Falla, Equipo

# Pseudo-conteo del suavizado bayesiano (prior de Beta). Con pocos
# diagnósticos reales, el porcentaje mostrado se queda cerca del que puso
# el experto al diseñar el árbol; a medida que se acumulan más sesiones
# con retroalimentación, el porcentaje se desplaza hacia la tasa de
# aciertos observada de verdad. ALPHA_SUAVIZADO controla qué tan rápido
# ocurre ese desplazamiento (más alto = más conservador / más lento).
ALPHA_SUAVIZADO = 8


def probabilidad_ajustada(prob_experto, falla):
    """Combina prob_experto (0-100, estimación inicial del experto) con
    las estadísticas reales de `falla` (veces_diagnosticada / veces_correcta)
    usando suavizado bayesiano estilo Beta-Binomial:

        posterior = (aciertos_reales + ALPHA * prior) / (n_reales + ALPHA)

    Si la falla nunca se ha diagnosticado todavía, se devuelve tal cual
    la estimación del experto (no hay evidencia real que mezclar aún).
    """
    if prob_experto is None:
        prob_experto = 70
    prior = max(0, min(100, prob_experto)) / 100

    if not falla or not falla.veces_diagnosticada:
        return round(prior * 100, 1)

    n = falla.veces_diagnosticada
    k = falla.veces_correcta or 0
    posterior = (k + ALPHA_SUAVIZADO * prior) / (n + ALPHA_SUAVIZADO)
    return round(posterior * 100, 1)


def _construir_opcion(opcion):
    data = {'id': opcion.id, 'texto': opcion.texto}
    if opcion.icono:
        data['icono'] = opcion.icono

    if opcion.siguiente_nodo:
        siguiente = db.session.get(Nodo, opcion.siguiente_nodo)
        if siguiente and siguiente.activo:
            data['siguiente'] = _construir_nodo(siguiente)
    elif opcion.falla_id:
        falla = db.session.get(Falla, opcion.falla_id)
        data['resultado'] = {
            'falla': falla.nombre if falla else 'Falla desconocida',
            'falla_id': opcion.falla_id,
            'prob': probabilidad_ajustada(opcion.prob_experto, falla),
            'prob_experto': opcion.prob_experto,
            'rec': opcion.rec_text or (falla.descripcion if falla else ''),
            'tags': (falla.equipos_tag.split(',') if falla and falla.equipos_tag else []),
        }
    return data


def _construir_nodo(nodo):
    opciones = (Opcion.query
                .filter_by(nodo_id=nodo.id)
                .order_by(Opcion.orden.asc(), Opcion.id.asc())
                .all())
    return {
        'nodo_id': nodo.id,
        'pregunta': nodo.pregunta,
        'opciones': [_construir_opcion(o) for o in opciones],
    }


def build_tree_from_db(equipo_nombre):
    """Devuelve el árbol dinámico (dict) para el equipo dado, leyendo la
    BD, o None si ese equipo todavía no tiene un nodo raíz migrado (en
    cuyo caso el llamador debe usar el árbol estático de respaldo)."""
    equipo = Equipo.query.filter_by(nombre=equipo_nombre).first()
    if not equipo:
        return None
    raiz = (Nodo.query
            .filter_by(equipo_id=equipo.id, es_raiz=True, activo=True)
            .order_by(Nodo.id.asc())
            .first())
    if not raiz:
        return None
    return _construir_nodo(raiz)
