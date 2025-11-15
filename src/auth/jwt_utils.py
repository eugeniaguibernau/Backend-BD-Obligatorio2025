import os
import jwt
from datetime import datetime, timedelta
from typing import Dict, Any

JWT_SECRET = os.environ.get('JWT_SECRET', 'dev-secret')
JWT_ALGORITHM = 'HS256'
JWT_EXP_HOURS = int(os.environ.get('JWT_EXP_HOURS', '2'))


def create_token(subject: str, user_type: str = 'participante', user_id: Any = None, additional_claims: Dict = None) -> str:
    """
    Crea un JWT con información del usuario.
    
    Args:
        subject: Email del usuario
        user_type: 'admin' o 'participante'
        user_id: CI del participante o ID del admin
        additional_claims: Claims adicionales a incluir
    """
    now = datetime.utcnow()
    payload = {
        'sub': subject,
        'iat': now,
        'exp': now + timedelta(hours=JWT_EXP_HOURS),
        'user_type': user_type,
        'user_id': user_id
    }
    
    if additional_claims:
        payload.update(additional_claims)
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def verify_token(token: str):
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return True, data
    except jwt.ExpiredSignatureError:
        return False, 'expired'
    except Exception as e:
        return False, str(e)


# Decorator para requerir JWT en rutas Flask
def jwt_required(fn):
    """Decorator: verifica Authorization: Bearer <token>.

    En éxito pone información del usuario en flask.g y llama a la función.
    En fallo devuelve 401 con JSON simple.
    """
    from functools import wraps
    from flask import request, jsonify, g

    @wraps(fn)
    def wrapper(*args, **kwargs):
        # Allow preflight OPTIONS requests to pass through without JWT validation
        if request.method == 'OPTIONS':
            # Devuelve la respuesta OPTIONS por defecto de Flask para que
            # la extensión Flask-CORS pueda añadir los headers CORS correctamente.
            from flask import current_app
            return current_app.make_default_options_response()

        auth = request.headers.get('Authorization', '')
        if not auth or not auth.startswith('Bearer '):
            return jsonify({'ok': False, 'mensaje': 'Authorization header missing or malformed'}), 401
        token = auth.split(' ', 1)[1].strip()
        ok, payload_or_err = verify_token(token)
        if not ok:
            # Token expired -> 401 with clear message so frontend can logout
            if payload_or_err == 'expired':
                return jsonify({'ok': False, 'error': 'Token expired'}), 401
            return jsonify({'ok': False, 'mensaje': 'Token inválido', 'detalle': payload_or_err}), 401
        
        # Extraer información del usuario del token
        if isinstance(payload_or_err, dict):
            g.current_user = payload_or_err.get('sub')
            g.user_type = payload_or_err.get('user_type', 'participante')
            g.user_id = payload_or_err.get('user_id')
        else:
            g.current_user = None
            g.user_type = 'participante'
            g.user_id = None
            
        return fn(*args, **kwargs)

    return wrapper


def require_admin(fn):
    """Decorator: requiere que el usuario sea admin."""
    from functools import wraps
    from flask import jsonify, g

    @wraps(fn)
    @jwt_required
    def wrapper(*args, **kwargs):
        if getattr(g, 'user_type', None) != 'admin':
            return jsonify({'ok': False, 'mensaje': 'Se requieren permisos de administrador'}), 403
        return fn(*args, **kwargs)

    return wrapper
