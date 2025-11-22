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
from src.config.database import get_connection
from datetime import timezone

sancion_bp = Blueprint("sancion_bp", __name__)


def _parse_date(s: str):
    # Aceptar formatos: YYYY-MM-DD (ISO), MM-DD-YYYY y MM/DD/YYYY (front)
    if not s or not isinstance(s, str):
        raise ValueError("Formato de fecha inválido. Use YYYY-MM-DD, MM-DD-YYYY o MM/DD/YYYY.")

    s_clean = s.strip()
    # Normalizar barras a guiones para cubrir MM/DD/YYYY -> MM-DD-YYYY
    s_norm = s_clean.replace('/', '-').replace('\u200e', '')

    # Intentar ISO primero, luego MM-DD-YYYY
    for fmt in ("%Y-%m-%d", "%m-%d-%Y"):
        try:
            return datetime.strptime(s_norm, fmt).date()
        except Exception:
            continue

    raise ValueError("Formato de fecha inválido. Use YYYY-MM-DD, MM-DD-YYYY o MM/DD/YYYY.")


@sancion_bp.route('/<int:id_sancion>', methods=['PATCH'])
@jwt_required
@require_admin
def actualizar_sancion_ruta(id_sancion: int):
    """
    PATCH /sanciones/:id
    Body (campos opcionales): 
    {
        "fecha_inicio": "YYYY-MM-DD",  // opcional
        "fecha_fin": "YYYY-MM-DD"      // opcional
    }
    
    Reglas de validación:
      - Al menos uno de los dos campos debe estar presente
      - Si se envía fecha_fin, no puede ser anterior a fecha_inicio (actual o nueva)
      - Si se envía fecha_fin, debe ser >= hoy (para que tenga sentido)
      - Si se envía fecha_inicio y es nueva, no validamos que sea >= hoy (permite extender sanciones pasadas)
    
    Ejecuta SELECT ... FOR UPDATE y UPDATE dentro de transacción.
    """
    datos = request.get_json() or {}
    
    # Validar que al menos un campo esté presente
    if 'fecha_inicio' not in datos and 'fecha_fin' not in datos:
        return jsonify({'ok': False, 'error': 'Debe proporcionar al menos fecha_inicio o fecha_fin'}), 400

    try:
        # Normalizar hoy en UTC (solo fecha)
        hoy_utc = datetime.utcnow().date()

        # Ejecutar en transacción con SELECT ... FOR UPDATE
        conn = get_connection(role='admin')
        try:
            cur = conn.cursor()
            cur.execute('START TRANSACTION')
            cur.execute('SELECT ci_participante, fecha_inicio, fecha_fin FROM sancion_participante WHERE id_sancion = %s FOR UPDATE', (id_sancion,))
            fila = cur.fetchone()
            if not fila:
                conn.rollback()
                cur.close()
                conn.close()
                return jsonify({'ok': False, 'error': 'Sanción no encontrada'}), 404

            # Obtener valores actuales
            fi_actual = fila.get('fecha_inicio')
            ff_actual = fila.get('fecha_fin')

            # Determinar valores finales (actual o nuevo)
            fi = _parse_date(datos['fecha_inicio']) if 'fecha_inicio' in datos else fi_actual
            ff = _parse_date(datos['fecha_fin']) if 'fecha_fin' in datos else ff_actual

            # Validaciones
            if ff <= fi:
                conn.rollback()
                cur.close()
                conn.close()
                return jsonify({'ok': False, 'error': 'La fecha fin debe ser posterior a la fecha de inicio'}), 400
            
            # Validar que fecha_fin tenga sentido (no en el pasado lejano)
            if ff < hoy_utc:
                conn.rollback()
                cur.close()
                conn.close()
                return jsonify({'ok': False, 'error': 'La fecha fin debe ser hoy o posterior (no tiene sentido extender una sanción ya vencida)'}), 400

            # Realizar update
            cur.execute(
                """
                UPDATE sancion_participante
                SET fecha_inicio = %s, fecha_fin = %s, updated_by = %s, updated_at = UTC_TIMESTAMP()
                WHERE id_sancion = %s
                """,
                (fi, ff, g.user_id, id_sancion)
            )

            # Obtener registro actualizado
            cur.execute('SELECT id_sancion, ci_participante, fecha_inicio, fecha_fin, updated_by, updated_at FROM sancion_participante WHERE id_sancion = %s', (id_sancion,))
            updated = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()

            # calcular activo (fecha_fin >= hoy)
            activo = False
            try:
                fecha_fin_db = updated.get('fecha_fin')
                if fecha_fin_db and fecha_fin_db >= hoy_utc:
                    activo = True
            except Exception:
                activo = False

            sancion_out = {
                'id_sancion': updated.get('id_sancion'),
                'ci_participante': updated.get('ci_participante'),
                'fecha_inicio': str(updated.get('fecha_inicio')) if updated.get('fecha_inicio') else None,
                'fecha_fin': str(updated.get('fecha_fin')) if updated.get('fecha_fin') else None,
                'activo': activo,
                'updated_by': updated.get('updated_by'),
                'updated_at': updated.get('updated_at').isoformat() if updated.get('updated_at') else None
            }

            return jsonify({'ok': True, 'sancion': sancion_out}), 200
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            cur.close()
            conn.close()
            return jsonify({'ok': False, 'error': 'Error interno', 'detalle': str(e)}), 500

    except ValueError as e:
        return jsonify({'ok': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'ok': False, 'error': 'Error interno', 'detalle': str(e)}), 500


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
    # Validar campos requeridos
    for campo in ["ci_participante", "fecha_inicio", "fecha_fin"]:
        if campo not in datos:
            return jsonify({"error": f"Falta el campo obligatorio: {campo}"}), 400

    # Validar CI
    try:
        ci = int(datos["ci_participante"])
    except Exception:
        return jsonify({"error": "CI de participante inválido", "valor_recibido": datos.get("ci_participante")}), 400

    # Validar formato explícito para fechas recibidas y dar mensajes claros
    fi_raw = datos.get("fecha_inicio")
    ff_raw = datos.get("fecha_fin")

    # Detectar valores claramente inválidos como 'NaN-NaN-NaN'
    for name, val in (('fecha_inicio', fi_raw), ('fecha_fin', ff_raw)):
        if not isinstance(val, str) or 'nan' in val.lower():
            return jsonify({
                "error": f"Formato de fecha inválido para {name}",
                "valor_recibido": val,
                "detalle": "Use YYYY-MM-DD, MM-DD-YYYY o MM/DD/YYYY"
            }), 400

    # Intentar parsear con helper, devolver mensaje que incluya el valor original si falla
    try:
        fi = _parse_date(fi_raw)
    except ValueError as e:
        return jsonify({"error": "Formato de fecha inválido para fecha_inicio", "valor_recibido": fi_raw, "detalle": str(e)}), 400

    try:
        ff = _parse_date(ff_raw)
    except ValueError as e:
        return jsonify({"error": "Formato de fecha inválido para fecha_fin", "valor_recibido": ff_raw, "detalle": str(e)}), 400

    try:
        filas = eliminar_sancion(ci, fi, ff)
        if filas == 0:
            return jsonify({"eliminada": False, "mensaje": "Sanción no encontrada"}), 404
        return jsonify({"eliminada": True, "filas_afectadas": filas}), 200
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
