"""
simulate_data.py — FrostAnalitic
Genera dataset sintetico de diagnosticos (N_REGISTROS).
Guarda los archivos en la misma carpeta ds/ donde esta este script.
"""
import random, json, csv, os
from datetime import datetime, timedelta

# ── Ruta relativa al script (funciona en cualquier PC) ────────
BASE = os.path.dirname(os.path.abspath(__file__))

random.seed(42)

SINTOMAS = {
    "Refrigerador": [
        "escarcha_mucha_ventilador_si","escarcha_mucha_ventilador_no",
        "escarcha_poca_burbujeo_si","escarcha_poca_burbujeo_no",
        "compresor_no_clic_si","compresor_no_voltaje_si","compresor_no_voltaje_no",
        "ruido_vibracion","ruido_zumbido","ruido_burbujeo",
        "hielo_puerta_mala","hielo_puerta_bien","gotea",
    ],
    "Aire Acondicionado": [
        "filtros_limpios_presion_baja","filtros_limpios_presion_normal",
        "filtros_sucios","exterior_no_control_si","exterior_no_control_no",
        "gotea_antigua","gotea_nueva","ruido_interior","ruido_exterior","codigo_error",
    ],
    "Congelador": [
        "comp_func_temp_0_10","comp_func_temp_mayor_0","comp_no",
        "hielo_evaporador","hielo_bordes","consumo_alto",
    ],
    "Enfriador Comercial": [
        "comp_func_cond_limpio","comp_func_cond_sucio","comp_no_ec",
        "cristales_resist_si","cristales_resist_no","puertas_mal",
    ],
    "Cuarto Frio": [
        "trabaja_sin_parar_filt_si","trabaja_sin_parar_filt_no",
        "cicla_hielo_si","cicla_hielo_no","consumo_alto_cf","alarmas",
    ],
}

GT = {
    "escarcha_mucha_ventilador_si":5,"escarcha_mucha_ventilador_no":6,
    "escarcha_poca_burbujeo_si":1,"escarcha_poca_burbujeo_no":2,
    "compresor_no_clic_si":4,"compresor_no_voltaje_si":3,"compresor_no_voltaje_no":17,
    "ruido_vibracion":3,"ruido_zumbido":18,"ruido_burbujeo":1,
    "hielo_puerta_mala":10,"hielo_puerta_bien":11,"gotea":9,
    "filtros_limpios_presion_baja":1,"filtros_limpios_presion_normal":3,
    "filtros_sucios":13,"exterior_no_control_si":4,"exterior_no_control_no":12,
    "gotea_antigua":9,"gotea_nueva":9,"ruido_interior":18,"ruido_exterior":3,"codigo_error":12,
    "comp_func_temp_0_10":1,"comp_func_temp_mayor_0":3,"comp_no":4,
    "hielo_evaporador":11,"hielo_bordes":10,"consumo_alto":8,
    "comp_func_cond_limpio":1,"comp_func_cond_sucio":8,"comp_no_ec":3,
    "cristales_resist_si":16,"cristales_resist_no":16,"puertas_mal":10,
    "trabaja_sin_parar_filt_si":14,"trabaja_sin_parar_filt_no":1,
    "cicla_hielo_si":11,"cicla_hielo_no":1,"consumo_alto_cf":8,"alarmas":15,
}

PREC = {s: round(random.uniform(0.72, 0.97), 2) for s in GT}
PREC.update({"filtros_sucios":0.97,"puertas_mal":0.95,"gotea":0.89,"gotea_antigua":0.94})

EQ_MAP = {"Refrigerador":1,"Congelador":2,"Aire Acondicionado":3,"Enfriador Comercial":4,"Cuarto Frio":5}
FALLAS_IDS = list(range(1, 19))

# Fallas que puede tener cada equipo (las que sus sintomas pueden indicar)
FALLAS_EQUIPO = {eq: sorted({GT[s] for s in sints}) for eq, sints in SINTOMAS.items()}

# Contexto que cambia la falla mas probable en ciertos sintomas. Esto es lo
# que el arbol de reglas NO mira y un modelo de ML si puede aprender.
#   (condicion, sintomas afectados, falla que se vuelve probable, probabilidad)
REGLAS_CONTEXTO = [
    # Equipo viejo + ruido -> rodamientos gastados
    (lambda ant, t: ant >= 12,
     {"ruido_vibracion", "ruido_zumbido", "ruido_exterior", "ruido_interior"}, 18, 0.60),
    # Equipo viejo + enfria poco sin causa obvia -> compresor desgastado
    (lambda ant, t: ant >= 12,
     {"escarcha_poca_burbujeo_no", "filtros_limpios_presion_normal",
      "comp_func_temp_mayor_0", "trabaja_sin_parar_filt_no"}, 3, 0.55),
    # Calor extremo + enfria poco -> condensador sucio / saturado
    (lambda ant, t: t >= 33,
     {"filtros_limpios_presion_baja", "comp_func_temp_0_10",
      "comp_func_cond_limpio", "cicla_hielo_no"}, 8, 0.60),
]

