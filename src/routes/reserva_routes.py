from flask import Blueprint, request, jsonify, g
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
from src.auth.jwt_utils import jwt_required
from src.middleware.permissions import require_admin
from src.config.database import execute_query

reserva_bp = Blueprint('reserva_bp', __name__)

@reserva_bp.route('/', methods=['POST'])
def crear_reserva_ruta():
    datos = request.get_json() or {}
    # Aceptamos que el cliente envíe 'id_turno' (número) o el par 'hora_inicio'/'hora_fin' (ej. "08:00","10:00")
    campos_requeridos = ['nombre_sala', 'edificio', 'fecha', 'participantes']
    for campo in campos_requeridos:
        if campo not in datos:
            return jsonify({'error': f'Falta el campo obligatorio: {campo}'}), 400

    # Debe suministrarse o bien id_turno o bien hora_inicio (y opcionalmente hora_fin)
    if 'id_turno' not in datos and 'hora_inicio' not in datos:
        return jsonify({'error': 'Falta el identificador de turno: envía id_turno o hora_inicio'}), 400

    try:
        fecha_reserva = datetime.strptime(datos['fecha'], '%Y-%m-%d').date()
        if fecha_reserva < datetime.now().date():
            return jsonify({'error': 'No se puede reservar para una fecha pasada.'}), 400

        # Si el cliente envió hora_inicio en lugar de id_turno, convertirla a id_turno buscando en la tabla turno
        if 'id_turno' not in datos and 'hora_inicio' in datos:
            hora_inicio = datos.get('hora_inicio')
            hora_fin = datos.get('hora_fin')
            # Buscar un turno con esas horas (comparando TIME)
            query = "SELECT id_turno FROM turno WHERE TIME(hora_inicio) = %s "
            params = [hora_inicio]
            if hora_fin:
                query += "AND TIME(hora_fin) = %s"
                params.append(hora_fin)
            query += " LIMIT 1"
            resultado = execute_query(query, tuple(params), role='readonly')
            if not resultado:
                return jsonify({'error': 'Turno no encontrado para el horario proporcionado.'}), 400
            datos['id_turno'] = resultado[0]['id_turno']

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
@jwt_required
def listar_reservas_ruta():
    ci_participante = request.args.get('ci_participante')
    nombre_sala = request.args.get('nombre_sala')

    try:
        # Control de acceso: participantes solo ven sus propias reservas
        if g.user_type != 'admin':
            ci_participante = g.user_id  # Forzar filtro por CI del participante logueado
        
        reservas = listar_reservas(ci_participante=ci_participante, nombre_sala=nombre_sala)
        from src.utils.response import with_auth_link
        return jsonify(with_auth_link({'reservas': reservas})), 200
    except Exception as e:
        return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500


@reserva_bp.route('/<int:id_reserva>', methods=['GET'])
@jwt_required
def obtener_reserva_ruta(id_reserva: int):
    try:
        reserva = obtener_reserva(id_reserva)
        if not reserva:
            return jsonify({'error': 'Reserva no encontrada'}), 404
        
        # Control de acceso: participantes solo pueden ver sus propias reservas
        if g.user_type != 'admin':
            # Verificar que el participante está en esta reserva
            query = "SELECT COUNT(*) as count FROM reserva_participante WHERE id_reserva = %s AND ci_participante = %s"
            resultado = execute_query(query, (id_reserva, g.user_id), role='readonly')
            if not resultado or resultado[0]['count'] == 0:
                return jsonify({'error': 'No tienes permiso para ver esta reserva'}), 403
        
        from src.utils.response import with_auth_link
        return jsonify(with_auth_link({'reserva': reserva})), 200
    except Exception as e:
        return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500


@reserva_bp.route('/<int:id_reserva>', methods=['PUT'])
@jwt_required
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
        # Control de acceso: verificar que el participante está en esta reserva o es admin
        if g.user_type != 'admin':
            query = "SELECT COUNT(*) as count FROM reserva_participante WHERE id_reserva = %s AND ci_participante = %s"
            resultado = execute_query(query, (id_reserva, g.user_id), role='readonly')
            if not resultado or resultado[0]['count'] == 0:
                return jsonify({'error': 'No tienes permiso para modificar esta reserva'}), 403
        
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
@jwt_required
@require_admin
def eliminar_reserva_ruta(id_reserva: int):
    try:
        filas_afectadas = eliminar_reserva(id_reserva)
        return jsonify({'reservas_eliminadas': filas_afectadas}), 200
    except Exception as e:
        return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500


@reserva_bp.route('/<int:id_reserva>/participantes/<int:ci>/asistencia', methods=['POST'])
@jwt_required
def marcar_asistencia_ruta(id_reserva: int, ci: int):
    datos = request.get_json() or {}
    if 'asistencia' not in datos:
        return jsonify({'error': 'Falta campo asistencia (true/false)'}), 400
    try:
        # Control de acceso: solo admin puede marcar asistencia
        if g.user_type != 'admin':
            return jsonify({'error': 'Solo administradores pueden marcar asistencia'}), 403
        
        asistencia = bool(datos.get('asistencia'))
        filas = marcar_asistencia(id_reserva, ci, asistencia)
        if filas == 0:
            return jsonify({'error': 'Participante o reserva no encontrada'}), 404
        return jsonify({'asistencia_actualizada': filas}), 200
    except Exception as e:
        return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500
