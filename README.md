# FrostAnalitic v3 — Guía de instalación

## Requisitos
- Python 3.9+
- MySQL 8.0+ (MySQL Workbench)
- pip

## Pasos para correr localmente

### 1. Importar la base de datos
Abre MySQL Workbench y ejecuta el archivo `schema.sql`:
```
File → Open SQL Script → schema.sql → Execute (rayo)
```
Esto crea (o actualiza, si ya existía) la BD `frostanalitic` con todas las
tablas, incluyendo `usuarios` y las columnas nuevas del árbol dinámico.
Es seguro volver a ejecutar este archivo tantas veces como quieras.

### 2. Configurar variables de entorno
Copia `.env.example` a `.env`:
```bash
cp .env.example .env
```
Edita `.env` y coloca tu contraseña real de MySQL root en `LOCAL_DB_PASSWORD`
(o define `DATABASE_URL` completo si prefieres). El archivo `.env` nunca se
sube a git — ya está excluido en `.gitignore`.

Variables relevantes:
| Variable | Para qué sirve | Valor por defecto |
|---|---|---|
| `SECRET_KEY` | Firma las cookies de sesión (login). **Cámbiala en producción.** | `frostanalitic-dev-secret-cambia-esto` |
| `ADMIN_EMAIL` | Email del usuario admin que se crea automáticamente la primera vez que arranca la app (si la tabla `usuarios` está vacía) | `admin@frostanalitic.local` |
| `ADMIN_PASSWORD` | Contraseña de ese admin inicial — **cámbiala después del primer login** | `admin123` |

### 3. Instalar dependencias Python
```bash
pip install -r requirements.txt
```

### 4. Correr la app
```bash
python app.py
```
Abre el navegador en: http://localhost:5000

### 5. (Opcional) Migrar el árbol de fábrica a la base de datos
El árbol de decisiones funciona "de fábrica" con `tree_static.py` (igual
que antes), pero para poder editarlo desde el panel admin sin tocar código
necesitas migrarlo una vez a las tablas `nodos`/`opciones`:
```bash
python migrate_tree.py
```
Es seguro ejecutarlo más de una vez: si un equipo ya fue migrado, se omite.
Los equipos que no migres siguen funcionando con el árbol estático de
respaldo, exactamente igual que antes.

### 6. Iniciar sesión como admin
Entra con el email/contraseña de `ADMIN_EMAIL`/`ADMIN_PASSWORD` (por
defecto `admin@frostanalitic.local` / `admin123`) usando el botón
"Iniciar sesión" arriba a la derecha. Verás la pestaña **Admin** en el
menú lateral para editar el árbol y gestionar usuarios.

## Estructura del proyecto
```
FrostAnalitic/
├── app.py              ← Servidor Flask: rutas núcleo (árbol, sesiones, stats)
├── auth.py             ← Autenticación y roles (login/registro/sesión)
├── admin_api.py         ← CRUD del árbol dinámico y gestión de usuarios (admin)
├── ml_api.py            ← Rutas HTTP de la integración de IA en vivo
├── ml_service.py        ← Entrenamiento/predicción del modelo de IA con datos reales
├── reports_api.py       ← Exportación de reportes (CSV / PDF)
├── tree_service.py       ← Construye el árbol desde la BD + probabilidad ajustada (Bayes)
├── tree_static.py        ← Árbol de decisiones de fábrica (respaldo / semilla)
├── migrate_tree.py       ← Migra tree_static.py -> tablas nodos/opciones
├── schema.sql           ← BD completa con datos iniciales (idempotente)
├── requirements.txt     ← Dependencias Python del servidor
├── Procfile             ← Comando de arranque para Railway (gunicorn)
├── .env.example         ← Plantilla de variables de entorno
├── .gitignore           ← Archivos/carpetas excluidos de git
├── models/
│   └── models.py        ← Modelos SQLAlchemy (ORM), incluye Usuario
├── ds/
│   ├── simulate_data.py     ← Genera dataset sintético (para la tesis)
│   ├── ml_model.py           ← Entrena y compara modelos ML sobre datos sintéticos
│   └── requirements-ds.txt   ← Dependencias extra solo para lo anterior
└── templates/
    └── index.html       ← SPA completa (HTML+CSS+JS)
```

## Roles y autenticación

El sistema tiene tres roles:
- **normal** — puede diagnosticar y dar retroalimentación (igual que un
  invitado sin cuenta; registrarse solo permite llevar historial).
- **tecnico** — además puede ver el estado del modelo de IA, reentrenarlo
  y exportar reportes (CSV/PDF).
- **admin** — además puede editar el árbol de decisiones y cambiar el rol
  de otros usuarios desde el panel Admin.

El autoregistro público (`/api/auth/register`) siempre crea cuentas
`normal`; un admin promueve a `tecnico` o `admin` desde el panel.

## Cómo funciona el aprendizaje

El sistema aprende de dos maneras:

