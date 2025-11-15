from typing import Any, Dict, List, Optional
from src.config.database import execute_query, execute_non_query, get_connection


VALID_TIPOS = ('libre', 'posgrado', 'docente')


def create_sala(nombre_sala: str, edificio: str, capacidad: int, tipo_sala: str, id_facultad: Optional[int] = None) -> int:
    if tipo_sala not in VALID_TIPOS:
        raise ValueError(f"tipo_sala must be one of {VALID_TIPOS}")

    query = """
        INSERT INTO sala (nombre_sala, edificio, capacidad, tipo_sala, id_facultad)
        VALUES (%s, %s, %s, %s, %s)
    """
    return execute_non_query(query, (nombre_sala, edificio, capacidad, tipo_sala, id_facultad))


def get_sala(nombre_sala: str, edificio: str) -> Optional[Dict[str, Any]]:
    query = """
        SELECT s.nombre_sala, s.edificio, s.capacidad, s.tipo_sala, s.id_facultad, f.nombre as facultad_nombre
        FROM sala s
        LEFT JOIN facultad f ON s.id_facultad = f.id_facultad
        WHERE s.nombre_sala = %s AND s.edificio = %s
    """
    rows = execute_query(query, (nombre_sala, edificio), role='readonly')
    return rows[0] if rows else None


def list_salas(edificio: Optional[str] = None, tipo_sala: Optional[str] = None, min_capacidad: Optional[int] = None) -> List[Dict[str, Any]]:
    query = """
        SELECT s.nombre_sala, s.edificio, s.capacidad, s.tipo_sala, s.id_facultad, f.nombre as facultad_nombre
        FROM sala s
        LEFT JOIN facultad f ON s.id_facultad = f.id_facultad
    """
    filters = []
    params = []
    if edificio:
        filters.append("s.edificio = %s")
        params.append(edificio)
    if tipo_sala:
        if tipo_sala not in VALID_TIPOS:
            raise ValueError(f"tipo_sala must be one of {VALID_TIPOS}")
        filters.append("s.tipo_sala = %s")
        params.append(tipo_sala)
    if min_capacidad is not None:
        filters.append("s.capacidad >= %s")
        params.append(min_capacidad)

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += " ORDER BY s.nombre_sala, s.edificio"

    return execute_query(query, tuple(params) if params else None, role='readonly')


def update_sala(nombre_sala: str, edificio: str, capacidad: Optional[int] = None, tipo_sala: Optional[str] = None, id_facultad: Optional[int] = None) -> int:
    sets = []
    params = []
    if capacidad is not None:
        sets.append("capacidad = %s")
        params.append(capacidad)
    if tipo_sala is not None:
        if tipo_sala not in VALID_TIPOS:
            raise ValueError(f"tipo_sala must be one of {VALID_TIPOS}")
        sets.append("tipo_sala = %s")
        params.append(tipo_sala)
    if id_facultad is not None:
        sets.append("id_facultad = %s")
        params.append(id_facultad)

    if not sets:
        return 0

    params.extend([nombre_sala, edificio])
    query = f"UPDATE sala SET {', '.join(sets)} WHERE nombre_sala = %s AND edificio = %s"
    return execute_non_query(query, tuple(params))


def delete_sala(nombre_sala: str, edificio: str) -> int:
    # ensure there are no active or future reservations
    conn = get_connection(role='readonly')
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS c FROM reserva WHERE nombre_sala = %s AND edificio = %s AND (estado = 'activa' OR fecha >= CURDATE())", (nombre_sala, edificio))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row and row.get('c', 0) > 0:
        raise ValueError('La sala tiene reservas activas o futuras y no puede ser eliminada')

    return execute_non_query("DELETE FROM sala WHERE nombre_sala = %s AND edificio = %s", (nombre_sala, edificio))
