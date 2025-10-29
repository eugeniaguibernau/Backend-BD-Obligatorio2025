from flask import Blueprint, request, jsonify
from typing import Any, Dict
from src.models.sql_sala import (
    create_sala,
    get_sala,
    list_salas,
    update_sala,
    delete_sala,
    VALID_TIPOS,
)

sala_bp = Blueprint('sala_bp', __name__)


@sala_bp.route('/', methods=['POST'])
def create_sala_route():
    data = request.get_json() or {}
    required = ['nombre_sala', 'edificio', 'capacidad', 'tipo_sala']
    for f in required:
        if f not in data:
            return jsonify({'error': f'Missing field: {f}'}), 400

    try:
        affected = create_sala(
            data['nombre_sala'], data['edificio'], int(data['capacidad']), data['tipo_sala']
        )
        return jsonify({'created': affected}), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'internal error', 'detail': str(e)}), 500


@sala_bp.route('/', methods=['GET'])
def list_salas_route():
    edificio = request.args.get('edificio')
    tipo = request.args.get('tipo_sala')
    min_cap = request.args.get('min_capacidad')
    try:
        min_cap_int = int(min_cap) if min_cap is not None else None
    except ValueError:
        return jsonify({'error': 'min_capacidad must be integer'}), 400

    if tipo and tipo not in VALID_TIPOS:
        return jsonify({'error': f'tipo_sala must be one of {VALID_TIPOS}'}), 400

    try:
        rows = list_salas(edificio=edificio, tipo_sala=tipo, min_capacidad=min_cap_int)
        return jsonify({'salas': rows}), 200
    except Exception as e:
        return jsonify({'error': 'internal error', 'detail': str(e)}), 500


@sala_bp.route('/<edificio>/<nombre_sala>', methods=['GET'])
def get_sala_route(edificio: str, nombre_sala: str):
    try:
        row = get_sala(nombre_sala, edificio)
        if not row:
            return jsonify({'error': 'not found'}), 404
        return jsonify({'sala': row}), 200
    except Exception as e:
        return jsonify({'error': 'internal error', 'detail': str(e)}), 500


@sala_bp.route('/<edificio>/<nombre_sala>', methods=['PUT'])
def update_sala_route(edificio: str, nombre_sala: str):
    data = request.get_json() or {}
    capacidad = data.get('capacidad')
    tipo_sala = data.get('tipo_sala')
    try:
        cap_int = int(capacidad) if capacidad is not None else None
    except ValueError:
        return jsonify({'error': 'capacidad must be integer'}), 400

    try:
        affected = update_sala(nombre_sala, edificio, capacidad=cap_int, tipo_sala=tipo_sala)
        if affected == 0:
            return jsonify({'updated': 0}), 200
        return jsonify({'updated': affected}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'internal error', 'detail': str(e)}), 500


@sala_bp.route('/<edificio>/<nombre_sala>', methods=['DELETE'])
def delete_sala_route(edificio: str, nombre_sala: str):
    """
    Elimina una sala.
    
    Validaciones:
    - No se puede eliminar si tiene reservas activas o futuras
    """
    try:
        affected = delete_sala(nombre_sala, edificio)
        return jsonify({'deleted': affected}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'internal error', 'detail': str(e)}), 500
