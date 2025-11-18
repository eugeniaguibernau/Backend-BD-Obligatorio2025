from flask import Blueprint, request, jsonify, current_app
from src.config.database import execute_query
from src.auth.jwt_utils import jwt_required

reports_bp = Blueprint('reports_bp', __name__)
"""
    EN TODAS: si no se pone query param start_date ni end_date, se consideran todos los datos (de todas las fechas)
    """

@reports_bp.route('/most-reserved-rooms', methods=['GET'])
@jwt_required
def most_reserved_rooms():
    """
    Consulta: Salas más reservadas
    
    Query params opcionales:
    - start_date: fecha inicio (YYYY-MM-DD)
    - end_date: fecha fin (YYYY-MM-DD)
    - limit: número máximo de resultados (default: 10)
    """
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    limit = request.args.get('limit', 10)
    
    try:
        limit = int(limit)
    except ValueError:
        return jsonify({'error': 'limit must be an integer'}), 400
    
    query = """
        SELECT 
            s.nombre_sala, s.edificio, s.tipo_sala, s.capacidad, COUNT(r.id_reserva) as total_reservas
        FROM sala s
        LEFT JOIN reserva r ON s.nombre_sala = r.nombre_sala AND s.edificio = r.edificio
    """
    
    filters = []
    params = []
    
    if start_date:
        filters.append("r.fecha >= %s")
        params.append(start_date)
    
    if end_date:
        filters.append("r.fecha <= %s")
        params.append(end_date)
    
    if filters:
        query += " WHERE " + " AND ".join(filters)
    
    query += """
        GROUP BY s.nombre_sala, s.edificio, s.tipo_sala, s.capacidad
        ORDER BY total_reservas DESC
        LIMIT %s
    """
    params.append(limit)
    
    try:
        results = execute_query(query, tuple(params), role='readonly')
        from src.utils.response import with_auth_link
        return jsonify(with_auth_link({
            'salas_mas_reservadas': results,
            'total': len(results)
        })), 200
    except Exception as e:
        try:
            current_app.logger.exception(e)
        except Exception:
            pass
        return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500


@reports_bp.route('/most-demanded-turns', methods=['GET'])
@jwt_required
def most_demanded_turns():
    """
    Consulta: Turnos más demandados
    
    Query params opcionales:
    - start_date: fecha inicio (YYYY-MM-DD)
    - end_date: fecha fin (YYYY-MM-DD)
    """
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = """
        SELECT 
            t.id_turno,t.hora_inicio, t.hora_fin, COUNT(r.id_reserva) as total_reservas
        FROM turno t
        LEFT JOIN reserva r ON t.id_turno = r.id_turno
    """
    
    filters = []
    params = []
    
    if start_date:
        filters.append("r.fecha >= %s")
        params.append(start_date)
    
    if end_date:
        filters.append("r.fecha <= %s")
        params.append(end_date)
    
    if filters:
        query += " WHERE " + " AND ".join(filters)
    
    query += """
        GROUP BY t.id_turno, t.hora_inicio, t.hora_fin
        ORDER BY total_reservas DESC
    """
    
    try:
        results = execute_query(query, tuple(params) if params else None, role='readonly')
        from src.utils.response import with_auth_link
        return jsonify(with_auth_link({
            'turnos_mas_demandados': results,
            'total': len(results)
        })), 200
    except Exception as e:
        return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500


