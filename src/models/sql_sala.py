from typing import Any, Dict, List, Optional, Tuple
from src.config.database import execute_query, execute_non_query


VALID_TIPOS = {'libre', 'posgrado', 'docente'}


def create_sala(nombre_sala: str, edificio: str, capacidad: int, tipo_sala: str) -> int:
    # Validar capacidad positiva
    if capacidad <= 0:
        raise ValueError("La capacidad debe ser mayor a 0")
    
    if tipo_sala not in VALID_TIPOS:
        raise ValueError(f"tipo_sala debe ser uno de {VALID_TIPOS}")
    
    # Validar que el edificio existe
    edificio_exists = execute_query("SELECT nombre_edificio FROM edificio WHERE nombre_edificio=%s", (edificio,))
    if not edificio_exists:
        raise ValueError(f"El edificio '{edificio}' no existe")

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
        # Validar capacidad positiva
        if capacidad <= 0:
            raise ValueError("La capacidad debe ser mayor a 0")
        
        # Modificar capacidad solo si no afecta a reservas preexistentes
        # Verificar que la nueva capacidad no sea menor que el máximo de participantes en reservas activas
        max_participantes_query = """
            SELECT MAX(participantes_count) as max_count
            FROM (
                SELECT COUNT(rp.ci_participante) as participantes_count
                FROM reserva r
                JOIN reserva_participante rp ON r.id_reserva = rp.id_reserva
                WHERE r.nombre_sala = %s AND r.edificio = %s 
                AND r.estado IN ('activa', 'finalizada')
                GROUP BY r.id_reserva
            ) AS subquery
        """
        max_participantes_result = execute_query(max_participantes_query, (nombre_sala, edificio))
        
        if max_participantes_result and max_participantes_result[0]['max_count'] is not None:
            max_participantes = max_participantes_result[0]['max_count']
            if capacidad < max_participantes:
                raise ValueError(
                    f"No se puede reducir la capacidad a {capacidad}. "
                    f"Hay reservas activas con {max_participantes} participantes."
                )
        
        sets.append("capacidad=%s")
        params.append(capacidad)
    
    if tipo_sala is not None:
        if tipo_sala not in VALID_TIPOS:
            raise ValueError(f"tipo_sala debe ser uno de {VALID_TIPOS}")
        sets.append("tipo_sala=%s")
        params.append(tipo_sala)

    if not sets:
        return 0
    
    # Validar que el edificio existe si se está cambiando
    edificio_exists = execute_query("SELECT nombre_edificio FROM edificio WHERE nombre_edificio=%s", (edificio,))
    if not edificio_exists:
        raise ValueError(f"El edificio '{edificio}' no existe")

    params.extend([nombre_sala, edificio])
    query = f"UPDATE sala SET {', '.join(sets)} WHERE nombre_sala=%s AND edificio=%s"
    return execute_non_query(query, tuple(params))


def delete_sala(nombre_sala: str, edificio: str) -> int:
    """
    Elimina una sala.
    
    Validaciones:
    - No se puede eliminar si tiene reservas activas
    - No se puede eliminar si tiene reservas futuras
    """
    from src.config.database import get_connection
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Verificar si tiene reservas activas o futuras
            cur.execute("""
                SELECT COUNT(*) as count FROM reserva 
                WHERE nombre_sala=%s AND edificio=%s 
                AND (estado IN ('activa', 'finalizada') OR fecha >= CURDATE())
            """, (nombre_sala, edificio))
            
            if cur.fetchone()['count'] > 0:
                raise ValueError("No se puede eliminar: la sala tiene reservas activas o futuras.")
            
            # Si pasa la validación, eliminar
            affected = cur.execute("DELETE FROM sala WHERE nombre_sala=%s AND edificio=%s", (nombre_sala, edificio))
            conn.commit()
            return affected
    finally:
        conn.close()
