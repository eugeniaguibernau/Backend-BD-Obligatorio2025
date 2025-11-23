from flask import Blueprint, request, jsonify, g
from datetime import datetime, date, timedelta
from src.models.reserva_model import (
    crear_reserva,
    listar_reservas,
    obtener_reserva,
    actualizar_reserva,
    eliminar_reserva,
    validar_reglas_negocio,
    crear_reservas_batch,
    marcar_asistencia
)
from src.models.sancion_model import aplicar_sanciones_por_reserva, eliminar_sancion
from src.auth.jwt_utils import jwt_required
from src.middleware.permissions import require_admin
from src.config.database import execute_query, execute_non_query

reserva_bp = Blueprint('reserva_bp', __name__)


def _compute_estado_actual(reserva):
    """Devuelve el estado actual calculado para mostrar en el frontend.

    Estados posibles:
    - 'activa' (fecha futura o turno de hoy sin finalizar)
    - 'asistida' (hubo asistencia registrada)
    - 'sin asistencia' (nadie asistió y ya terminó el turno)
    - 'cancelada' (si está cancelada en la base de datos)
    - cualquier otro estado almacenado se devuelve tal cual
    """

    estado_guardado = (reserva.get('estado') or '').strip().lower()
    if estado_guardado == 'cancelada':
        return 'cancelada'

    # Intentar obtener hora_fin desde turno si falta
    hora_fin = reserva.get('hora_fin')
    if not hora_fin and 'turno' in reserva and reserva['turno'] and 'hora_fin' in reserva['turno']:
        hora_fin = reserva['turno']['hora_fin']
        reserva['hora_fin'] = hora_fin

    # Si el estado guardado es distinto de 'activa', tratar casos especiales:
    # - 'finalizada' y hay asistencia: devolver 'asistida'
    # - 'finalizada' y NO hubo asistencia: devolver 'sin asistencia'
    # - otros estados no-activa: devolver tal cual
    if estado_guardado and estado_guardado != 'activa':
        if estado_guardado == 'finalizada':
            # Revisar asistencia para distinguir entre 'asistida' y 'sin asistencia'
            try:
                resultado_true = execute_query(
                    "SELECT COUNT(*) as c FROM reserva_participante WHERE id_reserva=%s AND asistencia=1",
                    (reserva.get('id_reserva'),),
                    role='readonly'
                )
                cnt_true = resultado_true[0]['c'] if resultado_true else 0
                if cnt_true and cnt_true > 0:
                    return 'asistida'
                # Si la reserva es de hoy y la hora_fin no ha pasado, debe seguir activa
                fecha_res = reserva.get('fecha')
                try:
                    if isinstance(fecha_res, str):
                        fecha_obj = datetime.strptime(fecha_res, '%Y-%m-%d').date()
                    elif isinstance(fecha_res, date):
                        fecha_obj = fecha_res
                    else:
                        fecha_obj = date.fromisoformat(str(fecha_res))
                except Exception:
                    return 'sin asistencia'
                hoy = datetime.now().date()
                ahora = datetime.now()
                if fecha_obj == hoy and hora_fin:
                    hf = hora_fin
                    if isinstance(hf, str) and len(hf.split(':')) == 2:
                        hf = hf + ':00'
                    try:
                        hora_fin_dt = datetime.combine(hoy, datetime.strptime(hf, '%H:%M:%S').time())
                        if ahora < hora_fin_dt:
                            return 'activa'
                    except Exception:
                        pass
                return 'sin asistencia'
            except Exception:
                return estado_guardado
        # Si la reserva es de hoy y la hora_fin no ha pasado, debe seguir activa
        fecha_res = reserva.get('fecha')
        try:
            if isinstance(fecha_res, str):
                fecha_obj = datetime.strptime(fecha_res, '%Y-%m-%d').date()
            elif isinstance(fecha_res, date):
                fecha_obj = fecha_res
            else:
                fecha_obj = date.fromisoformat(str(fecha_res))
        except Exception:
            return estado_guardado
        hoy = datetime.now().date()
        ahora = datetime.now()
        if fecha_obj == hoy and hora_fin:
            hf = hora_fin
            if isinstance(hf, str) and len(hf.split(':')) == 2:
                hf = hf + ':00'
            try:
                hora_fin_dt = datetime.combine(hoy, datetime.strptime(hf, '%H:%M:%S').time())
                if ahora < hora_fin_dt:
                    return 'activa'
            except Exception:
                pass
        return estado_guardado

    # Solo calcular para reservas que en la base están como 'activa' (o sin estado)
    fecha_res = reserva.get('fecha')
    try:
        if isinstance(fecha_res, str):
            fecha_obj = datetime.strptime(fecha_res, '%Y-%m-%d').date()
        elif isinstance(fecha_res, date):
            fecha_obj = fecha_res
        else:
            # Si es otro tipo, intentar convertir directamente
            fecha_obj = date.fromisoformat(str(fecha_res))
    except Exception:
        # En caso de error, retornar el estado guardado
        return estado_guardado or 'activa'

    hoy = datetime.now().date()
    ahora = datetime.now()
    if fecha_obj > hoy:
        return 'activa'

    # Si la reserva es de hoy, verificar hora_fin del turno
    if fecha_obj == hoy:
        hora_fin = None
        # Intentar obtener hora_fin del turno
        if 'hora_fin' in reserva and reserva['hora_fin']:
            hora_fin = reserva['hora_fin']
        elif 'turno' in reserva and reserva['turno'] and 'hora_fin' in reserva['turno']:
            hora_fin = reserva['turno']['hora_fin']
        if hora_fin:
            # Normalizar formato HH:MM o HH:MM:SS
            if isinstance(hora_fin, str) and len(hora_fin.split(':')) == 2:
                hora_fin = hora_fin + ':00'
            try:
                hora_fin_dt = datetime.combine(hoy, datetime.strptime(hora_fin, '%H:%M:%S').time())
                if ahora < hora_fin_dt:
                    return 'activa'
            except Exception as e:
                pass  # Si falla el parseo, sigue con la lógica vieja

    # Fecha pasada o (hoy y ya terminó el turno o no hay info de hora_fin)
    resultado_true = execute_query(
        "SELECT COUNT(*) as c FROM reserva_participante WHERE id_reserva=%s AND asistencia=1",
        (reserva.get('id_reserva'),),
        role='readonly'
    )
    cnt_true = resultado_true[0]['c'] if resultado_true else 0
    if cnt_true and cnt_true > 0:
        return 'asistida'

    # Ninguno asistió/registrado
    return 'sin asistencia'
    # Si ya fue marcada cancelada, respetamos el valor almacenado
    estado_guardado = (reserva.get('estado') or '').strip().lower()
    if estado_guardado == 'cancelada':
        return 'cancelada'

    # Si el estado guardado es distinto de 'activa', tratar casos especiales:
    # - 'finalizada' y hay asistencia: devolver 'asistida'
    # - 'finalizada' y NO hubo asistencia: devolver 'sin asistencia'
    # - otros estados no-activa: devolver tal cual
    if estado_guardado and estado_guardado != 'activa':
        if estado_guardado == 'finalizada':
            # revisar asistencia para distinguir entre 'asistida' y 'sin asistencia'
            try:
                resultado_true = execute_query(
                    "SELECT COUNT(*) as c FROM reserva_participante WHERE id_reserva=%s AND asistencia=1",
                    (reserva.get('id_reserva'),),
                    role='readonly'
                )
                cnt_true = resultado_true[0]['c'] if resultado_true else 0
                if cnt_true and cnt_true > 0:
                    return 'asistida'
                return 'sin asistencia'
            except Exception:
                # En caso de error consultando asistencia, devolvemos el estado guardado
                return estado_guardado
        return estado_guardado

    # Solo calculamos para reservas que en DB están como 'activa' (o sin estado)
    fecha_res = reserva.get('fecha')
    try:
        if isinstance(fecha_res, str):
            fecha_obj = datetime.strptime(fecha_res, '%Y-%m-%d').date()
        elif isinstance(fecha_res, date):
            fecha_obj = fecha_res
        else:
            # si es otro tipo, intentar convertir directamente
            fecha_obj = date.fromisoformat(str(fecha_res))
    except Exception:
        # En caso de error, retornamos el estado guardado
        return estado_guardado or 'activa'

    hoy = datetime.now().date()
    ahora = datetime.now()
    print(f"[DEBUG] hoy: {hoy} ahora: {ahora}")
    if fecha_obj > hoy:
        print("[DEBUG] Estado calculado: activa (fecha futura)")
        return 'activa'

    # Si la reserva es de hoy, verificar hora_fin del turno
    if fecha_obj == hoy:
        hora_fin = None
        # Intentar obtener hora_fin del turno
        if 'hora_fin' in reserva and reserva['hora_fin']:
            hora_fin = reserva['hora_fin']
        elif 'turno' in reserva and reserva['turno'] and 'hora_fin' in reserva['turno']:
            hora_fin = reserva['turno']['hora_fin']
        print(f"[DEBUG] hora_fin usada para comparación: {hora_fin}")
        if hora_fin:
            # Normalizar formato HH:MM o HH:MM:SS
            if isinstance(hora_fin, str) and len(hora_fin.split(':')) == 2:
                hora_fin = hora_fin + ':00'
            try:
                hora_fin_dt = datetime.combine(hoy, datetime.strptime(hora_fin, '%H:%M:%S').time())
                print(f"[DEBUG] hora_fin_dt: {hora_fin_dt}")
                if ahora < hora_fin_dt:
                    print("[DEBUG] Estado calculado: activa (hoy, antes de hora_fin)")
                    return 'activa'
            except Exception as e:
                print(f"[DEBUG] Error parseando hora_fin: {e}")
                pass  # Si falla el parseo, sigue con la lógica vieja

    # Fecha pasada o (hoy y ya terminó el turno o no hay info de hora_fin)
    resultado_true = execute_query(
        "SELECT COUNT(*) as c FROM reserva_participante WHERE id_reserva=%s AND asistencia=1",
        (reserva.get('id_reserva'),),
        role='readonly'
    )
    cnt_true = resultado_true[0]['c'] if resultado_true else 0
    if cnt_true and cnt_true > 0:
        return 'asistida'

    # Ninguno asistió/registrado
    return 'sin asistencia'


