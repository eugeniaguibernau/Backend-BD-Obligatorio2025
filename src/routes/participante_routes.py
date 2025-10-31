from flask import Blueprint, request, jsonify, g
import re
from src.models.participante_model import (
    create_participante,
    get_participante_by_ci,
    get_participante_by_email,
    list_participantes,
    update_participante,
    delete_participante,
    get_participante_with_programs,
    get_participante_sanciones,
)
from src.utils.response import with_auth_link
from src.auth.jwt_utils import jwt_required
from src.middleware.permissions import require_admin, can_modify_resource

participante_bp = Blueprint('participante_bp', __name__)

# Regex para validar formato de email
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

# Límites de longitud según esquema SQL
MAX_NOMBRE_LENGTH = 20
MAX_APELLIDO_LENGTH = 20
MAX_EMAIL_LENGTH = 30


@participante_bp.route('/', methods=['POST'])
def create_participante_route():
    data = request.get_json() or {}
    required = ['ci', 'nombre', 'apellido', 'email']

    for field in required:
        if field not in data:
            return jsonify({'error': f'Missing field: {field}'}), 400

    try:
        ci = int(data['ci'])
    except (ValueError, TypeError):
        return jsonify({'error': 'ci must be an integer'}), 400

    # Validaciones básicas
    if ci <= 0:
        return jsonify({'error': 'ci must be positive'}), 400

    # Validar campos no vacíos
    if not data.get('nombre') or not data['nombre'].strip():
        return jsonify({'error': 'nombre is required and cannot be empty'}), 400

    if not data.get('apellido') or not data['apellido'].strip():
        return jsonify({'error': 'apellido is required and cannot be empty'}), 400

    # Validar longitud de campos
    if len(data['nombre']) > MAX_NOMBRE_LENGTH:
        return jsonify({'error': f'nombre cannot exceed {MAX_NOMBRE_LENGTH} characters'}), 400

    if len(data['apellido']) > MAX_APELLIDO_LENGTH:
        return jsonify({'error': f'apellido cannot exceed {MAX_APELLIDO_LENGTH} characters'}), 400

    if len(data['email']) > MAX_EMAIL_LENGTH:
        return jsonify({'error': f'email cannot exceed {MAX_EMAIL_LENGTH} characters'}), 400

    if not data['email'] or not re.match(EMAIL_REGEX, data['email']):
        return jsonify({'error': 'email format is invalid (must be usuario@dominio.extension)'}), 400

    try:
        affected = create_participante(ci, data['nombre'], data['apellido'], data['email'])
        return jsonify({'created': affected, 'ci': ci}), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'internal error', 'detail': str(e)}), 500


@participante_bp.route('/', methods=['GET'])
@jwt_required
def list_participantes_route():
    """
    Lista todos los participantes.

    Query params opcionales:
    - limit: número máximo de resultados
    - offset: desplazamiento para paginación
    - email: filtrar por email exacto
    """
    email = request.args.get('email')

    if email:
        # Búsqueda por email
        try:
            participante = get_participante_by_email(email)
            if not participante:
                return jsonify({'error': 'not found'}), 404
            return jsonify(with_auth_link({'participante': participante})), 200
        except Exception as e:
            return jsonify({'error': 'internal error', 'detail': str(e)}), 500

    # Lista general
    limit = request.args.get('limit')
    offset = request.args.get('offset')

    try:
        limit_int = int(limit) if limit is not None else None
        offset_int = int(offset) if offset is not None else None
    except ValueError:
        return jsonify({'error': 'limit and offset must be integers'}), 400

    try:
        participantes = list_participantes(limit=limit_int, offset=offset_int)
        return jsonify(with_auth_link({'participantes': participantes, 'count': len(participantes)})), 200
    except Exception as e:
        return jsonify({'error': 'internal error', 'detail': str(e)}), 500


