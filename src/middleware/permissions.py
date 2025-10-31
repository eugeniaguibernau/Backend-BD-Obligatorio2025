"""
Middleware para control de permisos basado en roles.
"""
from functools import wraps
from flask import g, jsonify
from src.auth.jwt_utils import jwt_required


def get_user_info():
    """Obtiene la información del usuario actual desde flask.g"""
    return {
        'email': getattr(g, 'current_user', None),
        'user_type': getattr(g, 'user_type', 'participante'),
        'user_id': getattr(g, 'user_id', None)
    }


def require_admin(fn):
    """
    Decorator que requiere que el usuario sea admin.
    Debe usarse DESPUÉS de @jwt_required
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user_info = get_user_info()
        if user_info['user_type'] != 'admin':
            return jsonify({
                'ok': False, 
                'mensaje': 'Se requieren permisos de administrador'
            }), 403
        return fn(*args, **kwargs)
    return wrapper


def require_owner_or_admin(get_resource_owner_id):
    """
    Decorator que permite acceso al dueño del recurso o a admins.
    
    Args:
        get_resource_owner_id: Función que recibe los mismos args/kwargs del endpoint
                                y retorna el ID del dueño del recurso
    
    Ejemplo:
        @require_owner_or_admin(lambda ci: ci)
        def get_participante(ci):
            # Solo el participante con ese CI o un admin pueden acceder
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user_info = get_user_info()
            
            # Admin tiene acceso a todo
            if user_info['user_type'] == 'admin':
                return fn(*args, **kwargs)
            
            # Obtener el ID del dueño del recurso
            resource_owner_id = get_resource_owner_id(*args, **kwargs)
            
            # Verificar si el usuario es el dueño
            if str(user_info['user_id']) == str(resource_owner_id):
                return fn(*args, **kwargs)
            
            return jsonify({
                'ok': False, 
                'mensaje': 'No tiene permisos para acceder a este recurso'
            }), 403
        
        return wrapper
    return decorator


def can_modify_resource(resource_owner_id):
    """
    Verifica si el usuario actual puede modificar un recurso.
    Retorna True si es admin o si es el dueño del recurso.
    """
    user_info = get_user_info()
    
    if user_info['user_type'] == 'admin':
        return True
    
    return str(user_info['user_id']) == str(resource_owner_id)