@reports_bp.route('/avg-participants-by-room', methods=['GET'])
@jwt_required
def avg_participants_by_room():
    """
    Consulta: Promedio de participantes por sala
    
    Query params opcionales:
    - start_date: fecha inicio (YYYY-MM-DD)
    - end_date: fecha fin (YYYY-MM-DD)
    - edificio: filtrar por edificio
    - tipo_sala: filtrar por tipo (libre/posgrado/docente)
    """
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    edificio = request.args.get('edificio')
    tipo_sala = request.args.get('tipo_sala')
    
    query = """
        SELECT 
            s.nombre_sala, s.edificio, s.tipo_sala, s.capacidad, COUNT(DISTINCT r.id_reserva) as total_reservas,
            COUNT(rp.ci_participante) as total_participantes
        FROM sala s
        LEFT JOIN reserva r ON s.nombre_sala = r.nombre_sala AND s.edificio = r.edificio
        LEFT JOIN reserva_participante rp ON r.id_reserva = rp.id_reserva
    """
    
    filters = []
    params = []
    
    if start_date:
        filters.append("r.fecha >= %s")
        params.append(start_date)
    
    if end_date:
        filters.append("r.fecha <= %s")
        params.append(end_date)
    
    if edificio:
        filters.append("s.edificio = %s")
        params.append(edificio)
    
    if tipo_sala:
        filters.append("s.tipo_sala = %s")
        params.append(tipo_sala)
    
    if filters:
        query += " WHERE " + " AND ".join(filters)
    
    query += """
        GROUP BY s.nombre_sala, s.edificio, s.tipo_sala, s.capacidad
        HAVING total_reservas > 0
        ORDER BY total_participantes DESC
    """
    
    try:
        results = execute_query(query, tuple(params), role='readonly' if params else None)
        
        # Calcular promedios y porcentajes en Python
        for row in results:
            if row['total_reservas'] > 0:
                row['promedio_participantes'] = round(row['total_participantes'] / row['total_reservas'], 2)
                row['porcentaje_ocupacion'] = round((row['promedio_participantes'] / row['capacidad']) * 100, 2)
            else:
                row['promedio_participantes'] = 0
                row['porcentaje_ocupacion'] = 0
        
        from src.utils.response import with_auth_link
        return jsonify(with_auth_link({
            'promedio_participantes_por_sala': results,
            'total': len(results)
        })), 200
    except Exception as e:
        return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500


@reports_bp.route('/reservations-by-program', methods=['GET'])
@jwt_required
def reservations_by_program():
    """
    Consulta: Cantidad de reservas por carrera y facultad
    
    Query params opcionales:
    - start_date: fecha inicio (YYYY-MM-DD)
    - end_date: fecha fin (YYYY-MM-DD)
    - facultad: filtrar por nombre de facultad
    """
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    facultad = request.args.get('facultad')
    
    query = """
        SELECT 
            f.nombre as facultad, pa.nombre_programa as programa, pa.tipo as tipo_programa,
            COUNT(DISTINCT r.id_reserva) as total_reservas, COUNT(DISTINCT rp.ci_participante) as participantes_unicos
        FROM facultad f
        JOIN programa_academico pa ON f.id_facultad = pa.id_facultad
        JOIN participante_programa_academico ppa ON pa.nombre_programa = ppa.nombre_programa
        JOIN reserva_participante rp ON ppa.ci_participante = rp.ci_participante
        JOIN reserva r ON rp.id_reserva = r.id_reserva
    """
    
    filters = []
    params = []
    
    if start_date:
        filters.append("r.fecha >= %s")
        params.append(start_date)
    
    if end_date:
        filters.append("r.fecha <= %s")
        params.append(end_date)
    
    if facultad:
        filters.append("f.nombre = %s")
        params.append(facultad)
    
    if filters:
        query += " WHERE " + " AND ".join(filters)
    
    query += """
        GROUP BY f.nombre, pa.nombre_programa, pa.tipo
        ORDER BY f.nombre, total_reservas DESC
    """
    
    try:
        results = execute_query(query, tuple(params), role='readonly' if params else None)
        from src.utils.response import with_auth_link
        return jsonify(with_auth_link({
            'reservas_por_programa': results,
            'total': len(results)
        })), 200
    except Exception as e:
        return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500


