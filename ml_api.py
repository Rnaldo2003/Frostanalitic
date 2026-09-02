"""
ml_api.py — FrostAnalitic
Rutas HTTP para la integración de Machine Learning en el diagnóstico en
vivo (ver ml_service.py para la lógica real).
"""
from flask import Blueprint, request, jsonify
from auth import roles_required
import ml_service

ml_bp = Blueprint('ml_api', __name__, url_prefix='/api/ml')


@ml_bp.route('/status')
def status():
    return jsonify(ml_service.estado_modelo())


@ml_bp.route('/predict', methods=['POST'])
def predict():
    data = request.get_json(silent=True) or {}
    equipo = data.get('equipo')
    camino = data.get('camino') or []
    resultado = ml_service.predecir_ml(equipo, camino)
    if resultado is None:
        estado = ml_service.estado_modelo()
        return jsonify({'disponible': False, **estado})
    return jsonify({'disponible': True, **resultado})


@ml_bp.route('/retrain', methods=['POST'])
@roles_required('admin', 'tecnico')
def retrain():
    resultado = ml_service.entrenar_desde_sesiones()
    codigo = 200 if resultado.get('ok') else 400
    return jsonify(resultado), codigo
