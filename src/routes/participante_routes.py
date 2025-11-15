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
    add_program_to_participante,
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
        # Compatibilidad: aceptar tanto 'programa_academico' como 'programa'
        programa = data.get('programa_academico') or data.get('programa')
        # Compatibilidad: aceptar tanto 'tipo_participante' como 'tipo'
        tipo = data.get('tipo_participante') or data.get('tipo')

        affected = create_participante(ci, data['nombre'], data['apellido'], data['email'], programa, tipo)
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

        # Compatibility: accept either 'tipo_participante' (canonical) or 'tipo' (label)
        provided_canonical = data.get('tipo_participante') if 'tipo_participante' in data else None
        provided_label = data.get('tipo') if 'tipo' in data else None

        # Helper to derive canonical from a label (e.g. 'Postgrado' -> 'postgrado')
        def canonical_from_label(label: str):
            if not label:
                return None
            l = str(label).strip().lower()
            if l in ('estudiante', 'alumno'):
                return 'alumno'
            if l == 'postgrado':
                return 'postgrado'
            if l in ('docente', 'profesor'):
                return 'docente'
            return l

        # If both provided, validate they match (avoid silent mismatches from frontend)
        if provided_canonical is not None and provided_label is not None:
            canon_norm = str(provided_canonical).strip().lower()
            canon_from_label = canonical_from_label(provided_label)
            if canon_from_label is not None and canon_norm != canon_from_label:
                return jsonify({'error': 'Inconsistencia entre tipo_participante y tipo',
                                'tipo_participante': provided_canonical,
                                'tipo': provided_label,
                                'detalle': f"tipo_participante '{provided_canonical}' no coincide con tipo '{provided_label}' (esperado canonical '{canon_from_label}')"}), 400

        # Decide which raw value to use for normalization: prefer canonical if present
        raw_tipo = provided_canonical if provided_canonical is not None else provided_label
        # Compatibility for programa name
        programa = data.get('programa_academico') if 'programa_academico' in data else data.get('programa')

        tipo_canonical = None
        if raw_tipo is not None:
            if not str(raw_tipo).strip():
                return jsonify({'error': 'tipo_participante cannot be empty'}), 400
            rt = str(raw_tipo).lower()
            if rt in ('estudiante', 'alumno'):
                tipo_canonical = 'alumno'
            elif rt == 'postgrado':
                tipo_canonical = 'postgrado'
            elif rt in ('docente', 'profesor'):
                tipo_canonical = 'docente'
            elif rt == 'otro':
                tipo_canonical = 'otro'
            else:
                return jsonify({'error': 'tipo_participante inválido'}), 400

        affected = update_participante(
            ci,
            nombre=data.get('nombre'),
            apellido=data.get('apellido'),
            email=data.get('email'),
            tipo_participante=tipo_canonical,
            programa_academico=programa,
        )

        if affected == 0:
            return jsonify({'message': 'no changes made', 'updated': 0}), 200

        # Return the updated participante for frontend convenience
        updated = get_participante_by_ci(ci)
        return jsonify({'updated': affected, 'participante': updated}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'internal error', 'detail': str(e)}), 500


@participante_bp.route('/<int:ci>', methods=['DELETE'])
@jwt_required
@require_admin
def delete_participante_route(ci: int):
    """Elimina un participante."""
    try:
        existing = get_participante_by_ci(ci)
        if not existing:
            return jsonify({'error': 'participante not found'}), 404
        # Soportar borrado forzado desde el endpoint: ?force=true
        force = str(request.args.get('force', 'false')).lower() == 'true'

        # El endpoint DELETE ahora requiere autenticación y permisos de admin
        affected = delete_participante(ci, force=force)
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

