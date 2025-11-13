# src/routes/sancion_routes.py
from flask import Blueprint, request, jsonify, g
from datetime import datetime
from src.models.sancion_model import (
    crear_sancion,
    listar_sanciones,
    eliminar_sancion,
    aplicar_sanciones_por_reserva,
    procesar_reservas_vencidas,
    extender_sanciones_existentes,
)
from src.utils.response import with_auth_link
from src.auth.jwt_utils import jwt_required
from src.middleware.permissions import require_admin

sancion_bp = Blueprint("sancion_bp", __name__)


def _parse_date(s: str):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        raise ValueError("Formato de fecha inválido. Use YYYY-MM-DD.")


@sancion_bp.route("/", methods=["GET"])
@jwt_required
def listar_sanciones_ruta():
    """
    GET /sanciones?ci=123&activas=true
    Devuelve las sanciones y un resumen con totales
    """
    ci = request.args.get("ci", type=int)
    activas = request.args.get("activas", default="false").lower() in ("1", "true", "t", "yes", "y")
    try:
        # Control de acceso: participantes solo ven sus propias sanciones
        if g.user_type != 'admin':
            ci = g.user_id  # Forzar filtro por CI del participante logueado
        
        data = listar_sanciones(ci_participante=ci, solo_activas=activas)
        
        # Calcular resumen
        total_sanciones = len(data)
        total_dias_sancionados = sum(s.get('duracion_dias', 0) for s in data)
        
        # Para dias_restantes_total: encontrar la fecha_fin más lejana de sanciones vigentes
        from datetime import date
        hoy = date.today()
        sanciones_vigentes = [s for s in data if s.get('dias_restantes', 0) >= 0]
        
        if sanciones_vigentes:
            # Encontrar la fecha de fin más lejana
            fecha_fin_max = max(s.get('fecha_fin') for s in sanciones_vigentes if s.get('fecha_fin'))
            # Calcular días desde hoy hasta esa fecha
            if fecha_fin_max:
                dias_restantes_total = (fecha_fin_max - hoy).days
            else:
                dias_restantes_total = 0
        else:
            dias_restantes_total = 0
        
        return jsonify(with_auth_link({
            "sanciones": data,
            "resumen": {
                "total_sanciones": total_sanciones,
                "total_dias_sancionados": total_dias_sancionados,
                "dias_restantes_total": dias_restantes_total
            }
        })), 200
    except Exception as e:
        return jsonify({"error": "Error interno", "detalle": str(e)}), 500


@sancion_bp.route("/", methods=["POST"])
@jwt_required
@require_admin
def crear_sancion_ruta():
    """
    Body JSON: { "ci_participante": 123, "fecha_inicio":"YYYY-MM-DD", "fecha_fin":"YYYY-MM-DD" }
    """
    datos = request.get_json() or {}
    for campo in ["ci_participante", "fecha_inicio", "fecha_fin"]:
        if campo not in datos:
            return jsonify({"error": f"Falta el campo obligatorio: {campo}"}), 400
    try:
        ci = int(datos["ci_participante"])
        fi = _parse_date(datos["fecha_inicio"])
        ff = _parse_date(datos["fecha_fin"])
        filas = crear_sancion(ci, fi, ff)
        return jsonify({"sancion_creada": bool(filas), "filas_afectadas": filas}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Error interno", "detalle": str(e)}), 500


@sancion_bp.route('/extender', methods=['POST'])
@jwt_required
@require_admin
def extender_sanciones_ruta():
    """Endpoint admin para extender sanciones existentes a un mínimo de días."""
    body = request.get_json(silent=True) or {}
    min_dias = int(body.get('min_dias', 60))
    try:
        resultado = extender_sanciones_existentes(min_dias=min_dias)
        return jsonify({'resultado': resultado}), 200
    except Exception as e:
        return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500


@sancion_bp.route("/", methods=["DELETE"])
@jwt_required
@require_admin
def eliminar_sancion_ruta():
    """
    Body JSON: { "ci_participante": 123, "fecha_inicio":"YYYY-MM-DD", "fecha_fin":"YYYY-MM-DD" }
    Elimina una sanción por su clave natural.
    """
    datos = request.get_json() or {}
    for campo in ["ci_participante", "fecha_inicio", "fecha_fin"]:
        if campo not in datos:
            return jsonify({"error": f"Falta el campo obligatorio: {campo}"}), 400
    try:
        ci = int(datos["ci_participante"])
        fi = _parse_date(datos["fecha_inicio"])
        ff = _parse_date(datos["fecha_fin"])
        filas = eliminar_sancion(ci, fi, ff)
        if filas == 0:
            return jsonify({"eliminada": False, "mensaje": "Sanción no encontrada"}), 404
        return jsonify({"eliminada": True, "filas_afectadas": filas}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Error interno", "detalle": str(e)}), 500


@sancion_bp.route("/aplicar/<int:id_reserva>", methods=["POST"])
@jwt_required
@require_admin
def aplicar_por_reserva_ruta(id_reserva: int):
    """
    Aplica la regla: sancionar a todos SOLO si nadie asistió.
    Opcional: body {"sancion_dias": 60} (default=60)
    """
    body = request.get_json(silent=True) or {}
    sancion_dias = int(body.get("sancion_dias", 60))
    try:
        resultado = aplicar_sanciones_por_reserva(id_reserva, sancion_dias=sancion_dias)
        return jsonify({"resultado": resultado}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": "Error interno", "detalle": str(e)}), 500


@sancion_bp.route("/procesar-vencidas", methods=["POST"])
@jwt_required
@require_admin
def procesar_vencidas_ruta():
    """Endpoint para disparar el procesamiento de reservas vencidas que genera sanciones automáticamente."""
    body = request.get_json(silent=True) or {}
    sancion_dias = int(body.get("sancion_dias", 60))
    try:
        resumen = procesar_reservas_vencidas(sancion_dias=sancion_dias)
        return jsonify({"resultado": resumen}), 200
    except Exception as e:
        return jsonify({"error": "Error interno", "detalle": str(e)}), 500
