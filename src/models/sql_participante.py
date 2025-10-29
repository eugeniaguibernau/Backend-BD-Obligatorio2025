from typing import Any, Dict, List, Optional
from src.config.database import execute_query, execute_non_query, get_connection
import pymysql


def create_participante(ci: int, nombre: str, apellido: str, email: str) -> int:
    """Crea un participante. Valida que CI y email sean únicos."""
    query = """
    INSERT INTO participante (ci, nombre, apellido, email)
    VALUES (%s, %s, %s, %s)
    """
    try:
        affected = execute_non_query(query, (ci, nombre, apellido, email))
        return affected
    except pymysql.IntegrityError as e:
        if 'Duplicate entry' in str(e):
            if 'PRIMARY' in str(e):
                raise ValueError(f"Ya existe un participante con CI {ci}")
            elif 'email' in str(e):
                raise ValueError(f"Ya existe un participante con email {email}")
        raise


def get_participante_by_ci(ci: int) -> Optional[Dict[str, Any]]:
    """Obtiene un participante por CI."""
    query = "SELECT ci, nombre, apellido, email FROM participante WHERE ci=%s"
    rows = execute_query(query, (ci,))
    return rows[0] if rows else None


def get_participante_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Obtiene un participante por email."""
    query = "SELECT ci, nombre, apellido, email FROM participante WHERE email=%s"
    rows = execute_query(query, (email,))
    return rows[0] if rows else None


def list_participantes(limit: Optional[int] = None, offset: Optional[int] = None) -> List[Dict[str, Any]]:
    """Lista todos los participantes con paginación opcional."""
    query = "SELECT ci, nombre, apellido, email FROM participante"
    params = []
    
    if limit is not None:
        query += " LIMIT %s"
        params.append(limit)
        if offset is not None:
            query += " OFFSET %s"
            params.append(offset)
    
    return execute_query(query, tuple(params) if params else None)


def update_participante(ci: int, nombre: Optional[str] = None, 
                       apellido: Optional[str] = None, 
                       email: Optional[str] = None) -> int:
    """
    Actualiza datos de un participante.
    Solo actualiza los campos proporcionados (no None).
    """
    sets: List[str] = []
    params: List[Any] = []
    
    if nombre is not None:
        sets.append("nombre=%s")
        params.append(nombre)
    if apellido is not None:
        sets.append("apellido=%s")
        params.append(apellido)
    if email is not None:
        sets.append("email=%s")
        params.append(email)
    
    if not sets:
        return 0
    
    params.append(ci)
    query = f"UPDATE participante SET {', '.join(sets)} WHERE ci=%s"
    
    try:
        return execute_non_query(query, tuple(params))
    except pymysql.IntegrityError as e:
        if 'Duplicate entry' in str(e) and 'email' in str(e):
            raise ValueError(f"Ya existe un participante con email {email}")
        raise


def delete_participante(ci: int) -> int:
    """
    Elimina un participante.
    
    Validaciones:
    - No se puede eliminar si tiene login asociado
    - No se puede eliminar si tiene reservas activas
    - No se puede eliminar si tiene sanciones vigentes
    - No se puede eliminar si está en participante_programa_academico
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Verificar si tiene login
            cur.execute("SELECT COUNT(*) as count FROM login l JOIN participante p ON l.correo = p.email WHERE p.ci = %s", (ci,))
            if cur.fetchone()['count'] > 0:
                raise ValueError("No se puede eliminar: el participante tiene login asociado. Elimine primero el login.")
            
            # Verificar si está en participante_programa_academico
            cur.execute("SELECT COUNT(*) as count FROM participante_programa_academico WHERE ci_participante = %s", (ci,))
            if cur.fetchone()['count'] > 0:
                raise ValueError("No se puede eliminar: el participante está asociado a programas académicos.")
            
            # Verificar sanciones vigentes
            cur.execute("""
                SELECT COUNT(*) as count FROM sancion_participante sp
                JOIN participante_programa_academico ppa ON sp.ci_participante = ppa.ci_participante
                WHERE ppa.ci_participante = %s AND sp.fecha_fin >= CURDATE()
            """, (ci,))
            if cur.fetchone()['count'] > 0:
                raise ValueError("No se puede eliminar: el participante tiene sanciones vigentes.")
            
            # Verificar reservas activas
            cur.execute("""
                SELECT COUNT(*) as count FROM reserva_participante rp
                JOIN participante_programa_academico ppa ON rp.ci_participante = ppa.ci_participante
                JOIN reserva r ON rp.id_reserva = r.id_reserva
                WHERE ppa.ci_participante = %s AND r.estado IN ('activa', 'finalizada')
            """, (ci,))
            if cur.fetchone()['count'] > 0:
                raise ValueError("No se puede eliminar: el participante tiene reservas activas o finalizadas.")
            
            # Si pasa todas las validaciones, eliminar
            affected = cur.execute("DELETE FROM participante WHERE ci=%s", (ci,))
            conn.commit()
            return affected
    finally:
        conn.close()


def get_participante_with_programs(ci: int) -> Optional[Dict[str, Any]]:
    """Obtiene un participante con sus programas académicos asociados."""
    query = """
    SELECT 
        p.ci, p.nombre, p.apellido, p.email,
        ppa.nombre_programa, ppa.rol, ppa.id_alumno_programa
    FROM participante p
    LEFT JOIN participante_programa_academico ppa ON p.ci = ppa.ci_participante
    WHERE p.ci = %s
    """
    rows = execute_query(query, (ci,))
    
    if not rows:
        return None
    
    # Construir estructura con participante y sus programas
    participante = {
        'ci': rows[0]['ci'],
        'nombre': rows[0]['nombre'],
        'apellido': rows[0]['apellido'],
        'email': rows[0]['email'],
        'programas': []
    }
    
    for row in rows:
        if row['nombre_programa']:  # Si tiene programa asociado
            participante['programas'].append({
                'id_alumno_programa': row['id_alumno_programa'],
                'nombre_programa': row['nombre_programa'],
                'rol': row['rol']
            })
    
    return participante


def get_participante_sanciones(ci: int) -> List[Dict[str, Any]]:
    """Obtiene las sanciones de un participante."""
    query = """
    SELECT sp.fecha_inicio, sp.fecha_fin, sp.ci_participante
    FROM sancion_participante sp
    JOIN participante_programa_academico ppa ON sp.ci_participante = ppa.ci_participante
    WHERE ppa.ci_participante = %s
    ORDER BY sp.fecha_inicio DESC
    """
    return execute_query(query, (ci,))