@reports_bp.route('/occupancy-by-building', methods=['GET'])
@jwt_required
def occupancy_by_building():
    """
    Consulta: Porcentaje de ocupación de salas por edificio
    
    Query params opcionales:
    - start_date: fecha inicio (YYYY-MM-DD)
    - end_date: fecha fin (YYYY-MM-DD)
    """
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = """
        SELECT 
            e.nombre_edificio as edificio, e.direccion, e.departamento, COUNT(DISTINCT s.nombre_sala) as total_salas,
            SUM(s.capacidad) as capacidad_total, COUNT(DISTINCT r.id_reserva) as total_reservas,
            COUNT(rp.ci_participante) as total_participantes
        FROM edificio e
        JOIN sala s ON e.nombre_edificio = s.edificio
        LEFT JOIN reserva r ON s.nombre_sala = r.nombre_sala AND s.edificio = r.edificio
        LEFT JOIN reserva_participante rp ON r.id_reserva = rp.id_reserva
    """
    
    filters = []
    params = []
    
    if start_date:
        filters.append("r.fecha >= %s")
        params.append(start_date)
    
    if end_date:
        filters.append("r.fecha <= %s")
        params.append(end_date)
    
    if filters:
        query += " WHERE " + " AND ".join(filters)
    
    query += """
        GROUP BY e.nombre_edificio, e.direccion, e.departamento
        ORDER BY total_participantes DESC
    """
    
    try:
        results = execute_query(query, tuple(params), role='readonly' if params else None)
        
        # Calcular ratio y porcentaje en Python
        for row in results:
            if row['capacidad_total'] and row['capacidad_total'] > 0:
                row['ratio_ocupacion'] = round(row['total_participantes'] / row['capacidad_total'], 4)
                row['porcentaje_ocupacion'] = round((row['total_participantes'] / row['capacidad_total']) * 100, 2)
            else:
                row['ratio_ocupacion'] = 0
                row['porcentaje_ocupacion'] = 0
        
        from src.utils.response import with_auth_link
        return jsonify(with_auth_link({
            'ocupacion_por_edificio': results,
            'total': len(results)
        })), 200
    except Exception as e:
        return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500


@reports_bp.route('/reservations-and-attendance-by-role', methods=['GET'])
@jwt_required
def reservations_and_attendance_by_role():
    """
    Consulta: Cantidad de reservas y asistencias de profesores y alumnos (grado y posgrado)
    
    Query params opcionales:
    - start_date: fecha inicio (YYYY-MM-DD)
    - end_date: fecha fin (YYYY-MM-DD)
    - rol: filtrar por rol (alumno/docente)
    - tipo_programa: filtrar por tipo (grado/postgrado)
    """
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    rol = request.args.get('rol')
    tipo_programa = request.args.get('tipo_programa')
    
    query = """
        SELECT 
            ppa.rol, pa.tipo as tipo_programa, COUNT(DISTINCT rp.ci_participante) as participantes_unicos,
            COUNT(DISTINCT rp.id_reserva) as total_reservas
        FROM participante_programa_academico ppa
        JOIN programa_academico pa ON ppa.nombre_programa = pa.nombre_programa
        JOIN reserva_participante rp ON ppa.ci_participante = rp.ci_participante
        JOIN reserva r ON rp.id_reserva = r.id_reserva
    """
    
    filters = []
    params = []
    
    if start_date:
        filters.append("r.fecha >= %s")
        params.append(start_date)
    
    if end_date:
        filters.append("r.fecha <= %s")
        params.append(end_date)
    
    if rol:
        filters.append("ppa.rol = %s")
        params.append(rol)
    
    if tipo_programa:
        filters.append("pa.tipo = %s")
        params.append(tipo_programa)
    
    if filters:
        query += " WHERE " + " AND ".join(filters)
    
    query += """
        GROUP BY ppa.rol, pa.tipo
        ORDER BY ppa.rol, pa.tipo
    """
    
    try:
        results = execute_query(query, tuple(params), role='readonly' if params else None)
        
        # Calcular asistencias en Python para cada grupo
        for row in results:
            rol_filter = row['rol']
            tipo_filter = row['tipo_programa']
            
            # Query para contar asistencias por tipo
            asistencia_query = """
                SELECT COUNT(*) as total, rp.asistencia
                FROM participante_programa_academico ppa
                JOIN programa_academico pa ON ppa.nombre_programa = pa.nombre_programa
                JOIN reserva_participante rp ON ppa.ci_participante = rp.ci_participante
                JOIN reserva r ON rp.id_reserva = r.id_reserva
                WHERE ppa.rol = %s AND pa.tipo = %s
            """
            
            asistencia_params = [rol_filter, tipo_filter]
            
            if start_date:
                asistencia_query += " AND r.fecha >= %s"
                asistencia_params.append(start_date)
            
            if end_date:
                asistencia_query += " AND r.fecha <= %s"
                asistencia_params.append(end_date)
            
            asistencia_query += " GROUP BY rp.asistencia"
            
            asistencia_results = execute_query(asistencia_query, tuple(asistencia_params), role='readonly')
            
            row['total_asistencias'] = 0
            row['total_inasistencias'] = 0
            row['asistencias_sin_registrar'] = 0
            
            for asist_row in asistencia_results:
                if asist_row['asistencia'] == 1 or asist_row['asistencia'] is True:
                    row['total_asistencias'] = asist_row['total']
                elif asist_row['asistencia'] == 0 or asist_row['asistencia'] is False:
                    row['total_inasistencias'] = asist_row['total']
                elif asist_row['asistencia'] is None:
                    row['asistencias_sin_registrar'] = asist_row['total']
        from src.utils.response import with_auth_link
        return jsonify(with_auth_link({
            'reservas_y_asistencias_por_rol': results,
            'total': len(results)
        })), 200
    except Exception as e:
        return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500


