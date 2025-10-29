from flask import Blueprint, request, jsonify
from datetime import datetime
from src.models.reserva_model import (
    crear_reserva,
    listar_reservas,
    obtener_reserva,
    actualizar_reserva,
    eliminar_reserva,
    validar_reglas_negocio
)

reserva_bp = Blueprint('reserva_bp', __name__)

@reserva_bp.route('/', methods=['POST'])
def crear_reserva_ruta():
    datos = request.get_json() or {}
    campos_requeridos = ['nombre_sala', 'edificio', 'fecha', 'id_turno', 'participantes']
    for campo in campos_requeridos:
        if campo not in datos:
            return jsonify({'error': f'Falta el campo obligatorio: {campo}'}), 400

    try:
        fecha_reserva = datetime.strptime(datos['fecha'], '%Y-%m-%d').date()
        if fecha_reserva < datetime.now().date():
            return jsonify({'error': 'No se puede reservar para una fecha pasada.'}), 400

        valido, mensaje = validar_reglas_negocio(datos)
        if not valido:
            return jsonify({'error': mensaje}), 400

        id_generado = crear_reserva(
            datos['nombre_sala'],
            datos['edificio'],
            datos['fecha'],
            datos['id_turno'],
            datos['participantes']
        )
        return jsonify({'reserva_creada': id_generado}), 201

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500


@reserva_bp.route('/', methods=['GET'])
def listar_reservas_ruta():
    ci_participante = request.args.get('ci_participante')
    nombre_sala = request.args.get('nombre_sala')

    try:
        reservas = listar_reservas(ci_participante=ci_participante, nombre_sala=nombre_sala)
        return jsonify({'reservas': reservas}), 200
    except Exception as e:
        return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500


@reserva_bp.route('/<int:id_reserva>', methods=['GET'])
def obtener_reserva_ruta(id_reserva: int):
    try:
        reserva = obtener_reserva(id_reserva)
        if not reserva:
            return jsonify({'error': 'Reserva no encontrada'}), 404
        return jsonify({'reserva': reserva}), 200
    except Exception as e:
        return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500


@reserva_bp.route('/<int:id_reserva>', methods=['PUT'])
def actualizar_reserva_ruta(id_reserva: int):
    datos = request.get_json() or {}
    try:
        filas_afectadas = actualizar_reserva(id_reserva, datos)
        return jsonify({'reservas_actualizadas': filas_afectadas}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500


@reserva_bp.route('/<int:id_reserva>', methods=['DELETE'])
def eliminar_reserva_ruta(id_reserva: int):
    try:
        filas_afectadas = eliminar_reserva(id_reserva)
        return jsonify({'reservas_eliminadas': filas_afectadas}), 200
    except Exception as e:
        return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500
