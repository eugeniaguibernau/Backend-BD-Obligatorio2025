import os
import jwt
from datetime import datetime, timedelta

JWT_SECRET = os.environ.get('JWT_SECRET', 'dev-secret')
JWT_ALGORITHM = 'HS256'
JWT_EXP_HOURS = int(os.environ.get('JWT_EXP_HOURS', '2'))


def create_token(subject: str) -> str:
    now = datetime.utcnow()
    payload = {
        'sub': subject,
        'iat': now,
        'exp': now + timedelta(hours=JWT_EXP_HOURS)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def verify_token(token: str):
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return True, data
    except Exception as e:
        return False, str(e)


# Decorator simple para requerir JWT en rutas Flask
def jwt_required(fn):
    """Decorator pequeño y claro: verifica Authorization: Bearer <token>.

    En éxito pone el correo en flask.g.current_user y llama a la función.
    En fallo devuelve 401 con JSON simple.
    """
    from functools import wraps
    from flask import request, jsonify, g

    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        if not auth or not auth.startswith('Bearer '):
            return jsonify({'ok': False, 'mensaje': 'Authorization header missing or malformed'}), 401
        token = auth.split(' ', 1)[1].strip()
        ok, payload_or_err = verify_token(token)
        if not ok:
            return jsonify({'ok': False, 'mensaje': 'Token inválido', 'detalle': payload_or_err}), 401
        # payload_or_err es el payload decodificado
        try:
            g.current_user = payload_or_err.get('sub') if isinstance(payload_or_err, dict) else None
        except Exception:
            g.current_user = None
        return fn(*args, **kwargs)

    return wrapper