@reports_bp.route('/sanctions-by-role', methods=['GET'])
@jwt_required
def sanctions_by_role():
    """
    Consulta: Cantidad de sanciones por rol y tipo de programa (alumno/docente x grado/posgrado)

    Query params opcionales:
    - start_date: fecha inicio (YYYY-MM-DD) (filtra por fecha_inicio de la sanción)
    - end_date: fecha fin (YYYY-MM-DD) (filtra por fecha_fin de la sanción)
    """
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = """
        SELECT
            ppa.rol, pa.tipo as tipo_programa, COUNT(sp.ci_participante) as total_sanciones
        FROM sancion_participante sp
        JOIN participante_programa_academico ppa ON sp.ci_participante = ppa.ci_participante
        JOIN programa_academico pa ON ppa.nombre_programa = pa.nombre_programa
    """

    filters = []
    params = []

    if start_date:
        filters.append("sp.fecha_inicio >= %s")
        params.append(start_date)

    if end_date:
        filters.append("sp.fecha_fin <= %s")
        params.append(end_date)

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += """
        GROUP BY ppa.rol, pa.tipo
        ORDER BY total_sanciones DESC
    """

    try:
        results = execute_query(query, tuple(params), role='readonly' if params else None)
        return jsonify({
            'sanciones_por_rol': results,
            'total': len(results)
        }), 200
    except Exception as e:
        return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500


