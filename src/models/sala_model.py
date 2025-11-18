from typing import Any, Dict, List, Optional
from src.config.database import execute_query, execute_non_query, get_connection

VALID_TIPOS = ('libre', 'posgrado', 'docente')


def create_sala(
    nombre_sala: str,
    edificio: str,
    capacidad: int,
    tipo_sala: str
) -> int:
    if tipo_sala not in VALID_TIPOS:
        raise ValueError(f"tipo_sala must be one of {VALID_TIPOS}")

    query = """
        INSERT INTO sala (nombre_sala, edificio, capacidad, tipo_sala)
        VALUES (%s, %s, %s, %s)
    """
    return execute_non_query(query, (nombre_sala, edificio, capacidad, tipo_sala), role='admin')


def get_sala(nombre_sala: str, edificio: str) -> Optional[Dict[str, Any]]:
    query = """
        SELECT nombre_sala, edificio, capacidad, tipo_sala
        FROM sala
        WHERE nombre_sala = %s AND edificio = %s
    """
    rows = execute_query(query, (nombre_sala, edificio), role='readonly')
    return rows[0] if rows else None


def list_salas(
    edificio: Optional[str] = None,
    tipo_sala: Optional[str] = None,
    min_capacidad: Optional[int] = None
) -> List[Dict[str, Any]]:
    query = """
        SELECT nombre_sala, edificio, capacidad, tipo_sala
        FROM sala
        WHERE 1 = 1
    """
    filters = []
    params: List[Any] = []

    if edificio:
        query += " AND edificio = %s"
        params.append(edificio)

    if tipo_sala:
        if tipo_sala not in VALID_TIPOS:
            raise ValueError(f"tipo_sala must be one of {VALID_TIPOS}")
        query += " AND tipo_sala = %s"
        params.append(tipo_sala)

    if min_capacidad is not None:
        query += " AND capacidad >= %s"
        params.append(min_capacidad)

    query += " ORDER BY nombre_sala, edificio"
    return execute_query(query, tuple(params) if params else None, role='readonly')


def update_sala(
    nombre_sala: str,
    edificio: str,
    capacidad: Optional[int] = None,
    tipo_sala: Optional[str] = None
) -> int:
    sets = []
    params: List[Any] = []

    if capacidad is not None:
        sets.append("capacidad = %s")
        params.append(capacidad)

    if tipo_sala is not None:
        if tipo_sala not in VALID_TIPOS:
            raise ValueError(f"tipo_sala must be one of {VALID_TIPOS}")
        sets.append("tipo_sala = %s")
        params.append(tipo_sala)

    if not sets:
        return 0

    params.extend([nombre_sala, edificio])
    query = f"""
        UPDATE sala
        SET {', '.join(sets)}
        WHERE nombre_sala = %s AND edificio = %s
    """
    return execute_non_query(query, tuple(params), role='admin')


def delete_sala(nombre_sala: str, edificio: str) -> int:
    # Validar que no tenga reservas activas o futuras
    conn = get_connection(role='readonly')
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COUNT(*) AS c
            FROM reserva
            WHERE nombre_sala = %s
              AND edificio = %s
              AND (estado = 'activa' OR fecha >= CURDATE())
            """,
            (nombre_sala, edificio),
        )
        row = cur.fetchone()
    finally:
        cur.close()
        conn.close()

    if row and row.get('c', 0) > 0:
        raise ValueError('La sala tiene reservas activas o futuras y no puede ser eliminada')

    return execute_non_query(
        "DELETE FROM sala WHERE nombre_sala = %s AND edificio = %s",
        (nombre_sala, edificio),
        role='admin'
    )