N_REGISTROS = 2000   # antes 600: con mas registros ninguna falla queda con 2 muestras


def elegir_falla_real(eq, sint, antiguedad, temp):
    """La falla real ya NO es una funcion fija del sintoma: en ciertos
    contextos domina otra falla, y el resto del tiempo el sintoma acierta
    con probabilidad PREC[sint] (si no, es ruido aleatorio)."""
    principal = GT[sint]
    for cond, sintomas, falla, prob in REGLAS_CONTEXTO:
        if sint in sintomas and cond(antiguedad, temp) and random.random() < prob:
            return falla
    if random.random() < PREC.get(sint, 0.82):
        return principal
    otras = [f for f in FALLAS_EQUIPO[eq] if f != principal] or \
            [f for f in FALLAS_IDS if f != principal]
    return random.choice(otras)


rows = []
start = datetime(2024, 1, 1)

for i in range(N_REGISTROS):
    eq    = random.choice(list(SINTOMAS.keys()))
    sint  = random.choice(SINTOMAS[eq])
    antiguedad = random.choices(range(0, 21), weights=[max(1, 12 - abs(a - 6)) for a in range(21)])[0]
    temp  = round(random.gauss(29, 4), 1)
    falla_diag = GT[sint]                      # lo que responde el arbol de reglas
    falla_real = elegir_falla_real(eq, sint, antiguedad, temp)
    correcto   = 1 if falla_real == falla_diag else 0
    prec  = PREC.get(sint, 0.82)
    nivel = random.choices(["normal","tecnico"], weights=[0.7, 0.3])[0]
    fecha = start + timedelta(days=random.randint(0, 400), hours=random.randint(7, 20))
    rows.append({
        "sesion_id":            i + 1,
        "equipo":               eq,
        "equipo_id":            EQ_MAP[eq],
        "sintoma":              sint,
        "antiguedad_anios":     antiguedad,
        "temp_ambiente":        temp,
        "falla_diagnosticada_id": falla_diag,
        "falla_correcta_id":    falla_real,
        "fue_correcto":         correcto,
        "probabilidad":         int(prec * 100),
        "nivel_usuario":        nivel,
        "fecha":                fecha.strftime("%Y-%m-%d %H:%M:%S"),
    })

# ── Guardar CSV ────────────────────────────────────────────────
csv_path = os.path.join(BASE, "dataset_diagnosticos.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

# ── Guardar SQL para MySQL Workbench ──────────────────────────
sql_path = os.path.join(BASE, "insert_sesiones.sql")
with open(sql_path, "w", encoding="utf-8") as f:
    f.write(f"USE frostanalitic;\n-- {len(rows)} sesiones simuladas de diagnostico\n\n")
    for r in rows:
        camino = json.dumps({"sintoma": r["sintoma"]}).replace("'", "''")
        fr     = r["falla_correcta_id"] if not r["fue_correcto"] else "NULL"
        f.write(
            f"INSERT INTO sesiones (equipo_id, falla_id, probabilidad, camino_json, "
            f"fue_correcto, falla_real_id, nivel_usuario, created_at) VALUES "
            f"({r['equipo_id']}, {r['falla_diagnosticada_id']}, {r['probabilidad']}, "
            f"'{camino}', {r['fue_correcto']}, {fr}, '{r['nivel_usuario']}', '{r['fecha']}');\n"
        )
    f.write("\n-- Actualizar contadores de fallas\n")
    f.write("UPDATE fallas f SET\n"
            "  veces_diagnosticada = (SELECT COUNT(*) FROM sesiones s WHERE s.falla_id = f.id),\n"
            "  veces_correcta      = (SELECT COUNT(*) FROM sesiones s WHERE s.falla_id = f.id AND s.fue_correcto = 1);\n")

prec_global = sum(r["fue_correcto"] for r in rows) / len(rows) * 100
print(f"Dataset generado: {len(rows)} registros")
print(f"Precision simulada del arbol: {prec_global:.1f}%")
print(f"CSV guardado en:  {csv_path}")
print(f"SQL guardado en:  {sql_path}")
