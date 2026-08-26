# FrostAnalitic v2 — Guía de instalación

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
Esto crea la BD `frostanalitic` con todas las tablas y datos iniciales.

### 2. Configurar la conexión a MySQL
Copia `.env.example` a `.env`:
```bash
cp .env.example .env
```
Edita `.env` y coloca tu contraseña real de MySQL root en `LOCAL_DB_PASSWORD`
(o define `DATABASE_URL` completo si prefieres). El archivo `.env` nunca se
sube a git — ya está excluido en `.gitignore`.

### 3. Instalar dependencias Python
```bash
pip install -r requirements.txt
```

### 4. Correr la app
```bash
python app.py
```
Abre el navegador en: http://localhost:5000

## Estructura del proyecto
```
FrostAnalitic/
├── app.py              ← Servidor Flask + todas las rutas API
├── schema.sql          ← BD completa con datos iniciales
├── requirements.txt    ← Dependencias Python
├── Procfile            ← Comando de arranque para Railway (gunicorn)
├── .env.example        ← Plantilla de variables de entorno
├── .gitignore          ← Archivos/carpetas excluidos de git
├── models/
│   └── models.py       ← Modelos SQLAlchemy (ORM)
└── templates/
    └── index.html      ← SPA completa (HTML+CSS+JS)
```

## Cómo funciona el aprendizaje

El sistema aprende de dos maneras:

**Usuario normal** — Al terminar un diagnóstico ve:
> "¿El diagnóstico fue correcto?"  ✓ Sí / ✗ No

Si dice **Sí** → incrementa `veces_correcta` de esa falla en la BD.
Si dice **No** → puede seleccionar la falla real de una lista.

**Técnico especialista** — Puede además escribir una descripción libre
de lo que encontró. Esto se guarda en la tabla `correcciones` para
revisión y mejora futura del árbol.

## Tabla de aprendizaje
- `sesiones` → cada diagnóstico realizado
- `correcciones` → cuando un usuario corrige al sistema
- `fallas.veces_diagnosticada` → cuántas veces se diagnosticó
- `fallas.veces_correcta` → cuántas veces fue confirmada correcta
- La columna "Precisión BD" en el catálogo muestra el % en tiempo real

## API disponible
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/tree/<equipo>` | Árbol de decisiones del equipo |
| GET | `/api/equipos` | Lista de equipos |
| GET | `/api/fallas` | Catálogo de fallas con estadísticas |
| POST | `/api/sesion` | Guardar resultado de diagnóstico |
| POST | `/api/feedback` | Registrar retroalimentación |
| GET | `/api/stats` | Estadísticas globales del sistema |

## Despliegue en Railway

1. Sube este proyecto a un repositorio de GitHub (el archivo `.env` no se
   sube porque está en `.gitignore` — nunca subas tu contraseña real).
2. En [Railway](https://railway.app), crea un proyecto nuevo con
   **Deploy from GitHub repo** y selecciona este repositorio.
3. Agrega un plugin de **MySQL** desde el catálogo de Railway (botón
   "+ New" → "Database" → "MySQL").
4. En la pestaña **Variables** del servicio web, confirma que Railway
   inyectó las variables del plugin (`MYSQLHOST`, `MYSQLUSER`,
   `MYSQLPASSWORD`, `MYSQLDATABASE`, `MYSQLPORT`). `app.py` ya las lee
   automáticamente — no hace falta configurar nada manualmente.
5. Railway detecta el `Procfile` y arranca la app con `gunicorn`
   automáticamente.
6. Carga el esquema inicial: en la pestaña **Connect** del plugin de
   MySQL, copia las credenciales públicas y ejecuta `schema.sql` contra
   esa base (con MySQL Workbench o el cliente `mysql`).
7. Abre la URL pública que Railway asigna al servicio — FrostAnalitic
   debería estar corriendo ahí.
