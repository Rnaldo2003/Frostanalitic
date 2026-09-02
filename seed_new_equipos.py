"""
seed_new_equipos.py — FrostAnalitic
Agrega máquinas/equipos nuevos con su propio árbol de decisiones ya
construido (preguntas + resultados), además de crearlos desde el panel
admin. El admin puede seguir editando estos árboles normalmente desde
Admin → Árbol una vez creados aquí (quedan en las tablas nodos/opciones,
igual que cualquier árbol migrado o creado a mano).

Incluye dos grupos de equipos nuevos:
  1) Refrigeración comercial (el dominio original de la tesis): Vitrina
     Refrigerada, Máquina de Hielo.
  2) Línea blanca / electrodomésticos en general, para que el sistema deje
     de limitarse solo a "frost": Lavadora, Secadora, Estufa, Microondas,
     Calentador de Agua.

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
    # ── Lavadora ──────────────────────────────────────────────
    {
        'nombre': 'Interruptor de puerta (switch de seguridad) dañado',
        'descripcion': 'El seguro que detecta la puerta cerrada de la lavadora no cierra el circuito, así que el equipo no arranca.',
        'severidad': 'media', 'equipos_tag': 'Lavadora',
    },
    {
        'nombre': 'Banda (correa) de transmisión floja o rota',
        'descripcion': 'La correa que conecta el motor con el tambor patina o se rompió, así que el motor gira pero el tambor no.',
        'severidad': 'media', 'equipos_tag': 'Lavadora',
    },
    {
        'nombre': 'Motor de la lavadora dañado',
        'descripcion': 'El motor no gira en absoluto: devanado quemado o escobillas desgastadas.',
        'severidad': 'alta', 'equipos_tag': 'Lavadora',
    },
    {
        'nombre': 'Válvula de entrada de agua obstruida o dañada',
        'descripcion': 'La válvula solenoide que deja pasar el agua está sucia o su bobina está dañada.',
        'severidad': 'media', 'equipos_tag': 'Lavadora',
    },
    {
        'nombre': 'Manguera o bomba de desagüe obstruida',
        'descripcion': 'El agua no sale del tambor al final del ciclo por un objeto atascado o la bomba de desagüe dañada.',
        'severidad': 'media', 'equipos_tag': 'Lavadora',
    },
    {
        'nombre': 'Amortiguadores o resortes de suspensión desgastados',
        'descripcion': 'El tambor vibra o golpea las paredes del gabinete durante el centrifugado.',
        'severidad': 'media', 'equipos_tag': 'Lavadora',
    },
    {
        'nombre': 'Empaque o manguera deteriorado (fuga de agua)',
        'descripcion': 'Sellos de puerta o conexiones de manguera desgastados que dejan salir agua.',
        'severidad': 'baja', 'equipos_tag': 'Lavadora',
    },
    # ── Secadora ──────────────────────────────────────────────
    {
        'nombre': 'Interruptor de puerta o termofusible dañado',
        'descripcion': 'El switch de puerta o el fusible térmico de seguridad de la secadora está abierto/dañado.',
        'severidad': 'media', 'equipos_tag': 'Secadora',
    },
    {
        'nombre': 'Resistencia (elemento calefactor) quemada',
        'descripcion': 'El elemento que genera el calor de secado está quemado; el tambor gira pero sale aire frío.',
        'severidad': 'alta', 'equipos_tag': 'Secadora',
    },
    {
        'nombre': 'Motor o banda del tambor de la secadora dañada',
        'descripcion': 'El tambor no gira: motor dañado o banda de transmisión rota.',
        'severidad': 'alta', 'equipos_tag': 'Secadora',
    },
    {
        'nombre': 'Ducto de ventilación obstruido con pelusa',
        'descripcion': 'El ducto de salida de aire está tapado con pelusa, alargando mucho el tiempo de secado.',
        'severidad': 'media', 'equipos_tag': 'Secadora',
    },
    {
        'nombre': 'Rodillos o rodamientos del tambor desgastados',
        'descripcion': 'Piezas de soporte del tambor desgastadas que producen ruido o chirrido al girar.',
        'severidad': 'media', 'equipos_tag': 'Secadora',
    },
    {
        'nombre': 'Sensor de temperatura o termostato de seguridad defectuoso (secadora)',
        'descripcion': 'Corta el ciclo antes de tiempo por una lectura de temperatura incorrecta.',
        'severidad': 'media', 'equipos_tag': 'Secadora',
    },
    # ── Estufa / Cocina ───────────────────────────────────────
    {
        'nombre': 'Boquilla del quemador obstruida o válvula de gas dañada',
        'descripcion': 'Un quemador de gas no enciende por boquilla tapada o válvula individual defectuosa.',
        'severidad': 'media', 'equipos_tag': 'Estufa',
    },
    {
        'nombre': 'Resistencia (hornilla eléctrica) quemada',
        'descripcion': 'Una hornilla eléctrica no calienta porque su resistencia está quemada.',
        'severidad': 'media', 'equipos_tag': 'Estufa',
    },
    {
        'nombre': 'Termostato del horno descalibrado',
        'descripcion': 'El horno enciende pero la temperatura real no corresponde a la marcada en la perilla.',
        'severidad': 'media', 'equipos_tag': 'Estufa',
    },
    {
        'nombre': 'Resistencia o quemador del horno dañado',
        'descripcion': 'El horno no calienta en absoluto: resistencia eléctrica quemada o quemador de gas del horno dañado.',
        'severidad': 'alta', 'equipos_tag': 'Estufa',
    },
    {
        'nombre': 'Módulo o bujía de encendido dañado',
        'descripcion': 'El sistema de encendido eléctrico (chispa) de una estufa a gas no enciende la llama.',
        'severidad': 'media', 'equipos_tag': 'Estufa',
    },
    {
        'nombre': 'Sensor de temperatura del horno defectuoso',
        'descripcion': 'El horno no mantiene una temperatura constante durante la cocción.',
        'severidad': 'media', 'equipos_tag': 'Estufa',
    },
    {
        'nombre': 'Fuga de gas en instalación o válvula',
        'descripcion': 'Olor a gas detectado en la instalación de una estufa o calentador de agua a gas. Riesgo de seguridad: requiere revisión inmediata.',
        'severidad': 'alta', 'equipos_tag': 'Estufa,Calentador de Agua',
    },
    # ── Microondas ────────────────────────────────────────────
    {
        'nombre': 'Fusible interno del microondas quemado',
        'descripcion': 'El microondas no enciende ni el display, pero hay corriente en el tomacorriente.',
        'severidad': 'media', 'equipos_tag': 'Microondas',
    },
    {
        'nombre': 'Magnetrón dañado',
        'descripcion': 'El microondas enciende y el plato gira, pero no calienta la comida.',
        'severidad': 'alta', 'equipos_tag': 'Microondas',
    },
    {
        'nombre': 'Motor del plato giratorio dañado',
        'descripcion': 'El plato giratorio no gira, aunque el microondas sí calienta.',
        'severidad': 'baja', 'equipos_tag': 'Microondas',
    },
    {
        'nombre': 'Guía de ondas o mica dañada',
        'descripcion': 'Chispas o ruidos extraños dentro de la cavidad, normalmente por la mica quemada o restos de comida carbonizados.',
        'severidad': 'media', 'equipos_tag': 'Microondas',
    },
    {
        'nombre': 'Interruptores de seguridad de la puerta dañados (microondas)',
        'descripcion': 'El microondas no enciende con la puerta cerrada, o la puerta no cierra bien.',
        'severidad': 'media', 'equipos_tag': 'Microondas',
    },
    {
        'nombre': 'Panel de control o placa electrónica dañada (microondas)',
        'descripcion': 'Los botones o el panel táctil no responden.',
        'severidad': 'alta', 'equipos_tag': 'Microondas',
    },
    # ── Calentador de agua ────────────────────────────────────
    {
        'nombre': 'Piloto apagado o termopar dañado',
        'descripcion': 'El calentador de agua a gas no calienta porque el piloto está apagado o el termopar de seguridad está dañado.',
        'severidad': 'media', 'equipos_tag': 'Calentador de Agua',
    },
    {
        'nombre': 'Resistencia eléctrica del calentador quemada',
        'descripcion': 'El calentador de agua eléctrico no calienta: resistencia sumergida quemada.',
        'severidad': 'media', 'equipos_tag': 'Calentador de Agua',
    },
    {
        'nombre': 'Sedimento acumulado en el tanque',
        'descripcion': 'Cal/sarro acumulado en el fondo del tanque reduce la eficiencia y el agua sale tibia en vez de caliente.',
        'severidad': 'media', 'equipos_tag': 'Calentador de Agua',
    },
    {
        'nombre': 'Válvula de alivio de presión o tanque corroído',
        'descripcion': 'Fuga de agua visible en el calentador: válvula de alivio defectuosa o corrosión del tanque.',
        'severidad': 'alta', 'equipos_tag': 'Calentador de Agua',
    },
    {
        'nombre': 'Acumulación de sarro en la resistencia o serpentín',
        'descripcion': 'Ruido de golpeteo o silbido durante el calentamiento por sarro adherido a la resistencia/serpentín.',
        'severidad': 'media', 'equipos_tag': 'Calentador de Agua',
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
    {
        'nombre': 'Lavadora',
        'icono': '🧺',
        'arbol': {
            'pregunta': '¿Cuál es el síntoma principal?',
            'opciones': [
                {'texto': 'No enciende', 'icono': '🚫',
                 'siguiente': {
                     'pregunta': '¿Hay corriente en el tomacorriente?',
                     'opciones': [
                         {'texto': 'Sí hay corriente',
                          'resultado': {'falla_id': 'nueva:Interruptor de puerta (switch de seguridad) dañado', 'prob': 82, 'rec': 'Revisar el switch de seguridad de la puerta y su continuidad.', 'tags': ['Eléctrico', 'Seguridad']}},
                         {'texto': 'No hay corriente',
                          'resultado': {'falla_id': 17, 'prob': 90, 'rec': 'Revisar fusibles del tablero y el breaker asignado.', 'tags': ['Eléctrico', 'Instalación']}},
                     ],
                 }},
                {'texto': 'No centrifuga o no gira el tambor', 'icono': '🌀',
                 'siguiente': {
                     'pregunta': '¿Se escucha el motor intentando girar?',
                     'opciones': [
                         {'texto': 'Sí, intenta pero no gira',
                          'resultado': {'falla_id': 'nueva:Banda (correa) de transmisión floja o rota', 'prob': 84, 'rec': 'Revisar tensión y estado de la banda de transmisión.', 'tags': ['Mecánico']}},
                         {'texto': 'No, silencio total',
                          'resultado': {'falla_id': 'nueva:Motor de la lavadora dañado', 'prob': 80, 'rec': 'Medir devanados del motor. Revisar escobillas.', 'tags': ['Eléctrico', 'Motor']}},
                     ],
                 }},
                {'texto': 'No llena de agua o llena muy lento', 'icono': '🚰',
                 'resultado': {'falla_id': 'nueva:Válvula de entrada de agua obstruida o dañada', 'prob': 78, 'rec': 'Limpiar filtro de la válvula de entrada. Verificar bobina solenoide.', 'tags': ['Hidráulico']}},
                {'texto': 'No desagua o deja agua estancada', 'icono': '💧',
                 'resultado': {'falla_id': 'nueva:Manguera o bomba de desagüe obstruida', 'prob': 85, 'rec': 'Revisar manguera de desagüe y limpiar la bomba.', 'tags': ['Hidráulico']}},
                {'texto': 'Hace ruido fuerte o vibra excesivo', 'icono': '🔊',
                 'resultado': {'falla_id': 'nueva:Amortiguadores o resortes de suspensión desgastados', 'prob': 76, 'rec': 'Revisar amortiguadores/resortes de suspensión del tambor.', 'tags': ['Mecánico']}},
                {'texto': 'Presenta fuga de agua', 'icono': '💦',
                 'resultado': {'falla_id': 'nueva:Empaque o manguera deteriorado (fuga de agua)', 'prob': 88, 'rec': 'Revisar empaques de puerta y conexiones de manguera.', 'tags': ['Sellado', 'Fácil']}},
            ],
        },
    },
    {
        'nombre': 'Secadora',
        'icono': '🌀',
        'arbol': {
            'pregunta': '¿Cuál es el síntoma principal?',
            'opciones': [
                {'texto': 'No enciende', 'icono': '🚫',
                 'siguiente': {
                     'pregunta': '¿Hay corriente en el tomacorriente?',
                     'opciones': [
                         {'texto': 'Sí hay corriente',
                          'resultado': {'falla_id': 'nueva:Interruptor de puerta o termofusible dañado', 'prob': 80, 'rec': 'Revisar switch de puerta y fusible térmico de seguridad.', 'tags': ['Eléctrico', 'Seguridad']}},
                         {'texto': 'No hay corriente',
                          'resultado': {'falla_id': 17, 'prob': 90, 'rec': 'Revisar fusibles del tablero y el breaker asignado.', 'tags': ['Eléctrico', 'Instalación']}},
                     ],
                 }},
                {'texto': 'Enciende pero no calienta', 'icono': '🌡️',
                 'siguiente': {
                     'pregunta': '¿El tambor gira normalmente?',
                     'opciones': [
                         {'texto': 'Sí gira',
                          'resultado': {'falla_id': 'nueva:Resistencia (elemento calefactor) quemada', 'prob': 86, 'rec': 'Medir continuidad de la resistencia calefactora. Reemplazar.', 'tags': ['Eléctrico', 'Calor']}},
                         {'texto': 'No gira',
                          'resultado': {'falla_id': 'nueva:Motor o banda del tambor de la secadora dañada', 'prob': 82, 'rec': 'Revisar motor y banda de transmisión del tambor.', 'tags': ['Mecánico']}},
                     ],
                 }},
                {'texto': 'Tarda demasiado en secar', 'icono': '⏳',
                 'resultado': {'falla_id': 'nueva:Ducto de ventilación obstruido con pelusa', 'prob': 88, 'rec': 'Limpiar ducto de ventilación y filtro de pelusa.', 'tags': ['Mantenimiento', 'Fácil']}},
                {'texto': 'Hace ruido fuerte o chirrido', 'icono': '🔊',
                 'resultado': {'falla_id': 'nueva:Rodillos o rodamientos del tambor desgastados', 'prob': 79, 'rec': 'Revisar rodillos/rodamientos de soporte del tambor.', 'tags': ['Mecánico']}},
                {'texto': 'Se detiene sola a mitad de ciclo', 'icono': '⏸️',
                 'resultado': {'falla_id': 'nueva:Sensor de temperatura o termostato de seguridad defectuoso (secadora)', 'prob': 75, 'rec': 'Revisar sensor de temperatura y termostato de seguridad.', 'tags': ['Control', 'Electrónico']}},
            ],
        },
    },
    {
        'nombre': 'Estufa',
        'icono': '🔥',
        'arbol': {
            'pregunta': '¿Cuál es el síntoma principal?',
            'opciones': [
                {'texto': 'Un quemador (hornilla) no enciende', 'icono': '🔥',
                 'siguiente': {
                     'pregunta': '¿Es una estufa de gas o eléctrica?',
                     'opciones': [
                         {'texto': 'De gas',
                          'resultado': {'falla_id': 'nueva:Boquilla del quemador obstruida o válvula de gas dañada', 'prob': 80, 'rec': 'Limpiar boquilla del quemador. Revisar válvula individual.', 'tags': ['Gas', 'Limpieza']}},
                         {'texto': 'Eléctrica',
                          'resultado': {'falla_id': 'nueva:Resistencia (hornilla eléctrica) quemada', 'prob': 84, 'rec': 'Medir continuidad de la resistencia. Reemplazar hornilla.', 'tags': ['Eléctrico']}},
                     ],
                 }},
                {'texto': 'El horno no calienta o calienta poco', 'icono': '🌡️',
                 'siguiente': {
                     'pregunta': '¿Se enciende la llama o resistencia del horno?',
                     'opciones': [
                         {'texto': 'Sí enciende',
                          'resultado': {'falla_id': 'nueva:Termostato del horno descalibrado', 'prob': 78, 'rec': 'Calibrar termostato con termómetro de referencia.', 'tags': ['Control']}},
                         {'texto': 'No enciende',
                          'resultado': {'falla_id': 'nueva:Resistencia o quemador del horno dañado', 'prob': 85, 'rec': 'Revisar resistencia eléctrica o quemador de gas del horno.', 'tags': ['Eléctrico', 'Gas']}},
                     ],
                 }},
                {'texto': 'Huele a gas', 'icono': '👃',
                 'resultado': {'falla_id': 'nueva:Fuga de gas en instalación o válvula', 'prob': 95, 'rec': 'Cerrar la llave de paso de inmediato y ventilar. Revisión profesional urgente.', 'tags': ['Gas', 'Urgente']}},
                {'texto': 'El piloto/encendido eléctrico no hace chispa', 'icono': '⚡',
                 'resultado': {'falla_id': 'nueva:Módulo o bujía de encendido dañado', 'prob': 77, 'rec': 'Revisar módulo o bujía de encendido eléctrico.', 'tags': ['Eléctrico', 'Encendido']}},
                {'texto': 'El horno no mantiene temperatura constante', 'icono': '📉',
                 'resultado': {'falla_id': 'nueva:Sensor de temperatura del horno defectuoso', 'prob': 76, 'rec': 'Revisar sensor de temperatura del horno.', 'tags': ['Control', 'Electrónico']}},
            ],
        },
    },
    {
        'nombre': 'Microondas',
        'icono': '📡',
        'arbol': {
            'pregunta': '¿Cuál es el síntoma principal?',
            'opciones': [
                {'texto': 'No enciende ni el display', 'icono': '🚫',
                 'siguiente': {
                     'pregunta': '¿Hay corriente en el tomacorriente?',
                     'opciones': [
                         {'texto': 'Sí hay corriente',
                          'resultado': {'falla_id': 'nueva:Fusible interno del microondas quemado', 'prob': 83, 'rec': 'Revisar y reemplazar el fusible interno.', 'tags': ['Eléctrico']}},
                         {'texto': 'No hay corriente',
                          'resultado': {'falla_id': 17, 'prob': 90, 'rec': 'Revisar fusibles del tablero y el breaker asignado.', 'tags': ['Eléctrico', 'Instalación']}},
                     ],
                 }},
                {'texto': 'Enciende pero no calienta', 'icono': '🌡️',
                 'siguiente': {
                     'pregunta': '¿Gira el plato giratorio?',
                     'opciones': [
                         {'texto': 'Sí gira',
                          'resultado': {'falla_id': 'nueva:Magnetrón dañado', 'prob': 87, 'rec': 'Diagnóstico y reemplazo del magnetrón por un técnico calificado.', 'tags': ['Electrónico', 'Alta tensión']}},
                         {'texto': 'No gira',
                          'resultado': {'falla_id': 'nueva:Motor del plato giratorio dañado', 'prob': 72, 'rec': 'Revisar motor del plato giratorio.', 'tags': ['Mecánico', 'Fácil']}},
                     ],
                 }},
                {'texto': 'Hace chispas o ruidos extraños', 'icono': '✨',
                 'resultado': {'falla_id': 'nueva:Guía de ondas o mica dañada', 'prob': 89, 'rec': 'Reemplazar la mica y limpiar restos de comida quemados.', 'tags': ['Limpieza', 'Urgente']}},
                {'texto': 'La puerta no cierra bien o no enciende con la puerta cerrada', 'icono': '🚪',
                 'resultado': {'falla_id': 'nueva:Interruptores de seguridad de la puerta dañados (microondas)', 'prob': 81, 'rec': 'Revisar los interruptores de seguridad de la puerta.', 'tags': ['Eléctrico', 'Seguridad']}},
                {'texto': 'El panel/botones no responden', 'icono': '🔘',
                 'resultado': {'falla_id': 'nueva:Panel de control o placa electrónica dañada (microondas)', 'prob': 74, 'rec': 'Diagnóstico de la placa de control.', 'tags': ['Electrónico']}},
            ],
        },
    },
    {
        'nombre': 'Calentador de Agua',
        'icono': '🚿',
        'arbol': {
            'pregunta': '¿Cuál es el síntoma principal?',
            'opciones': [
                {'texto': 'No calienta el agua', 'icono': '🥶',
                 'siguiente': {
                     'pregunta': '¿Es a gas o eléctrico?',
                     'opciones': [
                         {'texto': 'A gas',
                          'resultado': {'falla_id': 'nueva:Piloto apagado o termopar dañado', 'prob': 82, 'rec': 'Reencender piloto. Revisar termopar si no se mantiene encendido.', 'tags': ['Gas']}},
                         {'texto': 'Eléctrico',
                          'resultado': {'falla_id': 'nueva:Resistencia eléctrica del calentador quemada', 'prob': 84, 'rec': 'Medir continuidad de la resistencia sumergida. Reemplazar.', 'tags': ['Eléctrico']}},
                     ],
                 }},
                {'texto': 'El agua sale tibia, no caliente', 'icono': '🌡️',
                 'resultado': {'falla_id': 'nueva:Sedimento acumulado en el tanque', 'prob': 75, 'rec': 'Drenar y limpiar el tanque de sedimento acumulado.', 'tags': ['Mantenimiento']}},
                {'texto': 'Gotea o tiene fuga de agua', 'icono': '💧',
                 'resultado': {'falla_id': 'nueva:Válvula de alivio de presión o tanque corroído', 'prob': 90, 'rec': 'Revisar válvula de alivio de presión. Si el tanque está corroído, reemplazar el equipo.', 'tags': ['Urgente']}},
                {'texto': 'Hace ruido (golpeteo o silbido)', 'icono': '🔊',
                 'resultado': {'falla_id': 'nueva:Acumulación de sarro en la resistencia o serpentín', 'prob': 78, 'rec': 'Descalcificar resistencia/serpentín. Revisar dureza del agua.', 'tags': ['Mantenimiento']}},
                {'texto': 'Huele a gas o no se detecta llama piloto', 'icono': '👃',
                 'resultado': {'falla_id': 'nueva:Fuga de gas en instalación o válvula', 'prob': 95, 'rec': 'Cerrar la llave de paso de inmediato y ventilar. Revisión profesional urgente.', 'tags': ['Gas', 'Urgente']}},
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
