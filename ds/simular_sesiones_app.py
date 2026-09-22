"""
simular_sesiones_app.py — FrostAnalitic
Genera diagnosticos simulados para la BASE DE DATOS de la app, recorriendo
los arboles reales de los 12 equipos (tree_static.py + seed_new_equipos.py).

Diferencias con ds/simulate_data.py (que es solo para el analisis de la tesis):
  - Cubre todos los equipos, no solo los 5 de refrigeracion.
  - camino_json tiene el mismo formato que guarda la app
    ([{"pregunta":..., "resp":...}, ...]), asi "Reentrenar IA" puede usarlos.
  - El SQL busca equipos y fallas por NOMBRE, no por id, asi funciona igual
    en la BD local y en Railway aunque los ids no coincidan.
  - Borra primero los simulados anteriores (los viejos de 600 y los de esta
    version, marcados con nota_usuario='[simulado]'); los diagnosticos que
    hiciste a mano no se tocan.

Uso:  python ds/simular_sesiones_app.py   ->  ds/insert_sesiones.sql
Luego ejecuta ese .sql en MySQL Workbench (local y/o Railway).
"""
import ast, json, os, random, re, sys
from datetime import datetime, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(BASE)
sys.path.insert(0, RAIZ)
from tree_static import TREE_STATIC   # noqa: E402

random.seed(2026)
MARCA = '[simulado]'
POR_EQUIPO = {  # cuantos diagnosticos simulados por equipo
    'Refrigerador': 260, 'Congelador': 220, 'Aire Acondicionado': 240,
    'Enfriador Comercial': 200, 'Cuarto Frío': 200,
}
POR_EQUIPO_NUEVO = 140
SIN_FEEDBACK = 0.08          # parte de diagnosticos que nadie confirmo
FECHA_FIN = datetime(2026, 9, 20)
DIAS = 420

# ── Catalogo de fallas (id "de fabrica" -> nombre) desde schema.sql ──
schema = open(os.path.join(RAIZ, 'schema.sql'), encoding='utf-8').read()
bloque = schema[schema.index('INSERT INTO `fallas`'):]
bloque = bloque[:bloque.index('ON DUPLICATE KEY')]
filas = re.findall(r"\('((?:[^']|'')*)',\s*'(?:[^']|'')*',\s*'\w+',\s*'([^']*)'\)", bloque)
ID_A_FALLA = {i + 1: n.replace("''", "'") for i, (n, _) in enumerate(filas)}
TAGS = {n.replace("''", "'"): t for n, t in filas}
assert len(ID_A_FALLA) == 18, len(ID_A_FALLA)

# ── Arboles y fallas nuevas desde seed_new_equipos.py (sin importar la app) ──
seed_src = open(os.path.join(RAIZ, 'seed_new_equipos.py'), encoding='utf-8').read()
seed = {}
for nodo in ast.parse(seed_src).body:
    if isinstance(nodo, ast.Assign) and isinstance(nodo.targets[0], ast.Name) \
            and nodo.targets[0].id in ('EQUIPOS_NUEVOS', 'FALLAS_NUEVAS'):
        seed[nodo.targets[0].id] = ast.literal_eval(nodo.value)
for f in seed['FALLAS_NUEVAS']:
    TAGS[f['nombre']] = f.get('equipos_tag', '')

ARBOLES = dict(TREE_STATIC)
for e in seed['EQUIPOS_NUEVOS']:
    ARBOLES[e['nombre']] = e['arbol']

ABREV = {'Ref': 'Refrigerador', 'Cong': 'Congelador', 'AA': 'Aire Acondicionado',
         'EC': 'Enfriador Comercial', 'CF': 'Cuarto Frío'}
REFRIG = set(ABREV.values()) | {'Vitrina Refrigerada', 'Máquina de Hielo'}


def nombre_falla(fid):
    if isinstance(fid, str) and fid.startswith('nueva:'):
        return fid.split(':', 1)[1]
    return ID_A_FALLA[int(fid)]


def hojas(nodo, camino=()):
    """Cada resultado del arbol con el camino de preguntas/respuestas."""
    for op in nodo.get('opciones', []):
        paso = camino + ({'pregunta': nodo['pregunta'], 'resp': op['texto']},)
        if 'resultado' in op:
            r = op['resultado']
            yield list(paso), nombre_falla(r['falla_id']), r.get('prob', 80)
        elif 'siguiente' in op:
            yield from hojas(op['siguiente'], paso)


def fallas_del_equipo(eq, de_hojas):
    """Fallas posibles del equipo: las de su arbol + las que lo etiquetan."""
    res = set(de_hojas)
    for falla, tag in TAGS.items():
        partes = [p.strip() for p in (tag or '').split(',')]
        if eq in partes or any(ABREV.get(p) == eq for p in partes) \
                or ('Todos' in partes and eq in REFRIG):
            res.add(falla)
    return sorted(res)


def q(s):
    return "'" + str(s).replace('\\', '\\\\').replace("'", "''") + "'"


filas_sql, resumen = [], {}
for eq, arbol in ARBOLES.items():
    lista = list(hojas(arbol))
    posibles = fallas_del_equipo(eq, [h[1] for h in lista])
    n = POR_EQUIPO.get(eq, POR_EQUIPO_NUEVO)
    for _ in range(n):
        camino, falla_arbol, prob = random.choice(lista)
        p_ok = min(0.97, max(0.55, prob / 100 + random.uniform(-0.06, 0.04)))
        if random.random() < SIN_FEEDBACK:
            ok, real = None, None
        elif random.random() < p_ok:
            ok, real = 1, None
        else:
            otras = [f for f in posibles if f != falla_arbol]
            ok, real = 0, random.choice(otras)
        nivel = random.choices(['normal', 'tecnico'], weights=[0.7, 0.3])[0]
        fecha = FECHA_FIN - timedelta(days=random.randint(0, DIAS),
                                      hours=random.randint(0, 12), minutes=random.randint(0, 59))
        filas_sql.append((eq, falla_arbol, prob, json.dumps(camino, ensure_ascii=False),
                          ok, real, nivel, fecha.strftime('%Y-%m-%d %H:%M:%S')))
    resumen[eq] = n