@reports_bp.route('/used-vs-cancelled', methods=['GET'])
@jwt_required
def used_vs_cancelled():
    """
    Consulta: Porcentaje de reservas efectivamente utilizadas vs canceladas/no asistidas

    Query params opcionales:
    - start_date: fecha inicio (YYYY-MM-DD)
    - end_date: fecha fin (YYYY-MM-DD)
    """
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # Query para contar total de reservas
    query_total = """
        SELECT COUNT(*) as total_reservas
        FROM reserva r
    """
    
    # Query para contar finalizadas
    query_used = """
        SELECT COUNT(*) as used
        FROM reserva r
        WHERE r.estado = 'finalizada'
    """
    
    # Query para contar canceladas o sin asistencia
    query_cancelled = """
        SELECT COUNT(*) as cancelled_or_no_show
        FROM reserva r
        WHERE r.estado IN ('cancelada', 'sin asistencia')
    """

    filters = []
    params = []

    if start_date:
        filters.append("r.fecha >= %s")
        params.append(start_date)

    if end_date:
        filters.append("r.fecha <= %s")
        params.append(end_date)

    # Agregar filtros a cada query
    if filters:
        filter_clause = " AND " + " AND ".join(filters)
        query_used += filter_clause
        query_cancelled += filter_clause
        query_total += " WHERE " + " AND ".join(filters)

    try:
        # Ejecutar las tres queries
        total_result = execute_query(query_total, tuple(params), role='readonly' if params else None)
        used_result = execute_query(query_used, tuple(params), role='readonly' if params else None)
        cancelled_result = execute_query(query_cancelled, tuple(params), role='readonly' if params else None)
        
        total = int(total_result[0]['total_reservas']) if total_result else 0
        used = int(used_result[0]['used']) if used_result else 0
        cancelled = int(cancelled_result[0]['cancelled_or_no_show']) if cancelled_result else 0

        if total > 0:
            pct_used = round((used / total) * 100, 2)
            pct_cancelled = round((cancelled / total) * 100, 2)
        else:
            pct_used = pct_cancelled = 0.0

        return jsonify({
            'used': used,
            'cancelled_or_no_show': cancelled,
            'total_reservas': total,
            'porcentaje_usadas': pct_used,
            'porcentaje_canceladas_o_no_asistidas': pct_cancelled
        }), 200
    except Exception as e:
        return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500



# CONSULTAS ADICIONALES

