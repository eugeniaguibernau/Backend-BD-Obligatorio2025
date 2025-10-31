from flask import Blueprint, request, jsonify, current_app
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

    conn = get_connection()
    cur = conn.cursor()

    # Crear participante si no existe
    cur.execute("SELECT email FROM participante WHERE email = %s", (correo,))
    if not cur.fetchone():
        ci = participante.get('ci') or 0
        nombre = participante.get('nombre') or ''
        apellido = participante.get('apellido') or ''
        cur.execute(
            "INSERT INTO participante (ci, nombre, apellido, email) VALUES (%s,%s,%s,%s)",
            (ci, nombre, apellido, correo)
        )

    hashed = hash_password(plain)
    cur.execute("SELECT correo FROM login WHERE correo = %s", (correo,))
    if cur.fetchone():
        cur.execute("UPDATE login SET `contraseña` = %s WHERE correo = %s", (hashed, correo))
    else:
        cur.execute("INSERT INTO login (correo, `contraseña`) VALUES (%s, %s)", (correo, hashed))

    conn.commit()
    cur.close()
    conn.close()
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

    token = create_token(correo)
    return jsonify({"ok": True, "data": payload, "token": token}), 200
