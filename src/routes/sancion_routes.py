# src/routes/sancion_routes.py
from flask import Blueprint, request, jsonify
from datetime import datetime
from src.models.sancion_model import (
    crear_sancion,
    listar_sanciones,
    eliminar_sancion,
    aplicar_sanciones_por_reserva,
)
from src.utils.response import with_auth_link
from src.auth.jwt_utils import jwt_required

sancion_bp = Blueprint("sancion_bp", __name__)


def _parse_date(s: str):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        raise ValueError("Formato de fecha inválido. Use YYYY-MM-DD.")


@sancion_bp.route("/", methods=["GET"])
def listar_sanciones_ruta():
    """
    GET /sanciones?ci=123&activas=true
    """
    ci = request.args.get("ci", type=int)
    activas = request.args.get("activas", default="false").lower() in ("1", "true", "t", "yes", "y")
    try:
        data = listar_sanciones(ci_participante=ci, solo_activas=activas)
        return jsonify(with_auth_link({"sanciones": data})), 200
    except Exception as e:
        return jsonify({"error": "Error interno", "detalle": str(e)}), 500


@sancion_bp.route("/", methods=["POST"])
@jwt_required
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


@sancion_bp.route("/", methods=["DELETE"])
@jwt_required
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
def aplicar_por_reserva_ruta(id_reserva: int):
    """
    Aplica la regla: sancionar a todos SOLO si nadie asistió.
    Opcional: body {"sancion_dias": 7} (default=7)
    """
    body = request.get_json(silent=True) or {}
    sancion_dias = int(body.get("sancion_dias", 7))
    try:
        resultado = aplicar_sanciones_por_reserva(id_reserva, sancion_dias=sancion_dias)
        return jsonify({"resultado": resultado}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": "Error interno", "detalle": str(e)}), 500
