"""
ml_service.py — FrostAnalitic
Integra un modelo de Machine Learning al diagnóstico EN VIVO, entrenado
con datos REALES (sesiones con retroalimentación), no solo con el dataset
sintético de `ds/`.

Por qué no reutilizamos directamente ds/output/frost_model.pkl:
    Ese modelo se entrenó sobre un vocabulario cerrado de "síntomas"
    sintéticos (ds/simulate_data.py) que no existe en el flujo real de la
    app (el usuario responde preguntas de texto libre del árbol, no elige
    un código de síntoma de una lista fija). Reutilizar sus encoders con
    entradas reales daría predicciones sin sentido.

    En su lugar, este módulo entrena su PROPIO modelo ("modelo real") a
    partir de las sesiones ya registradas en la base de datos, usando el
    camino de preguntas/respuestas de cada sesión como texto, vectorizado
    con HashingVectorizer (no necesita guardar un vocabulario: la misma
    función determinista sirve para entrenar y para predecir). El modelo
    sintético de ds/ se conserva tal cual para el análisis comparativo de
    la pestaña Estadísticas (esa es su función: mostrar en la tesis que un
    modelo de ML supera al árbol de reglas fijo en un dataset controlado).
"""
import os
import pickle
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE, 'ds', 'output')
MODEL_REAL_PATH = os.path.join(OUT_DIR, 'frost_model_real.pkl')

N_FEATURES = 256
MIN_MUESTRAS = 25  # mínimo de sesiones con feedback para poder entrenar

_vectorizer = HashingVectorizer(n_features=N_FEATURES, alternate_sign=False, norm=None)
_modelo_cache = None  # se carga perezosamente (lazy) al primer uso


def _camino_a_texto(equipo_nombre, camino):
    partes = [f"equipo={equipo_nombre or ''}"]
    for paso in (camino or []):
        partes.append(f"{paso.get('pregunta', '')}::{paso.get('resp', '')}")
    return ' | '.join(partes)


def _vectorizar(equipo_nombre, camino):
    return _vectorizer.transform([_camino_a_texto(equipo_nombre, camino)])


def _construir_dataset_real():
    from models.models import Sesion, Equipo
    equipos = {e.id: e.nombre for e in Equipo.query.all()}
    filas = Sesion.query.filter(Sesion.fue_correcto.isnot(None)).all()
    textos, etiquetas = [], []
    for s in filas:
        etiqueta = s.falla_real_id if (s.fue_correcto is False and s.falla_real_id) else s.falla_id
        if not etiqueta:
            continue
        textos.append(_camino_a_texto(equipos.get(s.equipo_id), s.camino_json or []))
        etiquetas.append(int(etiqueta))
    return textos, etiquetas


def entrenar_desde_sesiones():
    """Reentrena el modelo de IA en vivo con las sesiones reales que ya
    tienen retroalimentación. Guarda el modelo en disco y lo deja listo
    para usarse inmediatamente (sin reiniciar la app)."""
    global _modelo_cache
    textos, etiquetas = _construir_dataset_real()

    if len(textos) < MIN_MUESTRAS:
        return {
            'ok': False,
            'error': f'Se necesitan al menos {MIN_MUESTRAS} sesiones con retroalimentación '
                     f'para entrenar (hay {len(textos)}).',
        }
    clases_distintas = sorted(set(etiquetas))
    if len(clases_distintas) < 2:
        return {'ok': False, 'error': 'Se necesitan al menos 2 fallas distintas en los datos reales.'}

    X = _vectorizer.transform(textos)
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X, etiquetas, test_size=0.2, random_state=42, stratify=etiquetas
        )
    except ValueError:
        # Muy pocas muestras de alguna clase para estratificar: se entrena
        # con todo y se evalúa sobre el mismo conjunto (solo informativo).
        X_train, X_test, y_train, y_test = X, X, etiquetas, etiquetas

    modelo = RandomForestClassifier(n_estimators=150, random_state=42, min_samples_leaf=1)
    modelo.fit(X_train, y_train)
    accuracy = round(accuracy_score(y_test, modelo.predict(X_test)) * 100, 1) if y_test else None

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(MODEL_REAL_PATH, 'wb') as f:
        pickle.dump({'modelo': modelo, 'n_features': N_FEATURES, 'entrenado_con': len(textos)}, f)
    _modelo_cache = modelo

    return {
        'ok': True,
        'muestras_entrenamiento': len(textos),
        'clases_distintas': len(clases_distintas),
        'accuracy_validacion': accuracy,
    }


def _cargar_modelo():
    global _modelo_cache
    if _modelo_cache is not None:
        return _modelo_cache
    if os.path.exists(MODEL_REAL_PATH):
        try:
            with open(MODEL_REAL_PATH, 'rb') as f:
                _modelo_cache = pickle.load(f)['modelo']
        except Exception:
            _modelo_cache = None
    return _modelo_cache


def estado_modelo():
    """Info pública sobre si hay un modelo de IA en vivo disponible."""
    textos, _ = _construir_dataset_real()
    modelo = _cargar_modelo()
    return {
        'disponible': modelo is not None,
        'sesiones_con_feedback': len(textos),
        'minimo_requerido': MIN_MUESTRAS,
        'listo_para_entrenar': len(textos) >= MIN_MUESTRAS,
    }


def predecir_ml(equipo_nombre, camino):
    """Devuelve el top-3 de fallas según el modelo de IA en vivo, o None
    si todavía no existe un modelo entrenado con datos reales."""
    modelo = _cargar_modelo()
    if modelo is None:
        return None
    from models.models import Falla

    vector = _vectorizar(equipo_nombre, camino)
    try:
        probabilidades = modelo.predict_proba(vector)[0]
        clases = modelo.classes_
        top = sorted(zip(clases, probabilidades), key=lambda par: -par[1])[:3]
    except Exception:
        return None

    predicciones = []
    for falla_id, prob in top:
        falla = Falla.query.get(int(falla_id))
        predicciones.append({
            'falla_id': int(falla_id),
            'nombre': falla.nombre if falla else f'Falla #{falla_id}',
            'prob': round(float(prob) * 100, 1),
        })
    return {'predicciones': predicciones}