random.shuffle(filas_sql)
filas_sql.sort(key=lambda r: r[7])

out = os.path.join(BASE, 'insert_sesiones.sql')
with open(out, 'w', encoding='utf-8') as f:
    f.write(f"""-- ============================================================
--  FrostAnalitic — {len(filas_sql)} diagnosticos simulados ({len(ARBOLES)} equipos)
--  Generado por ds/simular_sesiones_app.py. Seguro de re-ejecutar:
--  borra los simulados anteriores y NO toca los diagnosticos reales.
--  Requiere haber corrido schema.sql y seed_new_equipos.py antes.
-- ============================================================
SET NAMES utf8mb4;
USE `frostanalitic`;
SET SQL_SAFE_UPDATES = 0;

-- 1) Borrar simulados anteriores (version de 600 y esta version)
DELETE c FROM correcciones c JOIN sesiones s ON s.id = c.sesion_id
 WHERE s.nota_usuario = '{MARCA}' OR JSON_EXTRACT(s.camino_json, '$.sintoma') IS NOT NULL;
DELETE FROM sesiones
 WHERE nota_usuario = '{MARCA}' OR JSON_EXTRACT(camino_json, '$.sintoma') IS NOT NULL;

-- 2) Cargar los nuevos en una tabla auxiliar (por nombre)
DROP TABLE IF EXISTS `_sim_sesiones`;
CREATE TABLE `_sim_sesiones` (
  equipo VARCHAR(100), falla VARCHAR(255), prob INT, camino JSON,
  ok TINYINT NULL, falla_real VARCHAR(255) NULL, nivel VARCHAR(10), fecha DATETIME
) DEFAULT CHARSET=utf8mb4;
""")
    for i in range(0, len(filas_sql), 200):
        chunk = filas_sql[i:i + 200]
        f.write("INSERT INTO `_sim_sesiones` VALUES\n" + ",\n".join(
            f"({q(e)},{q(fa)},{p},{q(c)},{'NULL' if ok is None else ok},"
            f"{'NULL' if r is None else q(r)},{q(nv)},{q(d)})"
            for e, fa, p, c, ok, r, nv, d in chunk) + ";\n")
    f.write(f"""
-- 3) Si esta consulta devuelve filas, falta algun equipo o falla en la BD
--    (corre schema.sql y seed_new_equipos.py primero). Deberia salir vacia.
SELECT DISTINCT 'equipo no encontrado' AS problema, s.equipo AS nombre FROM `_sim_sesiones` s
  LEFT JOIN equipos e ON e.nombre = s.equipo WHERE e.id IS NULL
UNION
SELECT DISTINCT 'falla no encontrada', s.falla FROM `_sim_sesiones` s
  LEFT JOIN fallas f ON f.nombre = s.falla WHERE f.id IS NULL
UNION
SELECT DISTINCT 'falla no encontrada', s.falla_real FROM `_sim_sesiones` s
  LEFT JOIN fallas f ON f.nombre = s.falla_real WHERE s.falla_real IS NOT NULL AND f.id IS NULL;

-- 4) Insertar en sesiones resolviendo ids por nombre
INSERT INTO sesiones (equipo_id, falla_id, probabilidad, camino_json, fue_correcto,
                      falla_real_id, nota_usuario, nivel_usuario, created_at)
SELECT e.id, f.id, s.prob, s.camino, s.ok, fr.id, '{MARCA}', s.nivel, s.fecha
  FROM `_sim_sesiones` s
  JOIN equipos e ON e.nombre = s.equipo
  JOIN fallas  f ON f.nombre = s.falla
  LEFT JOIN fallas fr ON fr.nombre = s.falla_real;

DROP TABLE `_sim_sesiones`;

-- 4b) Las correcciones de los simulados, ya marcadas como revisadas por un
--     admin. Sin esto, "Reentrenar IA" solo aprende a repetir el arbol
--     (sale 100% porque las correcciones sin aprobar no entran al entrenamiento).
INSERT INTO correcciones (sesion_id, falla_correcta_id, descripcion_libre,
                          nivel_usuario, revisado, created_at)
SELECT id, falla_real_id, '{MARCA}', nivel_usuario, 1, created_at
  FROM sesiones WHERE nota_usuario = '{MARCA}' AND fue_correcto = 0;

-- 5) Recalcular contadores de cada falla (los usa la probabilidad ajustada)
UPDATE fallas f SET
  veces_diagnosticada = (SELECT COUNT(*) FROM sesiones s WHERE s.falla_id = f.id),
  veces_correcta      = (SELECT COUNT(*) FROM sesiones s WHERE s.falla_id = f.id AND s.fue_correcto = 1);

-- 6) Resumen
SELECT e.nombre AS equipo, COUNT(s.id) AS diagnosticos
  FROM equipos e LEFT JOIN sesiones s ON s.equipo_id = e.id
 GROUP BY e.id, e.nombre ORDER BY e.id;
""")

total_fallas = len({r[1] for r in filas_sql} | {r[5] for r in filas_sql if r[5]})
print(f"{len(filas_sql)} diagnosticos simulados, {total_fallas} fallas distintas")
for eq, n in resumen.items():
    print(f"  {eq:<22} {n}")
print(f"SQL: {out}")
