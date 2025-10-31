from flask import Blueprint, request, jsonify
from datetime import datetime
from src.models.reserva_model import (
    crear_reserva,
    listar_reservas,
    obtener_reserva,
    actualizar_reserva,
    eliminar_reserva,
    validar_reglas_negocio,
    marcar_asistencia
)
from src.models.sancion_model import aplicar_sanciones_por_reserva

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
        from src.utils.response import with_auth_link
        return jsonify(with_auth_link({'reservas': reservas})), 200
    except Exception as e:
        return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500


@reserva_bp.route('/<int:id_reserva>', methods=['GET'])
def obtener_reserva_ruta(id_reserva: int):
    try:
        reserva = obtener_reserva(id_reserva)
        if not reserva:
            return jsonify({'error': 'Reserva no encontrada'}), 404
        from src.utils.response import with_auth_link
        return jsonify(with_auth_link({'reserva': reserva})), 200
    except Exception as e:
        return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500


@reserva_bp.route('/<int:id_reserva>', methods=['PUT'])
def actualizar_reserva_ruta(id_reserva: int):
    """
    Actualiza una reserva. Si el body incluye 'estado' con alguno de:
    - 'sin asistencia'  (regla: sanción solo si NADIE asistió)
    - 'finalizada'      (opcional: lo tratamos como cierre y revisamos sanción)
    - 'cerrada'         (opcional: idem)
    entonces se evalúa y aplican sanciones según la regla pedida.
    """
    datos = request.get_json() or {}
    try:
        # 1) Actualizamos la reserva
        filas_afectadas = actualizar_reserva(id_reserva, datos)

        # 2) Si el estado nuevo indica cierre/ausencia, aplicamos la regla de sanción
        estado_nuevo = (datos.get('estado') or '').strip().lower()
        debe_aplicar_sancion = estado_nuevo in ('sin asistencia', 'finalizada', 'cerrada')

        respuesta = {'reservas_actualizadas': filas_afectadas}

        if debe_aplicar_sancion:
            try:
                resultado = aplicar_sanciones_por_reserva(id_reserva, sancion_dias=7)
                respuesta['sanciones'] = {
                    'aplicadas': resultado.get('insertadas', 0),
                    'sancionados': resultado.get('sancionados', []),
                    'fecha_inicio': str(resultado.get('fecha_inicio')),
                    'fecha_fin': str(resultado.get('fecha_fin')),
                    'motivo': resultado.get('motivo')
                }
            except ValueError as e:
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                respuesta['sanciones_error'] = str(e)

        return jsonify(respuesta), 200

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


@reserva_bp.route('/<int:id_reserva>/participantes/<int:ci>/asistencia', methods=['POST'])
def marcar_asistencia_ruta(id_reserva: int, ci: int):
    datos = request.get_json() or {}
    if 'asistencia' not in datos:
        return jsonify({'error': 'Falta campo asistencia (true/false)'}), 400
    try:
        asistencia = bool(datos.get('asistencia'))
        filas = marcar_asistencia(id_reserva, ci, asistencia)
        if filas == 0:
            return jsonify({'error': 'Participante o reserva no encontrada'}), 404
        return jsonify({'asistencia_actualizada': filas}), 200
    except Exception as e:
        return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500