@reserva_bp.route('/', methods=['POST'])
def crear_reserva_ruta():
    datos = request.get_json() or {}
    # Aceptamos que el cliente envíe 'turnos' (array) o 'id_turno' (número único) para retrocompatibilidad
    campos_requeridos = ['nombre_sala', 'edificio', 'fecha', 'participantes']
    for campo in campos_requeridos:
        if campo not in datos:
            return jsonify({'error': f'Falta el campo obligatorio: {campo}'}), 400

    # participantes debe ser una lista no vacía
    if not isinstance(datos.get('participantes'), list) or len(datos.get('participantes')) == 0:
        return jsonify({'error': 'participantes debe ser una lista no vacía con los CI de los participantes'}), 400

    # Debe suministrarse 'turnos' (array), 'id_turno' (número) o 'hora_inicio'
    if 'turnos' not in datos and 'id_turno' not in datos and 'hora_inicio' not in datos:
        return jsonify({'error': 'Falta el identificador de turno: envía turnos (array), id_turno o hora_inicio'}), 400

    try:
        fecha_reserva = datetime.strptime(datos['fecha'], '%Y-%m-%d').date()
        if fecha_reserva < datetime.now().date():
            return jsonify({'error': 'No se puede reservar para una fecha pasada.'}), 400

        # Normalizar entrada: convertir a lista de id_turno
        turnos_a_reservar = []
        
        # Caso 1: Array de turnos (nuevo formato)
        if 'turnos' in datos:
            if not isinstance(datos['turnos'], list) or len(datos['turnos']) == 0:
                return jsonify({'error': 'turnos debe ser una lista no vacía'}), 400
            
            for turno_item in datos['turnos']:
                # Puede ser un número (id_turno) o un objeto con hora_inicio/hora_fin
                if isinstance(turno_item, (int, float)):
                    turnos_a_reservar.append(int(turno_item))
                elif isinstance(turno_item, dict):
                    # Convertir hora_inicio/hora_fin a id_turno
                    id_turno_convertido = _convertir_hora_a_id_turno(turno_item)
                    if id_turno_convertido:
                        turnos_a_reservar.append(id_turno_convertido)
                    else:
                        return jsonify({'error': f'No se encontró turno para {turno_item}'}), 400
                else:
                    return jsonify({'error': 'Formato de turno inválido en array turnos'}), 400
        
        # Caso 2: id_turno único (retrocompatibilidad)
        elif 'id_turno' in datos:
            turnos_a_reservar.append(int(datos['id_turno']))
        
        # Caso 3: hora_inicio/hora_fin (retrocompatibilidad)
        elif 'hora_inicio' in datos:
            id_turno_convertido = _convertir_hora_a_id_turno(datos)
            if id_turno_convertido:
                turnos_a_reservar.append(id_turno_convertido)
            else:
                return jsonify({'error': 'Turno no encontrado para el horario proporcionado'}), 400

        if not turnos_a_reservar:
            return jsonify({'error': 'No se especificaron turnos válidos'}), 400

        # Validación adicional: si la reserva es para HOY no permitimos crear
        # una reserva para un turno que ya finalizó (hora_fin <= ahora).
        # Esto evita que el cliente cree reservas para horarios ya pasados del mismo día.
        try:
            hoy = datetime.now().date()
            ahora = datetime.now()
            if fecha_reserva == hoy:
                for id_turno in turnos_a_reservar:
                    resultado_turno = execute_query(
                        "SELECT TIME(hora_fin) as hora_fin FROM turno WHERE id_turno = %s",
                        (id_turno,),
                        role='readonly'
                    )
                    if not resultado_turno or not resultado_turno[0].get('hora_fin'):
                        # si no tenemos info del turno no bloqueamos aquí, dejamos validar_reglas_negocio
                        continue
                    hf = resultado_turno[0].get('hora_fin')
                    # hf puede ser datetime.time o string 'HH:MM:SS'
                    hf_s = str(hf)
                    if len(hf_s.split(':')) == 2:
                        hf_s = hf_s + ':00'
                    try:
                        fin_dt = datetime.strptime(f"{fecha_reserva} {hf_s}", '%Y-%m-%d %H:%M:%S')
                        if ahora >= fin_dt:
                            return jsonify({'error': f'No se puede reservar: el turno {id_turno} ya finalizó en la fecha seleccionada.'}), 400
                    except Exception:
                        # si parse falla, no bloquear aquí
                        pass
        except Exception:
            # en caso de cualquier fallo de esta comprobación seguimos con el flujo normal
            pass

        # Crear las reservas en batch (validación atómica + inserción)
        try:
            reservas_creadas = crear_reservas_batch(
                datos['nombre_sala'],
                datos['edificio'],
                datos['fecha'],
                turnos_a_reservar,
                datos['participantes']
            )
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

        # Respuesta
        if len(reservas_creadas) == 1:
            # Retrocompatibilidad: si es una sola reserva, devolver como antes
            return jsonify({'reserva_creada': reservas_creadas[0]['id_reserva']}), 201
        else:
            # Múltiples reservas
            return jsonify({
                'ok': True,
                'reservas_creadas': reservas_creadas,
                'total': len(reservas_creadas)
            }), 201

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500


