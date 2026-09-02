"""
tree_static.py — FrostAnalitic
Árbol de decisiones "de fábrica" (diseñado por el experto), usado como
semilla para migrar a la base de datos (ver migrate_tree.py) y como
respaldo si un equipo todavía no tiene nodos migrados en la BD.
"""

TREE_STATIC = {
    "Refrigerador": {
        "pregunta": "¿Cuál es el síntoma principal?",
        "opciones": [
            {"texto": "No enfría o enfría poco", "icono": "🌡️",
             "siguiente": {
                 "pregunta": "¿El compresor arranca?",
                 "opciones": [
                     {"texto": "Sí arranca normalmente",
                      "siguiente": {
                          "pregunta": "¿El evaporador tiene escarcha excesiva?",
                          "opciones": [
                              {"texto": "Sí, mucha escarcha",
                               "siguiente": {
                                   "pregunta": "¿El ventilador del evaporador funciona?",
                                   "opciones": [
                                       {"texto": "Sí funciona",
                                        "resultado": {"falla": "Termostato o control de deshielo defectuoso", "prob": 82, "falla_id": 5, "rec": "Verificar ciclos de deshielo. Revisar termostato y calefactor.", "tags": ["Eléctrico","Control"]}},
                                       {"texto": "No funciona",
                                        "resultado": {"falla": "Motor del ventilador del evaporador dañado", "prob": 88, "falla_id": 6, "rec": "Revisar motor del ventilador. Comprobar rodamientos.", "tags": ["Mecánico","Ventilación"]}}
                                   ]
                               }},
                              {"texto": "No, poca o ninguna escarcha",
                               "siguiente": {
                                   "pregunta": "¿Se escucha burbujeo o sonido de gas?",
                                   "opciones": [
                                       {"texto": "Sí, sonido de burbujeo",
                                        "resultado": {"falla": "Fuga de refrigerante", "prob": 91, "falla_id": 1, "rec": "Prueba de presión con nitrógeno. Localizar fuga y recargar.", "tags": ["Refrigerante","Urgente"]}},
                                       {"texto": "No hay sonido",
                                        "resultado": {"falla": "Capilar obstruido o filtro secador saturado", "prob": 79, "falla_id": 2, "rec": "Sustituir filtro secador. Verificar capilar.", "tags": ["Hidráulico"]}}
                                   ]
                               }}
                          ]
                      }},
                     {"texto": "No arranca o intenta arrancar",
                      "siguiente": {
                          "pregunta": "¿Se escucha un clic repetitivo?",
                          "opciones": [
                              {"texto": "Sí, clic repetitivo",
                               "resultado": {"falla": "Relay de arranque o capacitor defectuoso", "prob": 87, "falla_id": 4, "rec": "Reemplazar relay PTC o capacitor de arranque.", "tags": ["Eléctrico","Arranque"]}},
                              {"texto": "No, silencio total",
                               "siguiente": {
                                   "pregunta": "¿Hay voltaje en el tomacorriente?",
                                   "opciones": [
                                       {"texto": "Sí hay voltaje",
                                        "resultado": {"falla": "Compresor defectuoso", "prob": 85, "falla_id": 3, "rec": "Medir devanados. Revisar protector térmico.", "tags": ["Eléctrico","Compresor"]}},
                                       {"texto": "No hay voltaje",
                                        "resultado": {"falla": "Falla eléctrica externa", "prob": 95, "falla_id": 17, "rec": "Revisar fusible y breaker del panel.", "tags": ["Eléctrico","Instalación"]}}
                                   ]
                               }}
                          ]
                      }}
                 ]
             }},
            {"texto": "Hace ruidos anormales", "icono": "🔊",
             "siguiente": {
                 "pregunta": "¿Cómo describe el ruido?",
                 "opciones": [
                     {"texto": "Vibración fuerte o golpeteo", "resultado": {"falla": "Compresor con vibración excesiva", "prob": 76, "falla_id": 3, "rec": "Verificar tornillos de montaje. Revisar aisladores.", "tags": ["Mecánico"]}},
                     {"texto": "Zumbido o quejido agudo", "resultado": {"falla": "Motor del ventilador con rodamientos desgastados", "prob": 83, "falla_id": 18, "rec": "Lubricar o reemplazar motor del ventilador.", "tags": ["Mecánico"]}},
                     {"texto": "Burbujeo o líquido", "resultado": {"falla": "Nivel de refrigerante bajo (fuga parcial)", "prob": 72, "falla_id": 1, "rec": "Verificar nivel de carga. Localizar microfuga.", "tags": ["Refrigerante"]}}
                 ]
             }},
            {"texto": "Forma hielo excesivo en la pared trasera", "icono": "❄️",
             "siguiente": {
                 "pregunta": "¿La puerta cierra perfectamente?",
                 "opciones": [
                     {"texto": "La puerta no sella bien", "resultado": {"falla": "Empaque de puerta deteriorado", "prob": 93, "falla_id": 10, "rec": "Reemplazar empaque de goma.", "tags": ["Sellado","Fácil"]}},
                     {"texto": "La puerta cierra bien", "resultado": {"falla": "Sistema de deshielo automático defectuoso", "prob": 86, "falla_id": 11, "rec": "Verificar resistencia de deshielo y temporizador.", "tags": ["Eléctrico","Deshielo"]}}
                 ]
             }},
            {"texto": "Gotea agua dentro o fuera", "icono": "💧",
             "resultado": {"falla": "Drenaje de deshielo obstruido", "prob": 89, "falla_id": 9, "rec": "Limpiar orificio de drenaje del evaporador.", "tags": ["Hidráulico","Limpieza"]}}
        ]
    },
    "Congelador": {
        "pregunta": "¿Cuál es el síntoma principal?",
        "opciones": [
            {"texto": "No congela o congela poco", "icono": "🌡️",
             "siguiente": {
                 "pregunta": "¿El compresor está funcionando?",
                 "opciones": [
                     {"texto": "Sí, se siente caliente y funciona",
                      "siguiente": {
                          "pregunta": "¿Cuál es la temperatura actual?",
                          "opciones": [
                              {"texto": "Entre 0°C y -10°C", "resultado": {"falla": "Carga baja de refrigerante / fuga parcial", "prob": 84, "falla_id": 1, "rec": "Revisar presiones. Localizar y reparar fuga.", "tags": ["Refrigerante"]}},
                              {"texto": "Más de 0°C (no congela nada)", "resultado": {"falla": "Pérdida total de refrigerante o compresor ineficiente", "prob": 88, "falla_id": 3, "rec": "Diagnóstico completo del sistema.", "tags": ["Sistema","Urgente"]}}
                          ]
                      }},
                     {"texto": "No funciona / no arranca", "resultado": {"falla": "Relay, capacitor o compresor defectuoso", "prob": 86, "falla_id": 4, "rec": "Diagnóstico eléctrico completo.", "tags": ["Eléctrico"]}}
                 ]
             }},
            {"texto": "Se forman bloques de hielo anormales", "icono": "🧊",
             "siguiente": {
                 "pregunta": "¿Dónde se acumula el hielo?",
                 "opciones": [
                     {"texto": "En el evaporador (pared trasera)", "resultado": {"falla": "Sistema de deshielo defectuoso", "prob": 91, "falla_id": 11, "rec": "Reemplazar resistencia de deshielo.", "tags": ["Deshielo"]}},
                     {"texto": "En la tapa o bordes", "resultado": {"falla": "Empaque de puerta deteriorado", "prob": 87, "falla_id": 10, "rec": "Reemplazar empaque. Verificar sellado.", "tags": ["Sellado"]}}
                 ]
             }},
            {"texto": "Consume mucha energía", "icono": "⚡", "resultado": {"falla": "Condensador sucio o ventilación obstruida", "prob": 78, "falla_id": 8, "rec": "Limpiar condensador con compresor de aire.", "tags": ["Limpieza","Eficiencia"]}}
        ]
    },
    "Aire Acondicionado": {
        "pregunta": "¿Cuál es el síntoma principal?",
        "opciones": [
            {"texto": "No enfría", "icono": "🌡️",
             "siguiente": {
                 "pregunta": "¿La unidad exterior enciende?",
                 "opciones": [
                     {"texto": "Sí enciende",
                      "siguiente": {
                          "pregunta": "¿Los filtros están limpios?",
                          "opciones": [
                              {"texto": "Sí están limpios",
                               "siguiente": {
                                   "pregunta": "¿La presión del gas es correcta?",
                                   "opciones": [
                                       {"texto": "Presión baja (con manómetro)", "resultado": {"falla": "Fuga de gas refrigerante", "prob": 90, "falla_id": 1, "rec": "Localizar fuga y recargar R-410A/R-22.", "tags": ["Refrigerante","Urgente"]}},
                                       {"texto": "Presión normal", "resultado": {"falla": "Compresor de baja eficiencia", "prob": 75, "falla_id": 3, "rec": "Revisar eficiencia del compresor.", "tags": ["Compresor"]}}
                                   ]
                               }},
                              {"texto": "No, están sucios", "resultado": {"falla": "Filtros obstruidos", "prob": 97, "falla_id": 13, "rec": "Limpiar o reemplazar filtros.", "tags": ["Limpieza","Fácil"]}}
                          ]
                      }},
                     {"texto": "No enciende",
                      "siguiente": {
                          "pregunta": "¿El control remoto funciona?",
                          "opciones": [
                              {"texto": "Sí funciona", "resultado": {"falla": "Capacitor o compresor exterior dañado", "prob": 82, "falla_id": 4, "rec": "Revisar capacitor del compresor y contactor.", "tags": ["Eléctrico"]}},
                              {"texto": "No responde", "resultado": {"falla": "Tarjeta de control o PCB defectuosa", "prob": 79, "falla_id": 12, "rec": "Reemplazar baterías. Si persiste, revisar PCB.", "tags": ["Electrónico"]}}
                          ]
                      }}
                 ]
             }},
            {"texto": "Gotea agua hacia adentro", "icono": "💧",
             "siguiente": {
                 "pregunta": "¿La instalación tiene más de 3 años?",
                 "opciones": [
                     {"texto": "Sí, instalación antigua", "resultado": {"falla": "Drenaje obstruido por algas/suciedad", "prob": 94, "falla_id": 9, "rec": "Limpiar tubería de drenaje con agua a presión.", "tags": ["Limpieza"]}},
                     {"texto": "No, instalación nueva", "resultado": {"falla": "Instalación incorrecta del drenaje", "prob": 88, "falla_id": 9, "rec": "Verificar pendiente mínima del 2%.", "tags": ["Instalación"]}}
                 ]
             }},
            {"texto": "Hace mucho ruido", "icono": "🔊",
             "siguiente": {
                 "pregunta": "¿El ruido viene de la unidad interior o exterior?",
                 "opciones": [
                     {"texto": "Unidad interior", "resultado": {"falla": "Rodamientos del ventilador interior desgastados", "prob": 80, "falla_id": 18, "rec": "Lubricar o reemplazar motor del ventilador.", "tags": ["Mecánico"]}},
                     {"texto": "Unidad exterior", "resultado": {"falla": "Compresor con vibración o anclaje suelto", "prob": 76, "falla_id": 3, "rec": "Revisar montaje y tornillos del compresor.", "tags": ["Mecánico"]}}
                 ]
             }},
            {"texto": "Display muestra código de error", "icono": "💻",
             "resultado": {"falla": "Error en sensor, tarjeta o comunicación", "prob": 85, "falla_id": 12, "rec": "Anotar código. E1-E5: sensores. F-codes: ventiladores.", "tags": ["Electrónico"]}}
        ]
    },
    "Enfriador Comercial": {
        "pregunta": "¿Cuál es el problema del enfriador?",
        "opciones": [
            {"texto": "No mantiene temperatura", "icono": "🌡️",
             "siguiente": {
                 "pregunta": "¿El compresor funciona?",
                 "opciones": [
                     {"texto": "Sí funciona",
                      "siguiente": {
                          "pregunta": "¿El condensador está limpio?",
                          "opciones": [
                              {"texto": "Sí, limpio", "resultado": {"falla": "Carga de refrigerante baja o fuga", "prob": 83, "falla_id": 1, "rec": "Verificar presiones y recargar sistema.", "tags": ["Refrigerante"]}},
                              {"texto": "No, obstruido", "resultado": {"falla": "Condensador obstruido", "prob": 91, "falla_id": 8, "rec": "Limpiar condensador con aire comprimido.", "tags": ["Limpieza","Urgente"]}}
                          ]
                      }},
                     {"texto": "No funciona", "resultado": {"falla": "Falla eléctrica en compresor o control", "prob": 87, "falla_id": 3, "rec": "Revisar panel, termostato y relay de compresor.", "tags": ["Eléctrico"]}}
                 ]
             }},
            {"texto": "Cristales con mucha humedad", "icono": "💧",
             "siguiente": {
                 "pregunta": "¿Hay resistencias calefactoras en los cristales?",
                 "opciones": [
                     {"texto": "Sí pero no calientan", "resultado": {"falla": "Resistencia anti-vaho defectuosa", "prob": 89, "falla_id": 16, "rec": "Verificar continuidad de resistencias.", "tags": ["Eléctrico"]}},
                     {"texto": "No hay resistencias", "resultado": {"falla": "Falta de resistencias anti-condensación", "prob": 80, "falla_id": 16, "rec": "Instalar resistencias anti-condensación.", "tags": ["Instalación"]}}
                 ]
             }},
            {"texto": "Puertas no sellan bien", "icono": "🚪",
             "resultado": {"falla": "Empaques deteriorados o puerta mal alineada", "prob": 95, "falla_id": 10, "rec": "Reemplazar empaques. Verificar alineación.", "tags": ["Sellado","Fácil"]}}
        ]
    },
    "Cuarto Frío": {
        "pregunta": "¿Cuál es el síntoma del cuarto frío?",
        "opciones": [
            {"texto": "No alcanza temperatura de diseño", "icono": "🌡️",
             "siguiente": {
                 "pregunta": "¿El sistema trabaja continuamente sin parar?",
                 "opciones": [
                     {"texto": "Sí, trabaja sin parar",
                      "siguiente": {
                          "pregunta": "¿Hay filtraciones de aire o paredes dañadas?",
                          "opciones": [
                              {"texto": "Sí hay filtraciones", "resultado": {"falla": "Pérdida de aislamiento térmico", "prob": 88, "falla_id": 14, "rec": "Sellar juntas y reparar paneles de aislamiento.", "tags": ["Aislamiento","Urgente"]}},
                              {"texto": "No, aislamiento parece bien", "resultado": {"falla": "Sistema subdimensionado o carga excesiva", "prob": 76, "falla_id": 1, "rec": "Verificar carga térmica vs capacidad instalada.", "tags": ["Sistema"]}}
                          ]
                      }},
                     {"texto": "Cicla normalmente pero no baja",
                      "siguiente": {
                          "pregunta": "¿El evaporador tiene escarcha excesiva?",
                          "opciones": [
                              {"texto": "Sí, evaporador cubierto de hielo", "resultado": {"falla": "Sistema de deshielo defectuoso", "prob": 92, "falla_id": 11, "rec": "Descongelar manualmente. Revisar resistencias de deshielo.", "tags": ["Deshielo","Urgente"]}},
                              {"texto": "No, evaporador normal", "resultado": {"falla": "Carga insuficiente de refrigerante", "prob": 84, "falla_id": 1, "rec": "Medir presiones. Detectar posible fuga.", "tags": ["Refrigerante"]}}
                          ]
                      }}
                 ]
             }},
            {"texto": "Alto consumo de energía", "icono": "⚡",
             "siguiente": {
                 "pregunta": "¿Cuándo fue la última limpieza del condensador?",
                 "opciones": [
                     {"texto": "Hace más de 6 meses", "resultado": {"falla": "Condensador sucio — alta presión de condensación", "prob": 90, "falla_id": 8, "rec": "Limpiar condensador. Programar mantenimiento trimestral.", "tags": ["Limpieza","Eficiencia"]}},
                     {"texto": "Limpieza reciente", "resultado": {"falla": "Compresor ineficiente o fuga parcial", "prob": 77, "falla_id": 3, "rec": "Medir amperaje del compresor. Verificar presiones.", "tags": ["Compresor"]}}
                 ]
             }},
            {"texto": "Alarmas de temperatura", "icono": "🔔",
             "resultado": {"falla": "Sensor de temperatura defectuoso o mal configurado", "prob": 82, "falla_id": 15, "rec": "Calibrar sensor con termómetro de referencia.", "tags": ["Control"]}}
        ]
    }
}