@participante_bp.route('/<int:ci>', methods=['GET'])
@jwt_required
def get_participante_route(ci: int):
    """
    Obtiene un participante por CI.
    - Admin: puede ver cualquier participante
    - Participante: solo puede ver su propia información

    Query params opcionales:
    - detailed: si es "true", incluye programas académicos
    """
    # Verificar permisos
    user_type = getattr(g, 'user_type', 'participante')
    user_id = getattr(g, 'user_id', None)
    
    if user_type != 'admin' and str(user_id) != str(ci):
        return jsonify({
            'ok': False,
            'mensaje': 'No tiene permisos para ver este participante'
        }), 403
    
    detailed = request.args.get('detailed', '').lower() == 'true'

    try:
        if detailed:
            participante = get_participante_with_programs(ci)
        else:
            participante = get_participante_by_ci(ci)

        if not participante:
            return jsonify({'error': 'not found'}), 404

        return jsonify(with_auth_link({'participante': participante})), 200
    except Exception as e:
        return jsonify({'error': 'internal error', 'detail': str(e)}), 500


@participante_bp.route('/<int:ci>', methods=['PUT'])
@jwt_required
def update_participante_route(ci: int):
    """
    Actualiza un participante.
    - Admin: puede actualizar cualquier participante
    - Participante: solo puede actualizar su propia información

    Body JSON (todos opcionales):
    {
        "nombre": "Juan Carlos",
        "apellido": "Pérez",
        "email": "nuevo.email@example.com"
    }
    """
    # Verificar permisos
    if not can_modify_resource(ci):
        return jsonify({
            'ok': False,
            'mensaje': 'No tiene permisos para modificar este participante'
        }), 403
        
    data = request.get_json() or {}

    if not data:
        return jsonify({'error': 'No fields to update'}), 400

    # Validar campos no vacíos si se proporcionan
    if 'nombre' in data and (not data['nombre'] or not data['nombre'].strip()):
        return jsonify({'error': 'nombre cannot be empty'}), 400

    if 'apellido' in data and (not data['apellido'] or not data['apellido'].strip()):
        return jsonify({'error': 'apellido cannot be empty'}), 400

    if 'email' in data and (not data['email'] or not data['email'].strip()):
        return jsonify({'error': 'email cannot be empty'}), 400

    # Validar longitud de campos si se proporcionan
    if 'nombre' in data and len(data['nombre']) > MAX_NOMBRE_LENGTH:
        return jsonify({'error': f'nombre cannot exceed {MAX_NOMBRE_LENGTH} characters'}), 400

    if 'apellido' in data and len(data['apellido']) > MAX_APELLIDO_LENGTH:
        return jsonify({'error': f'apellido cannot exceed {MAX_APELLIDO_LENGTH} characters'}), 400

    if 'email' in data and len(data['email']) > MAX_EMAIL_LENGTH:
        return jsonify({'error': f'email cannot exceed {MAX_EMAIL_LENGTH} characters'}), 400

    # Validar email si se proporciona
    if 'email' in data and data['email']:
        if not re.match(EMAIL_REGEX, data['email']):
            return jsonify({'error': 'email format is invalid (must be usuario@dominio.extension)'}), 400

    try:
        # Verificar que el participante existe
        existing = get_participante_by_ci(ci)
        if not existing:
            return jsonify({'error': 'participante not found'}), 404

        affected = update_participante(
            ci,
            nombre=data.get('nombre'),
            apellido=data.get('apellido'),
            email=data.get('email')
        )

        if affected == 0:
            return jsonify({'message': 'no changes made', 'updated': 0}), 200

        return jsonify({'updated': affected}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'internal error', 'detail': str(e)}), 500


@participante_bp.route('/<int:ci>', methods=['DELETE'])
@jwt_required
@require_admin  # Solo admins pueden eliminar participantes
def delete_participante_route(ci: int):
    """
    Elimina un participante.
    REQUIERE PERMISOS DE ADMINISTRADOR

    Validaciones:
    - No puede tener login asociado
    - No puede estar en programas académicos
    - No puede tener sanciones vigentes
    - No puede tener reservas activas
    """
    try:
        # Verificar que existe
        existing = get_participante_by_ci(ci)
        if not existing:
            return jsonify({'error': 'participante not found'}), 404

        affected = delete_participante(ci)
        return jsonify({'deleted': affected, 'ci': ci}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'internal error', 'detail': str(e)}), 500