def _convertir_hora_a_id_turno(datos):
    """Helper para convertir hora_inicio/hora_fin a id_turno"""
    hora_inicio = datos.get('hora_inicio')
    hora_fin = datos.get('hora_fin')
    
    if not hora_inicio:
        return None
    
    # normalizar formato HH:MM -> HH:MM:00 para comparar con TIME() en SQL
    if isinstance(hora_inicio, str) and len(hora_inicio.split(':')) == 2:
        hora_inicio = hora_inicio + ':00'
    if hora_fin and isinstance(hora_fin, str) and len(hora_fin.split(':')) == 2:
        hora_fin = hora_fin + ':00'
    
    # Buscar un turno con esas horas (comparando TIME)
    query = "SELECT id_turno FROM turno WHERE TIME(hora_inicio) = %s "
    params = [hora_inicio]
    if hora_fin:
        query += "AND TIME(hora_fin) = %s"
        params.append(hora_fin)
    query += " LIMIT 1"
    
    resultado = execute_query(query, tuple(params), role='readonly')
    if not resultado:
        return None
    
    return resultado[0]['id_turno']


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
        # Asegurar que cada reserva tenga hora_fin (para el cálculo correcto del estado)
        for r in reservas:
            # Asegurar que siempre haya id_turno y hora_fin
            id_turno = r.get('id_turno')
            if not id_turno and 'turno' in r and r['turno'] and 'id_turno' in r['turno']:
                id_turno = r['turno']['id_turno']
                r['id_turno'] = id_turno
            if (not r.get('hora_fin')) and id_turno:
                resultado_turno = execute_query(
                    "SELECT TIME(hora_fin) as hora_fin FROM turno WHERE id_turno = %s",
                    (id_turno,),
                    role='readonly'
                )
                if resultado_turno and resultado_turno[0].get('hora_fin'):
                    r['hora_fin'] = str(resultado_turno[0]['hora_fin'])
            try:
                r['estado_actual'] = _compute_estado_actual(r)
            except Exception:
                r['estado_actual'] = r.get('estado', 'activa')
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
        
        # Asegurar que siempre haya id_turno y hora_fin
        id_turno = reserva.get('id_turno')
        if not id_turno and 'turno' in reserva and reserva['turno'] and 'id_turno' in reserva['turno']:
            id_turno = reserva['turno']['id_turno']
            reserva['id_turno'] = id_turno
        if (not reserva.get('hora_fin')) and id_turno:
            resultado_turno = execute_query(
                "SELECT TIME(hora_fin) as hora_fin FROM turno WHERE id_turno = %s",
                (id_turno,),
                role='readonly'
            )
            if resultado_turno and resultado_turno[0].get('hora_fin'):
                reserva['hora_fin'] = str(resultado_turno[0]['hora_fin'])
        try:
            reserva['estado_actual'] = _compute_estado_actual(reserva)
        except Exception:
            reserva['estado_actual'] = reserva.get('estado', 'activa')
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
    - 'finalizada'      (opcional: lo tratamos como cierre)
    - 'asistida'        (indica que hubo asistencia y NO se deben generar sanciones)
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

        # Mapear 'asistida' -> 'finalizada' antes de guardar si el cliente lo pidió,
        # para evitar tocar el ENUM de la BD. Devolvemos el valor solicitado en la respuesta.
        estado_solicitado = (datos.get('estado') or '').strip().lower()
        if estado_solicitado == 'asistida':
            datos['estado'] = 'finalizada'

        # Guard extra: evitar que participantes marquen 'sin asistencia' antes de que termine el turno
        if estado_solicitado == 'sin asistencia' and g.user_type != 'admin':
            reserva_info = obtener_reserva(id_reserva)
            fecha_res = reserva_info.get('fecha')
            hora_fin = None
            if 'hora_fin' in reserva_info and reserva_info['hora_fin']:
                hora_fin = reserva_info['hora_fin']
            elif 'turno' in reserva_info and reserva_info['turno'] and 'hora_fin' in reserva_info['turno']:
                hora_fin = reserva_info['turno']['hora_fin']
            hoy = datetime.now().date()
            ahora = datetime.now()
            if fecha_res == hoy and hora_fin:
                if isinstance(hora_fin, str) and len(hora_fin.split(':')) == 2:
                    hora_fin = hora_fin + ':00'
                try:
                    hora_fin_dt = datetime.combine(hoy, datetime.strptime(hora_fin, '%H:%M:%S').time())
                    if ahora < hora_fin_dt:
                        return jsonify({'error': 'No se puede marcar sin asistencia antes de que finalice el turno', 'code': 'TURN_NOT_FINISHED'}), 403
                except Exception:
                    return jsonify({'error': 'No se puede marcar sin asistencia: información de turno incompleta', 'code': 'NO_TURNO_INFO'}), 403
            elif fecha_res == hoy and not hora_fin:
                return jsonify({'error': 'No se puede marcar sin asistencia: información de turno incompleta', 'code': 'NO_TURNO_INFO'}), 403

        # Si se intenta marcar como 'sin asistencia' o 'finalizada' antes de hora_fin, forzar estado 'activa'
        estado_solicitado = (datos.get('estado') or '').strip().lower()
        if estado_solicitado in ('sin asistencia', 'finalizada'):
            reserva_info = obtener_reserva(id_reserva)
            fecha_res = reserva_info.get('fecha')
            # Ensure fecha_res is a datetime.date
            if isinstance(fecha_res, str):
                try:
                    fecha_res = datetime.strptime(fecha_res, '%Y-%m-%d').date()
                except Exception:
                    fecha_res = None
            hora_fin = None
            if 'hora_fin' in reserva_info and reserva_info['hora_fin']:
                hora_fin = reserva_info['hora_fin']
            elif 'turno' in reserva_info and reserva_info['turno'] and 'hora_fin' in reserva_info['turno']:
                hora_fin = reserva_info['turno']['hora_fin']
            hoy = datetime.now().date()
            ahora = datetime.now()
            if fecha_res == hoy and hora_fin:
                if isinstance(hora_fin, str) and len(hora_fin.split(':')) == 2:
                    hora_fin = hora_fin + ':00'
                try:
                    hora_fin_dt = datetime.combine(hoy, datetime.strptime(hora_fin, '%H:%M:%S').time())
                    if ahora < hora_fin_dt:
                        return jsonify({'error': 'No se puede marcar sin asistencia ni finalizar antes de que termine el turno', 'code': 'TURN_NOT_FINISHED'}), 403
                except Exception:
                    return jsonify({'error': 'No se puede marcar sin asistencia: información de turno incompleta', 'code': 'NO_TURNO_INFO'}), 403
            elif fecha_res and fecha_res > hoy:
                return jsonify({'error': 'No se puede marcar sin asistencia ni finalizar una reserva a futuro', 'code': 'FUTURE_RESERVA'}), 403
        # Actualizar la reserva en la BD
        filas_afectadas = actualizar_reserva(id_reserva, datos)

        # Construir respuesta básica
        respuesta = {
            'reservas_actualizadas': filas_afectadas,
            'estado_aplicado': estado_solicitado or None
        }

        # Si el usuario pidió explícitamente 'asistida', marcar asistencia en reserva_participante
        # para reflejar que hubo asistencia y evitar generación de sanciones.
        if estado_solicitado == 'asistida':
            try:
                updated = execute_non_query(
                    "UPDATE reserva_participante SET asistencia = 1 WHERE id_reserva = %s",
                    (id_reserva,)
                )
                respuesta['asistencia_marcada'] = updated
            except Exception as e:
                # No detener el proceso por este fallo; devolver un campo con el error para diagnóstico
                respuesta['asistencia_marcada_error'] = str(e)
            # Además, eliminar sanciones previamente creadas para los participantes
            # (posible escenario: el procesador vencido ya aplicó sanciones; si ahora se marca
            # como asistida, debemos removerlas). Usamos la misma ventana por defecto de 60 días.
            try:
                reserva_info = obtener_reserva(id_reserva)
                if reserva_info and reserva_info.get('fecha'):
                    # normalizar fecha a date
                    fecha_res = reserva_info.get('fecha')
                    if isinstance(fecha_res, str):
                        fecha_res = datetime.strptime(fecha_res, '%Y-%m-%d').date()
                    fecha_fin = fecha_res + timedelta(days=60)

                    # obtener participantes
                    participantes = execute_query(
                        "SELECT ci_participante FROM reserva_participante WHERE id_reserva = %s",
                        (id_reserva,),
                        role='readonly'
                    )
                    eliminadas = 0
                    eliminados_list = []
                    for p in participantes:
                        ci = p.get('ci_participante')
                        try:
                            filas = eliminar_sancion(ci, fecha_res, fecha_fin)
                            if filas:
                                eliminadas += filas
                                eliminados_list.append(ci)
                        except Exception:
                            # ignorar fallos individuales para no abortar la operación
                            pass
                    respuesta['sanciones_eliminadas'] = eliminadas
                    respuesta['sancionados_eliminados_ci'] = eliminados_list
                else:
                    respuesta['sanciones_eliminadas_error'] = 'Fecha de reserva no encontrada'
            except Exception as e:
                respuesta['sanciones_eliminadas_error'] = str(e)

        # Decidir si debemos aplicar sanciones según el estado que se guardó
        estado_nuevo = (datos.get('estado') or '').strip().lower()
        debe_aplicar_sancion = estado_nuevo in ('sin asistencia', 'cerrada')

        # Solo aplicar sanción si el turno ya terminó (hora_fin < ahora)
        aplicar_sancion = False
        if debe_aplicar_sancion:
            reserva_info = obtener_reserva(id_reserva)
            fecha_res = reserva_info.get('fecha')
            # Ensure fecha_res is a datetime.date
            if isinstance(fecha_res, str):
                try:
                    fecha_res = datetime.strptime(fecha_res, '%Y-%m-%d').date()
                except Exception:
                    fecha_res = None
            hora_fin = None
            if 'hora_fin' in reserva_info and reserva_info['hora_fin']:
                hora_fin = reserva_info['hora_fin']
            elif 'turno' in reserva_info and reserva_info['turno'] and 'hora_fin' in reserva_info['turno']:
                hora_fin = reserva_info['turno']['hora_fin']
            hoy = datetime.now().date()
            ahora = datetime.now()
            turno_ya_termino = True
            if fecha_res == hoy and hora_fin:
                if isinstance(hora_fin, str) and len(hora_fin.split(':')) == 2:
                    hora_fin = hora_fin + ':00'
                try:
                    hora_fin_dt = datetime.combine(hoy, datetime.strptime(hora_fin, '%H:%M:%S').time())
                    if ahora >= hora_fin_dt:
                        turno_ya_termino = True
                    else:
                        turno_ya_termino = False
                except Exception:
                    turno_ya_termino = True  # Si no se puede parsear, por seguridad aplicar sanción
            elif fecha_res == hoy and not hora_fin:
                turno_ya_termino = False  # No hay info de hora_fin, no aplicar sanción aún
            if fecha_res and fecha_res > hoy:
                turno_ya_termino = False  # Es una reserva a futuro
            if turno_ya_termino:
                aplicar_sancion = True

        if aplicar_sancion:
            try:
                resultado = aplicar_sanciones_por_reserva(id_reserva, sancion_dias=60)
                respuesta['sanciones'] = {
                    'aplicadas': resultado.get('insertadas', 0),
                    'sancionados': resultado.get('sancionados', []),
                    'fecha_inicio': str(resultado.get('fecha_inicio')) if resultado.get('fecha_inicio') else None,
                    'fecha_fin': str(resultado.get('fecha_fin')) if resultado.get('fecha_fin') else None,
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
        import traceback
        print('--- Exception in actualizar_reserva_ruta ---')
        print(traceback.format_exc())
        return jsonify({'error': 'Error interno', 'detalle': str(e), 'traceback': traceback.format_exc()}), 500


@reserva_bp.route('/<int:id_reserva>', methods=['DELETE'])
@jwt_required
def eliminar_reserva_ruta(id_reserva: int):
    """Permitir que el participante dueño de la reserva o un admin eliminen la reserva.

    Para usuarios no-admin se respeta la ventana mínima de cancelación (2 días).
    """
    CANCEL_DIAS = 2
    try:
        # Si no es admin, verificar que el participante forma parte de la reserva
        if g.user_type != 'admin':
            resultado = execute_query(
                "SELECT COUNT(*) as c FROM reserva_participante WHERE id_reserva=%s AND ci_participante=%s",
                (id_reserva, g.user_id),
                role='readonly'
            )
            if not resultado or resultado[0]['c'] == 0:
                return jsonify({'error': 'No tienes permiso para eliminar esta reserva'}), 403

            # verificar ventana minima de cancelación
            reserva = obtener_reserva(id_reserva)
            if not reserva:
                return jsonify({'error': 'Reserva no encontrada'}), 404
            fecha_reserva = reserva.get('fecha')
            if isinstance(fecha_reserva, str):
                fecha_reserva = datetime.strptime(fecha_reserva, '%Y-%m-%d').date()
            dias_anticipacion = (fecha_reserva - datetime.now().date()).days
            if dias_anticipacion < CANCEL_DIAS:
                return jsonify({'error': f'No se puede cancelar con menos de {CANCEL_DIAS} días de anticipación'}), 400

        filas_afectadas = eliminar_reserva(id_reserva)
        return jsonify({'reservas_eliminadas': filas_afectadas}), 200
    except Exception as e:
        return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500


@reserva_bp.route('/<int:id_reserva>/participantes', methods=['GET'])
@jwt_required
def listar_participantes_reserva(id_reserva: int):
    """
    GET /reservas/{id_reserva}/participantes
    Lista todos los participantes de una reserva con su estado de asistencia.
    """
    try:
        # Verificar que la reserva existe
        reserva = obtener_reserva(id_reserva)
        if not reserva:
            return jsonify({'error': 'Reserva no encontrada'}), 404
        
        # Control de acceso: los participantes solo pueden ver sus propias reservas
        if g.user_type != 'admin':
            # Verificar que el usuario es parte de la reserva
            query_check = """
                SELECT 1 FROM reserva_participante 
                WHERE id_reserva = %s AND ci_participante = %s
            """
            resultado = execute_query(query_check, (id_reserva, g.user_id), role='readonly')
            if not resultado:
                return jsonify({'error': 'No tienes permiso para ver esta reserva'}), 403
        
        # Obtener lista de participantes con información detallada
        query = """
            SELECT 
                rp.ci_participante,
                p.nombre,
                p.apellido,
                p.email,
                rp.asistencia
            FROM reserva_participante rp
            JOIN participante p ON rp.ci_participante = p.ci
            WHERE rp.id_reserva = %s
            ORDER BY p.apellido, p.nombre
        """
        participantes = execute_query(query, (id_reserva,), role='readonly')
        
        # Formatear respuesta
        participantes_formateados = []
        for p in participantes:
            participantes_formateados.append({
                'ci': p['ci_participante'],
                'nombre': p['nombre'],
                'apellido': p['apellido'],
                'email': p['email'],
                'asistencia': bool(p['asistencia']) if p['asistencia'] is not None else False
            })
        
        return jsonify({
            'ok': True,
            'id_reserva': id_reserva,
            'participantes': participantes_formateados,
            'total': len(participantes_formateados)
        }), 200
        
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
