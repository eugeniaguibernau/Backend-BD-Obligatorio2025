from flask import Blueprint, jsonify
from src.config.database import execute_query

programas_bp = Blueprint('programas_bp', __name__)


@programas_bp.route('/', methods=['GET'])
def list_programas():
    """Devuelve la lista de programas académicos disponibles.

    Response:
    {
        "programas": [
            {"nombre_programa": "Ingeniería Informática", "id_facultad": 1, "tipo": "grado"},
            ...
        ]
    }
    """
    query = "SELECT nombre_programa, id_facultad, tipo FROM programa_academico ORDER BY nombre_programa"
    rows = execute_query(query, role='readonly')

    # Deduplicate by exact nombre_programa and add value/label for frontend compatibility.
    seen = set()
    programas = []
    for r in rows:
        nombre = r.get('nombre_programa')
        if not nombre or nombre in seen:
            continue
        seen.add(nombre)
        programas.append({
            'nombre_programa': nombre,
            'id_facultad': r.get('id_facultad'),
            'tipo': r.get('tipo'),
            'value': nombre,
            'label': nombre,
        })

    return jsonify({'programas': programas}), 200


@programas_bp.route('/facultades', methods=['GET'])
def list_facultades():
    """Devuelve la lista de facultades para poblar selects en el frontend.

    Response:
    {
        "facultades": [ {"id_facultad": 1, "nombre": "Facultad de Ingeniería"}, ... ]
    }
    """
    query = "SELECT id_facultad, nombre FROM facultad ORDER BY nombre"
    rows = execute_query(query, role='readonly')

    facultades = []
    for r in rows:
        facultades.append({
            'id_facultad': r.get('id_facultad'),
            'nombre': r.get('nombre'),
            # frontend expects to send 'facultad' as the faculty name in reports endpoints,
            # so set value to nombre (label) to avoid extra frontend mapping.
            'value': r.get('nombre'),
            'label': r.get('nombre')
        })

    return jsonify({'facultades': facultades}), 200
