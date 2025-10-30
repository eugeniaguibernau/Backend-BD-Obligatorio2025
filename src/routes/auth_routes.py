from flask import Blueprint, request, jsonify
from src.auth.login import hash_password, authenticate_user
from src.config.database import get_connection

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    correo = data.get('correo')
    plain = data.get('contraseña')
    participante = data.get('participante') or {}

    if not correo or not plain:
        return jsonify({"ok": False, "mensaje": "correo y contraseña requeridos"}), 400

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
def login():
    data = request.get_json() or {}
    correo = data.get('correo')
    plain = data.get('contraseña')

    if not correo or not plain:
        return jsonify({"ok": False, "mensaje": "correo y contraseña requeridos"}), 400

    ok, payload = authenticate_user(correo, plain)
    if not ok:
        # payload is an error message
        return jsonify({"ok": False, "mensaje": payload}), 401

    return jsonify({"ok": True, "data": payload}), 200
