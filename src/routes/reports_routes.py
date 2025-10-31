from flask import Blueprint, request, jsonify
from src.config.database import execute_query

reports_bp = Blueprint('reports_bp', __name__)
"""
    EN TODAS: si no se pone query param start_date ni end_date, se consideran todos los datos (de todas las fechas)
    """

@reports_bp.route('/most-reserved-rooms', methods=['GET'])
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
        results = execute_query(query, tuple(params))
        return jsonify({
            'salas_mas_reservadas': results,
            'total': len(results)
        }), 200
    except Exception as e:
        return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500


@reports_bp.route('/most-demanded-turns', methods=['GET'])
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
        results = execute_query(query, tuple(params) if params else None)
        return jsonify({
            'turnos_mas_demandados': results,
            'total': len(results)
        }), 200
    except Exception as e:
        return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500


@reports_bp.route('/avg-participants-by-room', methods=['GET'])
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
        results = execute_query(query, tuple(params) if params else None)
        
        # Calcular promedios y porcentajes en Python
        for row in results:
            if row['total_reservas'] > 0:
                row['promedio_participantes'] = round(row['total_participantes'] / row['total_reservas'], 2)
                row['porcentaje_ocupacion'] = round((row['promedio_participantes'] / row['capacidad']) * 100, 2)
            else:
                row['promedio_participantes'] = 0
                row['porcentaje_ocupacion'] = 0
        
        return jsonify({
            'promedio_participantes_por_sala': results,
            'total': len(results)
        }), 200
    except Exception as e:
        return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500


@reports_bp.route('/reservations-by-program', methods=['GET'])
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
        results = execute_query(query, tuple(params) if params else None)
        return jsonify({
            'reservas_por_programa': results,
            'total': len(results)
        }), 200
    except Exception as e:
        return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500


@reports_bp.route('/occupancy-by-building', methods=['GET'])
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
        results = execute_query(query, tuple(params) if params else None)
        
        # Calcular ratio y porcentaje en Python
        for row in results:
            if row['capacidad_total'] and row['capacidad_total'] > 0:
                row['ratio_ocupacion'] = round(row['total_participantes'] / row['capacidad_total'], 4)
                row['porcentaje_ocupacion'] = round((row['total_participantes'] / row['capacidad_total']) * 100, 2)
            else:
                row['ratio_ocupacion'] = 0
                row['porcentaje_ocupacion'] = 0
        
        return jsonify({
            'ocupacion_por_edificio': results,
            'total': len(results)
        }), 200
    except Exception as e:
        return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500


@reports_bp.route('/reservations-and-attendance-by-role', methods=['GET'])
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
            COUNT(DISTINCT rp.id_reserva) as total_reservas, SUM(rp.asistencia = true) as total_asistencias,
            SUM(rp.asistencia = false) as total_inasistencias, SUM(rp.asistencia IS NULL) as asistencias_sin_registrar
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
        results = execute_query(query, tuple(params) if params else None)
        return jsonify({
            'reservas_y_asistencias_por_rol': results,
            'total': len(results)
        }), 200
    except Exception as e:
        return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500


@reports_bp.route('/sanctions-by-role', methods=['GET'])
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
        results = execute_query(query, tuple(params) if params else None)
        return jsonify({
            'sanciones_por_rol': results,
            'total': len(results)
        }), 200
    except Exception as e:
        return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500


@reports_bp.route('/used-vs-cancelled', methods=['GET'])
def used_vs_cancelled():
    """
    Consulta: Porcentaje de reservas efectivamente utilizadas vs canceladas/no asistidas

    Query params opcionales:
    - start_date: fecha inicio (YYYY-MM-DD)
    - end_date: fecha fin (YYYY-MM-DD)
    """
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = """
        SELECT
            SUM(CASE WHEN r.estado = 'finalizada' THEN 1 ELSE 0 END) as used,
            SUM(CASE WHEN r.estado IN ('cancelada','sin asistencia') THEN 1 ELSE 0 END) as cancelled_or_no_show,
            COUNT(*) as total_reservas
        FROM reserva r
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

    try:
        rows = execute_query(query, tuple(params) if params else None)
        # execute_query returns a list of rows; for an aggregate query we expect one row
        row = rows[0] if rows else {'used': 0, 'cancelled_or_no_show': 0, 'total_reservas': 0}

        used = int(row.get('used', 0) or 0)
        cancelled = int(row.get('cancelled_or_no_show', 0) or 0)
        total = int(row.get('total_reservas', 0) or 0)

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