@reports_bp.route('/peak-hours-by-room', methods=['GET'])
@jwt_required
def peak_hours_by_room():
    """
    Consulta adicional 1: Horas pico por sala
    
    Muestra los turnos más demandados por cada sala, agrupando por sala.
    Útil para identificar patrones de uso específicos de cada espacio.
    
    Query params opcionales:
    - start_date: fecha inicio (YYYY-MM-DD)
    - end_date: fecha fin (YYYY-MM-DD)
    - edificio: filtrar por edificio
    - limit: número de salas a mostrar (default: todas)
    """
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    edificio = request.args.get('edificio')
    limit = request.args.get('limit')
    
    query = """
        SELECT 
            r.nombre_sala, r.edificio, s.tipo_sala, r.id_turno, t.hora_inicio, t.hora_fin, COUNT(r.id_reserva) as total_reservas,
            COUNT(DISTINCT r.fecha) as dias_diferentes, e.departamento
        FROM reserva r
        JOIN sala s ON r.nombre_sala = s.nombre_sala AND r.edificio = s.edificio
        JOIN edificio e ON r.edificio = e.nombre_edificio
        JOIN turno t ON r.id_turno = t.id_turno
    """
    
    filters = []
    params = []
    
    if start_date:
        filters.append("r.fecha >= %s")
        params.append(start_date)
    
    if end_date:
        filters.append("r.fecha <= %s")
        params.append(end_date)
    
    if edificio:
        filters.append("r.edificio = %s")
        params.append(edificio)
    
    if filters:
        query += " WHERE " + " AND ".join(filters)
    
    query += """
    GROUP BY r.nombre_sala, r.edificio, s.tipo_sala, r.id_turno, t.hora_inicio, t.hora_fin
        ORDER BY r.nombre_sala, r.edificio, total_reservas DESC
    """
    
    if limit:
        try:
            limit_int = int(limit)
            query += f" LIMIT {limit_int}"
        except ValueError:
            return jsonify({'error': 'limit must be an integer'}), 400
    
    try:
        results = execute_query(query, tuple(params) if params else None, role='readonly')
        
        # Agrupar resultados por sala
        salas_dict = {}
        for row in results:
            sala_key = f"{row['nombre_sala']} - {row['edificio']}"
            if sala_key not in salas_dict:
                salas_dict[sala_key] = {
                    'nombre_sala': row['nombre_sala'],
                    'edificio': row['edificio'],
                    'tipo_sala': row['tipo_sala'],
                    'departamento': row.get('departamento'),
                    'unidad': row.get('departamento'),
                    'facultad': None,
                    'facultad_nombre': None,
                    'faculty': None,
                    'fac': None,
                    'turnos': []
                }
            
            horario_inicio = str(row['hora_inicio'])
            horario_fin = str(row['hora_fin'])
            total_res = row['total_reservas']
            dias = row['dias_diferentes']

            salas_dict[sala_key]['turnos'].append({
                'id_turno': row['id_turno'],
                'horario_inicio': horario_inicio,
                'horario_fin': horario_fin,
                'total_reservas': total_res,
                'dias_diferentes': dias
            })
        
        # Convertir a lista y generar etiquetas legibles para el frontend
        salas_list = []
        for sala in salas_dict.values():
            turnos_raw = sala.get('turnos', [])
            turnos_display = []
            for t in turnos_raw:
                # normalize hora strings to HH:MM
                raw_hi = t.get('horario_inicio') or t.get('hora_inicio') or ''
                raw_hf = t.get('horario_fin') or t.get('hora_fin') or ''
                def time_short(s):
                    s = str(s)
                    if ' ' in s:
                        part = s.split(' ')[-1]
                    else:
                        part = s
                    return part[:5] if len(part) >= 5 else part

                hi = time_short(raw_hi)
                hf = time_short(raw_hf)
                cnt = t.get('total_reservas', 0)
                dias = t.get('dias_diferentes', 0)
                label = f"{hi}–{hf} — {cnt} reservas ({dias} días)"
                turnos_display.append(label)

            salas_list.append({
                'nombre_sala': sala['nombre_sala'],
                'edificio': sala['edificio'],
                'tipo_sala': sala.get('tipo_sala'),
                'turnos': turnos_display
            })

        return jsonify({
            'total_salas': len(salas_list),
            'salas': salas_list
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500


@reports_bp.route('/occupancy-by-room-type', methods=['GET'])
@jwt_required
def occupancy_by_room_type():
    """
    Consulta Adicional 2: Porcentaje de ocupación por tipo de sala
    
    Mide la eficiencia de uso por categoría de sala (libre, docente, posgrado).
    Calcula el porcentaje de ocupación basado en:
    - Total de reservas realizadas vs capacidad total disponible
    - Considera turnos disponibles y capacidad de cada sala
    
    Query params opcionales:
    - start_date: fecha inicio (YYYY-MM-DD)
    - end_date: fecha fin (YYYY-MM-DD)
    """
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query_reservas = """
        SELECT 
            s.tipo_sala, COUNT(r.id_reserva) as total_reservas, COUNT(DISTINCT r.fecha) as dias_con_reservas,
            COUNT(DISTINCT CONCAT(r.nombre_sala, '-', r.edificio)) as salas_usadas
        FROM sala s
        LEFT JOIN reserva r ON s.nombre_sala = r.nombre_sala AND s.edificio = r.edificio
    """
    
    filters = []
    params = []
    
    if start_date:
        filters.append("r.fecha >= %s")
        params.append(start_date)
    
    if end_date:
        filters.append("r.fecha <= %s")
        params.append(end_date)
    
    if filters:
        query_reservas += " WHERE " + " AND ".join(filters)
    
    query_reservas += " GROUP BY s.tipo_sala"
    
    # Query para obtener capacidad total por tipo de sala
    query_capacidad = """
        SELECT 
            tipo_sala,
            COUNT(*) as total_salas,
            SUM(capacidad) as capacidad_total
        FROM sala
        GROUP BY tipo_sala
    """
    
    try:
        reservas_results = execute_query(query_reservas, tuple(params) if params else None, role='readonly')
        capacidad_results = execute_query(query_capacidad, role='readonly')
        
        # Crear diccionario de capacidades
        capacidades = {row['tipo_sala']: row for row in capacidad_results}
        
        # Calcular estadísticas
        tipos_sala = []
        for row in reservas_results:
            tipo = row['tipo_sala']
            total_reservas = row['total_reservas'] or 0
            
            if tipo in capacidades:
                cap_info = capacidades[tipo]
                total_salas = cap_info['total_salas']
                dias = row['dias_con_reservas'] or 1
                slots_disponibles = total_salas * dias * 5
                
                # Calcular porcentaje de ocupación
                if slots_disponibles > 0:
                    porcentaje_ocupacion = round((total_reservas / slots_disponibles) * 100, 2)
                else:
                    porcentaje_ocupacion = 0.0
                
                tipos_sala.append({
                    'tipo_sala': tipo,
                    'total_salas': total_salas,
                    'capacidad_total': cap_info['capacidad_total'],
                    'total_reservas': total_reservas,
                    'dias_con_reservas': row['dias_con_reservas'],
                    'salas_usadas': row['salas_usadas'],
                    'porcentaje_ocupacion': porcentaje_ocupacion
                })
        
        return jsonify({
            'tipos_sala': tipos_sala,
            'total_tipos': len(tipos_sala)
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500


@reports_bp.route('/repeat-offenders', methods=['GET'])
@jwt_required
def repeat_offenders():
    """
    Consulta Adicional 3: Participantes sancionados por reincidencia
    
    Lista participantes que han tenido más de una sanción,
    ordenados por cantidad de sanciones (de mayor a menor).
    Útil para identificar patrones de comportamiento problemático.
    
    Query params opcionales:
    - min_sanctions: mínimo de sanciones para considerar reincidente (default: 2)
    - only_active: 'true' para mostrar solo sanciones vigentes (default: false)
    """
    min_sanctions = request.args.get('min_sanctions', 2)
    only_active = request.args.get('only_active', 'false').lower() in ('true', '1', 'yes')
    
    try:
        min_sanctions = int(min_sanctions)
    except ValueError:
        return jsonify({'error': 'min_sanctions must be an integer'}), 400
    
    # Query base: obtener todas las sanciones agrupadas por participante
    query = """
        SELECT 
            sp.ci_participante, p.nombre, p.apellido, p.email, COUNT(sp.fecha_inicio) as total_sanciones,
            MIN(sp.fecha_inicio) as primera_sancion, MAX(sp.fecha_fin) as ultima_sancion
        FROM sancion_participante sp
        JOIN participante p ON sp.ci_participante = p.ci
    """
    
    if only_active:
        query += " WHERE sp.fecha_fin >= CURDATE()"
    
    query += """
        GROUP BY sp.ci_participante, p.nombre, p.apellido, p.email
        HAVING total_sanciones >= %s
        ORDER BY total_sanciones DESC, ultima_sancion DESC
    """
    
    try:
        results = execute_query(query, (min_sanctions,), role='readonly')
        
        # Query adicional para contar sanciones activas por cada participante
        query_activas = """
            SELECT ci_participante, COUNT(*) as activas
            FROM sancion_participante
            WHERE fecha_fin >= CURDATE()
            GROUP BY ci_participante
        """
        activas_results = execute_query(query_activas, role='readonly')
        
        # Crear diccionario de sanciones activas
        activas_dict = {row['ci_participante']: row['activas'] for row in activas_results}
        
        # Construir respuesta
        reincidentes = []
        for row in results:
            ci = row['ci_participante']
            reincidentes.append({
                'ci': ci,
                'nombre_completo': f"{row['nombre']} {row['apellido']}",
                'email': row['email'],
                'total_sanciones': row['total_sanciones'],
                'primera_sancion': str(row['primera_sancion']),
                'ultima_sancion': str(row['ultima_sancion']),
                'sanciones_activas': activas_dict.get(ci, 0)
            })
        
        return jsonify({
            'total_reincidentes': len(reincidentes),
            'min_sanciones': min_sanctions,
            'solo_activas': only_active,
            'reincidentes': reincidentes
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500
