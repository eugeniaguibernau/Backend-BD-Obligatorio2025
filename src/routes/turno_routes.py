from flask import Blueprint, request, jsonify
from src.config.database import execute_query

turno_bp = Blueprint('turno_bp', __name__)


@turno_bp.route('/', methods=['GET'])
def list_turnos():
    fecha = request.args.get('fecha')  # YYYY-MM-DD opcional
    nombre_sala = request.args.get('nombre_sala')
    edificio = request.args.get('edificio')

    # Obtener turnos (sólo horas)
    rows = execute_query("SELECT id_turno, TIME(hora_inicio) AS hora_inicio, TIME(hora_fin) AS hora_fin FROM turno", (), role='readonly') or []

    result = []
    for r in rows:
        disponible = None
        if fecha and nombre_sala and edificio:
            q = """
                SELECT COUNT(*) AS cnt
                FROM reserva
                WHERE nombre_sala = %s AND edificio = %s AND fecha = %s AND id_turno = %s AND estado = 'activa'
            """
            res = execute_query(q, (nombre_sala, edificio, fecha, r['id_turno']), role='readonly')
            cnt = res[0]['cnt'] if res else 0
            disponible = (cnt == 0)
        result.append({
            'id_turno': r['id_turno'],
            'hora_inicio': str(r['hora_inicio']),
            'hora_fin': str(r['hora_fin']),
            'disponible': disponible
        })
    return jsonify({'turnos': result}), 200