@participante_bp.route('/<int:ci>/sanciones', methods=['GET'])
@jwt_required
def get_sanciones_route(ci: int):
    """
    Obtiene todas las sanciones de un participante.
    """
    try:
        # Verificar que el participante existe
        existing = get_participante_by_ci(ci)
        if not existing:
            return jsonify({'error': 'participante not found'}), 404

        sanciones = get_participante_sanciones(ci)
        return jsonify(with_auth_link({'sanciones': sanciones, 'count': len(sanciones)})), 200
    except Exception as e:
        return jsonify({'error': 'internal error', 'detail': str(e)}), 500
from flask import Blueprint, request, jsonify
import re
from src.models.participante_model import (
    create_participante,
    get_participante_by_ci,
    get_participante_by_email,
    list_participantes,
    update_participante,
    delete_participante,
    get_participante_with_programs,
    get_participante_sanciones,
)
from src.utils.response import with_auth_link

participante_bp = Blueprint('participante_bp', __name__)

# Regex para validar formato de email
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

# Límites de longitud según esquema SQL
MAX_NOMBRE_LENGTH = 20
MAX_APELLIDO_LENGTH = 20
MAX_EMAIL_LENGTH = 30


@participante_bp.route('/', methods=['POST'])
def create_participante_route():
    data = request.get_json() or {}
    required = ['ci', 'nombre', 'apellido', 'email']

    for field in required:
        if field not in data:
            return jsonify({'error': f'Missing field: {field}'}), 400

    try:
        ci = int(data['ci'])
    except (ValueError, TypeError):
        return jsonify({'error': 'ci must be an integer'}), 400

    # Validaciones básicas
    if ci <= 0:
        return jsonify({'error': 'ci must be positive'}), 400

    # Validar campos no vacíos
    if not data.get('nombre') or not data['nombre'].strip():
        return jsonify({'error': 'nombre is required and cannot be empty'}), 400

    if not data.get('apellido') or not data['apellido'].strip():
        return jsonify({'error': 'apellido is required and cannot be empty'}), 400

    # Validar longitud de campos
    if len(data['nombre']) > MAX_NOMBRE_LENGTH:
        return jsonify({'error': f'nombre cannot exceed {MAX_NOMBRE_LENGTH} characters'}), 400

    if len(data['apellido']) > MAX_APELLIDO_LENGTH:
        return jsonify({'error': f'apellido cannot exceed {MAX_APELLIDO_LENGTH} characters'}), 400

    if len(data['email']) > MAX_EMAIL_LENGTH:
        return jsonify({'error': f'email cannot exceed {MAX_EMAIL_LENGTH} characters'}), 400

    if not data['email'] or not re.match(EMAIL_REGEX, data['email']):
        return jsonify({'error': 'email format is invalid (must be usuario@dominio.extension)'}), 400

    try:
        affected = create_participante(ci, data['nombre'], data['apellido'], data['email'])
        return jsonify({'created': affected, 'ci': ci}), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'internal error', 'detail': str(e)}), 500


@participante_bp.route('/', methods=['GET'])
@jwt_required
def list_participantes_route():
    """Lista todos los participantes.

    Query params opcionales:
    - limit: número máximo de resultados
    - offset: desplazamiento para paginación
    - email: filtrar por email exacto
    """
    email = request.args.get('email')

    if email:
        try:
            participante = get_participante_by_email(email)
            if not participante:
                return jsonify({'error': 'not found'}), 404
            return jsonify(with_auth_link({'participante': participante})), 200
        except Exception as e:
            return jsonify({'error': 'internal error', 'detail': str(e)}), 500

    limit = request.args.get('limit')
    offset = request.args.get('offset')

    try:
        limit_int = int(limit) if limit is not None else None
        offset_int = int(offset) if offset is not None else None
    except ValueError:
        return jsonify({'error': 'limit and offset must be integers'}), 400

    try:
        participantes = list_participantes(limit=limit_int, offset=offset_int)
        return jsonify(with_auth_link({'participantes': participantes, 'count': len(participantes)})), 200
    except Exception as e:
        return jsonify({'error': 'internal error', 'detail': str(e)}), 500


