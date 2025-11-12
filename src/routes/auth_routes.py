from flask import Blueprint, request, jsonify, current_app
import pymysql
from src.auth.login import hash_password, authenticate_user
from src.config.database import get_connection
from src.auth.jwt_utils import create_token
from src.extensions import limiter
from src.utils.validators import is_valid_email, is_strong_password, validate_participante

auth_bp = Blueprint('auth', __name__)

# Validaciones centralizadas en `src/utils/validators.py`


@auth_bp.route('/register', methods=['POST'])
@limiter.limit("2/minute")
def register():
    data = request.get_json() or {}
    correo = data.get('correo')
    plain = data.get('contraseña')
    participante = data.get('participante') or {}

    if not correo or not plain:
        return jsonify({"ok": False, "mensaje": "correo y contraseña requeridos"}), 400

    # Validaciones centralizadas
    if not is_valid_email(correo):
        return jsonify({"ok": False, "mensaje": "Formato de email inválido"}), 400
    if not is_strong_password(plain):
        return jsonify({"ok": False, "mensaje": "La contraseña debe tener al menos 8 caracteres"}), 400
    ok, msg = validate_participante(participante)
    if not ok:
        return jsonify({"ok": False, "mensaje": msg}), 400

    conn = get_connection('user')  # Usar usuario con permisos de INSERT/UPDATE
    cur = conn.cursor()

    # Preparar datos del participante
    ci = participante.get('ci') if participante else None
    nombre = participante.get('nombre') if participante else ''
    apellido = participante.get('apellido') if participante else ''

    try:
        # Comprobar existencia preferentemente por CI (si se envía), sino por email
        exists_by_ci = None
        if ci:
            cur.execute("SELECT ci FROM participante WHERE ci = %s", (ci,))
            exists_by_ci = cur.fetchone()

        cur.execute("SELECT email FROM participante WHERE email = %s", (correo,))
        exists_by_email = cur.fetchone()

        if not exists_by_ci and not exists_by_email:
            # No existe: insertar nuevo participante
            cur.execute(
                "INSERT INTO participante (ci, nombre, apellido, email) VALUES (%s,%s,%s,%s)",
                (ci or 0, nombre, apellido, correo)
            )
        elif exists_by_ci and not exists_by_email:
            # El CI ya existe pero el email es nuevo: actualizar registro para mantener consistencia
            cur.execute(
                "UPDATE participante SET nombre=%s, apellido=%s, email=%s WHERE ci=%s",
                (nombre, apellido, correo, ci)
            )

        # Ahora insertar/actualizar login
        hashed = hash_password(plain)
        cur.execute("SELECT correo FROM login WHERE correo = %s", (correo,))
        if cur.fetchone():
            cur.execute("UPDATE login SET `contraseña` = %s WHERE correo = %s", (hashed, correo))
        else:
            cur.execute("INSERT INTO login (correo, `contraseña`) VALUES (%s, %s)", (correo, hashed))

        conn.commit()
    except pymysql.err.IntegrityError as e:
        # Manejar violaciones de constraints (por ejemplo duplicados de PK) de forma limpia
        conn.rollback()
        cur.close()
        conn.close()
        current_app.logger.warning(f"IntegrityError en register: {e}")
        return jsonify({"ok": False, "mensaje": "Conflicto en la base de datos: dato duplicado"}), 409
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        current_app.logger.error(f"Error en register: {e}")
        return jsonify({"ok": False, "mensaje": "Error interno al crear usuario"}), 500
    finally:
        # cerrar si no fue cerrado ya
        try:
            cur.close()
            conn.close()
        except Exception:
            pass

    return jsonify({"ok": True, "mensaje": "Usuario creado/actualizado"}), 201


@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5/minute")
def login():
    data = request.get_json() or {}
    correo = data.get('correo')
    plain = data.get('contraseña')

    if not correo or not plain:
        return jsonify({"ok": False, "mensaje": "correo y contraseña requeridos"}), 400

    # Validaciones básicas
    if not is_valid_email(correo):
        return jsonify({"ok": False, "mensaje": "Formato de email inválido"}), 400
    if not is_strong_password(plain):
        # no revelar detalles en producción; aquí es para desarrollo
        return jsonify({"ok": False, "mensaje": "Contraseña inválida"}), 400

    ok, payload = authenticate_user(correo, plain)
    if not ok:
        return jsonify({"ok": False, "mensaje": payload}), 401

    # Generar token con información del usuario
    user_type = payload.get('user_type', 'participante')
    user_id = payload.get('user_id')
    token = create_token(correo, user_type=user_type, user_id=user_id)
    
    return jsonify({
        "ok": True, 
        "data": payload, 
        "token": token,
        "user_type": user_type,
        "user_id": user_id
    }), 200