**1. Probabilidad ajustada (suavizado bayesiano)** — El porcentaje que ves
en cada resultado ya no es fijo: combina la estimación original del
experto con la tasa de aciertos real observada en `fallas.veces_correcta`
/ `veces_diagnosticada` (ver `probabilidad_ajustada()` en
`tree_service.py`). Con pocos datos reales domina la estimación del
experto; con más uso, domina la evidencia real.

**2. Modelo de IA en vivo** — Cuando hay suficientes sesiones con
retroalimentación (25 por defecto), un botón en Estadísticas
("Reentrenar IA con datos reales") entrena un modelo de Random Forest
sobre los caminos de diagnóstico reales y sus correcciones. A partir de
ahí, cada diagnóstico muestra una comparación "árbol de reglas vs. IA".

**Usuario normal** — Al terminar un diagnóstico ve:
> "¿El diagnóstico fue correcto?"  ✓ Sí / ✗ No

Si dice **Sí** → incrementa `veces_correcta` de esa falla en la BD.
Si dice **No** → puede seleccionar la falla real de una lista.

**Técnico especialista** — Puede además escribir una descripción libre
de lo que encontró. Esto se guarda en la tabla `correcciones` para
revisión y mejora futura del árbol.

## Tabla de aprendizaje
- `sesiones` → cada diagnóstico realizado (incluye quién lo hizo, si tenía sesión iniciada)
- `correcciones` → cuando un usuario corrige al sistema
- `fallas.veces_diagnosticada` → cuántas veces se diagnosticó
- `fallas.veces_correcta` → cuántas veces fue confirmada correcta
- La columna "Precisión BD" en el catálogo muestra el % en tiempo real

## API disponible

### Núcleo
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/tree/<equipo>` | Árbol de decisiones del equipo (BD si está migrado, si no TREE_STATIC) |
| GET | `/api/equipos` | Lista de equipos |
| GET | `/api/fallas` | Catálogo de fallas con estadísticas |
| POST | `/api/sesion` | Guardar resultado de diagnóstico |
| POST | `/api/feedback` | Registrar retroalimentación |
| GET | `/api/stats` | Estadísticas globales del sistema |

### Autenticación (`auth.py`)
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/auth/register` | Crear cuenta (rol `normal`) |
| POST | `/api/auth/login` | Iniciar sesión |
| POST | `/api/auth/logout` | Cerrar sesión |
| GET | `/api/auth/me` | Usuario actual (o `null`) |

### Panel admin (`admin_api.py`, requieren rol `admin`)
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET/POST | `/api/admin/nodos` | Listar / crear nodos del árbol |
| PUT/DELETE | `/api/admin/nodos/<id>` | Editar / borrar un nodo |
| POST | `/api/admin/opciones` | Crear una opción |
| PUT/DELETE | `/api/admin/opciones/<id>` | Editar / borrar una opción |
| GET | `/api/admin/usuarios` | Listar usuarios |
| PUT | `/api/admin/usuarios/<id>` | Cambiar rol / activar-desactivar |

### IA en vivo (`ml_api.py`)
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/ml/status` | ¿Hay modelo entrenado con datos reales? ¿cuántas sesiones hay? |
| POST | `/api/ml/predict` | Predicción de IA para un camino de diagnóstico dado |
| POST | `/api/ml/retrain` | Reentrena el modelo con las sesiones reales (rol `admin`/`tecnico`) |

### Reportes (`reports_api.py`, requieren rol `admin`/`tecnico`)
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/export/csv` | Exporta todas las sesiones en CSV |
| GET | `/api/export/pdf` | Reporte PDF con estadísticas y gráficas |

## Despliegue en Railway

1. Sube este proyecto a un repositorio de GitHub (el archivo `.env` no se
   sube porque está en `.gitignore` — nunca subas tu contraseña real).
2. En [Railway](https://railway.app), crea un proyecto nuevo con
   **Deploy from GitHub repo** y selecciona este repositorio.
3. Agrega un plugin de **MySQL** desde el catálogo de Railway (botón
   "+ New" → "Database" → "MySQL") **dentro del mismo proyecto** que el
   servicio web (si quedan en proyectos distintos, las variables de
   referencia `${{MySQL.VARIABLE}}` no van a resolver).
4. En la pestaña **Variables** del servicio web, define (además de las
   que Railway ya inyecta automáticamente desde el plugin de MySQL):
   - `SECRET_KEY` → una cadena larga y aleatoria.
   - `ADMIN_EMAIL` / `ADMIN_PASSWORD` → credenciales del admin inicial.
5. Railway detecta el `Procfile` y arranca la app con `gunicorn`
   automáticamente.
6. Carga el esquema: en la pestaña **Connect** del plugin de MySQL, copia
   las credenciales (públicas, temporalmente, si es la primera carga) y
   ejecuta `schema.sql` contra esa base con MySQL Workbench.
7. (Opcional pero recomendado) Corre `migrate_tree.py` una vez contra esa
   misma base para poder editar el árbol desde el panel admin.
8. Abre la URL pública que Railway asigna al servicio — FrostAnalitic
   debería estar corriendo ahí, ya con login, panel admin, IA en vivo y
   exportación de reportes.
