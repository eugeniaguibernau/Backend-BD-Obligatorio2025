from typing import Any, Dict, List, Optional, Tuple
from src.config.database import execute_query, execute_non_query


VALID_TIPOS = {'libre', 'posgrado', 'docente'}


def create_sala(nombre_sala: str, edificio: str, capacidad: int, tipo_sala: str) -> int:
    if tipo_sala not in VALID_TIPOS:
        raise ValueError(f"tipo_sala debe ser uno de {VALID_TIPOS}")

    query = """
    INSERT INTO sala (nombre_sala, edificio, capacidad, tipo_sala)
    VALUES (%s, %s, %s, %s)
    """
    affected = execute_non_query(query, (nombre_sala, edificio, capacidad, tipo_sala))
    return affected


def get_sala(nombre_sala: str, edificio: str) -> Optional[Dict[str, Any]]:
    query = "SELECT nombre_sala, edificio, capacidad, tipo_sala FROM sala WHERE nombre_sala=%s AND edificio=%s"
    rows = execute_query(query, (nombre_sala, edificio))
    return rows[0] if rows else None


def list_salas(edificio: Optional[str] = None, tipo_sala: Optional[str] = None, min_capacidad: Optional[int] = None) -> List[Dict[str, Any]]:
    base = "SELECT nombre_sala, edificio, capacidad, tipo_sala FROM sala"
    filters: List[str] = []
    params: List[Any] = []
    if edificio:
        filters.append("edificio=%s")
        params.append(edificio)
    if tipo_sala:
        filters.append("tipo_sala=%s")
        params.append(tipo_sala)
    if min_capacidad is not None:
        filters.append("capacidad>=%s")
        params.append(min_capacidad)

    if filters:
        base = f"{base} WHERE {' AND '.join(filters)}"

    return execute_query(base, tuple(params))


def update_sala(nombre_sala: str, edificio: str, capacidad: Optional[int] = None, tipo_sala: Optional[str] = None) -> int:
    sets: List[str] = []
    params: List[Any] = []
    if capacidad is not None:
        sets.append("capacidad=%s")
        params.append(capacidad)
    if tipo_sala is not None:
        if tipo_sala not in VALID_TIPOS:
            raise ValueError(f"tipo_sala debe ser uno de {VALID_TIPOS}")
        sets.append("tipo_sala=%s")
        params.append(tipo_sala)

    if not sets:
        return 0

    params.extend([nombre_sala, edificio])
    query = f"UPDATE sala SET {', '.join(sets)} WHERE nombre_sala=%s AND edificio=%s"
    return execute_non_query(query, tuple(params))


def delete_sala(nombre_sala: str, edificio: str) -> int:
    query = "DELETE FROM sala WHERE nombre_sala=%s AND edificio=%s"
    return execute_non_query(query, (nombre_sala, edificio))