@participante_bp.route('/<int:ci>', methods=['GET'])
@jwt_required
def get_participante_route(ci: int):
    """Obtiene un participante por CI.

    Query params opcionales:
    - detailed: si es "true", incluye programas académicos
    """
    detailed = request.args.get('detailed', '').lower() == 'true'

    try:
        if detailed:
            participante = get_participante_with_programs(ci)
        else:
            participante = get_participante_by_ci(ci)

        if not participante:
            return jsonify({'error': 'not found'}), 404

        return jsonify(with_auth_link({'participante': participante})), 200
    except Exception as e:
        return jsonify({'error': 'internal error', 'detail': str(e)}), 500


@participante_bp.route('/<int:ci>', methods=['PUT'])
def update_participante_route(ci: int):
    """Actualiza un participante."""
    data = request.get_json() or {}

    if not data:
        return jsonify({'error': 'No fields to update'}), 400

    if 'nombre' in data and (not data['nombre'] or not data['nombre'].strip()):
        return jsonify({'error': 'nombre cannot be empty'}), 400

    if 'apellido' in data and (not data['apellido'] or not data['apellido'].strip()):
        return jsonify({'error': 'apellido cannot be empty'}), 400

    if 'email' in data and (not data['email'] or not data['email'].strip()):
        return jsonify({'error': 'email cannot be empty'}), 400

    if 'nombre' in data and len(data['nombre']) > MAX_NOMBRE_LENGTH:
        return jsonify({'error': f'nombre cannot exceed {MAX_NOMBRE_LENGTH} characters'}), 400

    if 'apellido' in data and len(data['apellido']) > MAX_APELLIDO_LENGTH:
        return jsonify({'error': f'apellido cannot exceed {MAX_APELLIDO_LENGTH} characters'}), 400

    if 'email' in data and len(data['email']) > MAX_EMAIL_LENGTH:
        return jsonify({'error': f'email cannot exceed {MAX_EMAIL_LENGTH} characters'}), 400

    if 'email' in data and data['email']:
        if not re.match(EMAIL_REGEX, data['email']):
            return jsonify({'error': 'email format is invalid (must be usuario@dominio.extension)'}), 400

    try:
        existing = get_participante_by_ci(ci)
        if not existing:
            return jsonify({'error': 'participante not found'}), 404

        affected = update_participante(
            ci,
            nombre=data.get('nombre'),
            apellido=data.get('apellido'),
            email=data.get('email'),
        )

        if affected == 0:
            return jsonify({'message': 'no changes made', 'updated': 0}), 200

        return jsonify({'updated': affected}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'internal error', 'detail': str(e)}), 500


@participante_bp.route('/<int:ci>', methods=['DELETE'])
def delete_participante_route(ci: int):
    """Elimina un participante."""
    try:
        existing = get_participante_by_ci(ci)
        if not existing:
            return jsonify({'error': 'participante not found'}), 404
        
        affected = delete_participante(ci)
        return jsonify({'deleted': affected, 'ci': ci}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'internal error', 'detail': str(e)}), 500


@participante_bp.route('/<int:ci>/sanciones', methods=['GET'])
@jwt_required
def get_sanciones_route(ci: int):
    """Obtiene todas las sanciones de un participante."""
    try:
        existing = get_participante_by_ci(ci)
        if not existing:
            return jsonify({'error': 'participante not found'}), 404

        sanciones = get_participante_sanciones(ci)
        return jsonify(with_auth_link({'sanciones': sanciones, 'count': len(sanciones)})), 200
    except Exception as e:
        return jsonify({'error': 'internal error', 'detail': str(e)}), 500

