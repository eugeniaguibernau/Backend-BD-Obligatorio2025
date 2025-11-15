from typing import Any, Dict, List, Optional
from src.config.database import execute_query, execute_non_query, get_connection
import pymysql
import re


# Regex para validar formato de email
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

# Límites de longitud según esquema SQL
MAX_NOMBRE_LENGTH = 20
MAX_APELLIDO_LENGTH = 20
MAX_EMAIL_LENGTH = 30


def _validate_email(email: str) -> bool:
    """Valida el formato del email usando regex."""
    return re.match(EMAIL_REGEX, email) is not None


def _validate_field_length(field_name: str, value: str, max_length: int) -> None:
    """Valida que un campo no exceda la longitud máxima."""
    if len(value) > max_length:
        raise ValueError(f"El {field_name} no puede exceder {max_length} caracteres")


def _validate_not_empty(field_name: str, value: str) -> None:
    """Valida que un campo no esté vacío."""
    if not value or not value.strip():
        raise ValueError(f"El {field_name} es obligatorio y no puede estar vacío")


def create_participante(ci: int, nombre: str, apellido: str, email: str,
                        programa_academico: Optional[str] = None,
                        tipo_participante: Optional[str] = None) -> int:
    """Crea un participante. Valida que CI y email sean únicos.

    Nota: la relación participante <-> programa se guarda en la tabla
    `participante_programa_academico`. Si se pasan `programa_academico`
    y `tipo_participante`, la función intentará crear también esa
    asociación (rol normalizado a 'alumno'|'docente').
    """
    # Validar campos no vacíos
    _validate_not_empty("nombre", nombre)
    _validate_not_empty("apellido", apellido)
    _validate_not_empty("email", email)
    
    # Validar longitud de campos
    _validate_field_length("nombre", nombre, MAX_NOMBRE_LENGTH)
    _validate_field_length("apellido", apellido, MAX_APELLIDO_LENGTH)
    _validate_field_length("email", email, MAX_EMAIL_LENGTH)
    
    # Validar formato de email
    if not _validate_email(email):
        raise ValueError(f"El email '{email}' no tiene un formato válido")
    
    query = """
    INSERT INTO participante (ci, nombre, apellido, email)
    VALUES (%s, %s, %s, %s)
    """
    try:
        affected = execute_non_query(query, (ci, nombre, apellido, email), role='user')
        # Si se recibieron datos de programa/rol, intentar asociarlos.
        if programa_academico or tipo_participante:
            # Requerir ambos valores para crear la asociación
            if not programa_academico or not tipo_participante:
                # No hacemos rollback del participante insertado; devolvemos error
                raise ValueError("Para asociar un programa se requieren 'programa_academico' y 'tipo_participante'.")

            # Normalizar tipo_participante a los valores de DB esperados
            tipo_norm = tipo_participante.lower()
            if tipo_norm in ('estudiante', 'alumno'):
                tipo_db = 'alumno'
            elif tipo_norm in ('docente', 'profesor'):
                tipo_db = 'docente'
            else:
                raise ValueError("tipo_participante inválido: debe ser 'alumno' o 'docente' (o 'Estudiante'/'Docente').")

            # add_program_to_participante usa execute_non_query internamente
            # y validará que el programa exista.
            add_program_to_participante(ci, programa_academico, tipo_db)

        return affected
    except pymysql.IntegrityError as e:
        if 'Duplicate entry' in str(e):
            if 'PRIMARY' in str(e):
                raise ValueError(f"Ya existe un participante con CI {ci}")
            elif 'email' in str(e):
                raise ValueError(f"Ya existe un participante con email {email}")
        raise


def get_participante_by_ci(ci: int) -> Optional[Dict[str, Any]]:
    """Obtiene un participante por CI, incluyendo su tipo/rol si existe."""
    query = """
        SELECT 
            p.ci, 
            p.nombre, 
            p.apellido, 
            p.email,
                ppa.rol as tipo_participante,
                ppa.nombre_programa as programa
        FROM participante p
        LEFT JOIN participante_programa_academico ppa ON p.ci = ppa.ci_participante
        WHERE p.ci = %s
        LIMIT 1
    """
    rows = execute_query(query, (ci,), role='readonly')
    if rows:
        # Si tiene múltiples programas, solo tomamos el primero
        # El tipo_participante será 'alumno', 'docente' o None
        result = rows[0].copy()
        # Normalizar el valor para el frontend
        # Mapear tipo a cadena amigable
        if result.get('tipo_participante'):
            tipo = result['tipo_participante']
            if tipo == 'alumno':
                result['tipo_participante'] = 'Estudiante'
            elif tipo == 'docente':
                result['tipo_participante'] = 'Docente'
        else:
            result['tipo_participante'] = None

        # Añadir campo 'programa' para el frontend (nombre del programa o None)
        result['programa'] = result.get('programa') if result.get('programa') else None
        return result
    return None


def get_participante_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Obtiene un participante por email, incluyendo su tipo/rol si existe."""
    query = """
        SELECT 
            p.ci, 
            p.nombre, 
            p.apellido, 
            p.email,
                ppa.rol as tipo_participante,
                ppa.nombre_programa as programa
        FROM participante p
        LEFT JOIN participante_programa_academico ppa ON p.ci = ppa.ci_participante
        WHERE p.email = %s
        LIMIT 1
    """
    rows = execute_query(query, (email,), role='readonly')
    if rows:
        result = rows[0].copy()
        # Normalizar el valor para el frontend
        if result.get('tipo_participante'):
            tipo = result['tipo_participante']
            if tipo == 'alumno':
                result['tipo_participante'] = 'Estudiante'
            elif tipo == 'docente':
                result['tipo_participante'] = 'Docente'
        else:
            result['tipo_participante'] = None

        result['programa'] = result.get('programa') if result.get('programa') else None
        return result
    return None


def list_participantes(limit: Optional[int] = None, offset: Optional[int] = None) -> List[Dict[str, Any]]:
    """Lista todos los participantes con paginación opcional, incluyendo su tipo/rol."""
    query = """
        SELECT 
            p.ci, 
            p.nombre, 
            p.apellido, 
            p.email,
                ppa.rol as tipo_participante,
                ppa.nombre_programa as programa
        FROM participante p
        LEFT JOIN participante_programa_academico ppa ON p.ci = ppa.ci_participante
    """
    params = []
    
    if limit is not None:
        query += " LIMIT %s"
        params.append(limit)
        if offset is not None:
            query += " OFFSET %s"
            params.append(offset)
    
    rows = execute_query(query, tuple(params) if params else None, role='readonly')
    
    # Normalizar los valores para el frontend
    result = []
    for row in rows:
        item = row.copy()
        if item.get('tipo_participante'):
            tipo = item['tipo_participante']
            if tipo == 'alumno':
                item['tipo_participante'] = 'Estudiante'
            elif tipo == 'docente':
                item['tipo_participante'] = 'Docente'
        else:
            item['tipo_participante'] = None

        # Normalizar programa
        item['programa'] = item.get('programa') if item.get('programa') else None
        result.append(item)
    
    return result


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
        # Validar campo no vacío
        _validate_not_empty("nombre", nombre)
        # Validar longitud
        _validate_field_length("nombre", nombre, MAX_NOMBRE_LENGTH)
        sets.append("nombre=%s")
        params.append(nombre)
    
    if apellido is not None:
        # Validar campo no vacío
        _validate_not_empty("apellido", apellido)
        # Validar longitud
        _validate_field_length("apellido", apellido, MAX_APELLIDO_LENGTH)
        sets.append("apellido=%s")
        params.append(apellido)
    
    if email is not None:
        # Validar campo no vacío
        _validate_not_empty("email", email)
        # Validar longitud
        _validate_field_length("email", email, MAX_EMAIL_LENGTH)
        # Validar formato de email
        if not _validate_email(email):
            raise ValueError(f"El email '{email}' no tiene un formato válido")
        sets.append("email=%s")
        params.append(email)
    
    if not sets:
        return 0
    
    params.append(ci)
    query = f"UPDATE participante SET {', '.join(sets)} WHERE ci=%s"
    
    try:
        return execute_non_query(query, tuple(params), role='user')
    except pymysql.IntegrityError as e:
        if 'Duplicate entry' in str(e) and 'email' in str(e):
            raise ValueError(f"Ya existe un participante con email {email}")
        raise


def delete_participante(ci: int, force: bool = False) -> int:
    """
    Elimina un participante.

    Si force == False (comportamiento por defecto) realiza las validaciones:
    - No se puede eliminar si tiene login asociado
    - No se puede eliminar si tiene reservas activas
    - No se puede eliminar si tiene sanciones vigentes
    - No se puede eliminar si está en participante_programa_academico

    Si force == True, realiza un borrado en cascada a nivel de aplicación:
    - elimina filas en reserva_participante, sancion_participante, participante_programa_academico
    - elimina login asociado (por correo)
    - elimina el participante

    Todas las operaciones se hacen dentro de la misma transacción usando la conexión admin.
    """
    conn = get_connection('admin')  # DELETE requiere rol admin
    try:
        with conn.cursor() as cur:
            if not force:
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
            else:
                # Borrado forzado: eliminamos relaciones y login antes de borrar participante
                # Obtener email (para borrar login)
                cur.execute("SELECT email FROM participante WHERE ci = %s", (ci,))
                row = cur.fetchone()
                if not row:
                    return 0
                email = row.get('email')

                # Borrar reservas asociadas (si existen)
                cur.execute("DELETE rp FROM reserva_participante rp WHERE rp.ci_participante = %s", (ci,))

                # Borrar sanciones del participante
                cur.execute("DELETE FROM sancion_participante WHERE ci_participante = %s", (ci,))

                # Borrar asociaciones a programas
                cur.execute("DELETE FROM participante_programa_academico WHERE ci_participante = %s", (ci,))

                # Borrar login asociado (por correo) si existe
                if email:
                    cur.execute("DELETE FROM login WHERE correo = %s", (email,))

                # Finalmente, borrar participante
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
    rows = execute_query(query, (ci,), role='readonly')
    
    if not rows:
        return None
    
    # Construir estructura con participante y sus programas
    participante = {
        'ci': rows[0]['ci'],
        'nombre': rows[0]['nombre'],
        'apellido': rows[0]['apellido'],
        'email': rows[0]['email'],
        'tipo_participante': None,  # Se asignará con el primer rol encontrado
        'programas': []
    }
    
    for row in rows:
        if row['nombre_programa']:  # Si tiene programa asociado
            # Asignar tipo_participante con el primer rol encontrado
            if participante['tipo_participante'] is None and row['rol']:
                if row['rol'] == 'alumno':
                    participante['tipo_participante'] = 'Estudiante'
                elif row['rol'] == 'docente':
                    participante['tipo_participante'] = 'Docente'
            
            participante['programas'].append({
                'id_alumno_programa': row['id_alumno_programa'],
                'nombre_programa': row['nombre_programa'],
                'rol': 'Estudiante' if row['rol'] == 'alumno' else 'Docente' if row['rol'] == 'docente' else row['rol']
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
    return execute_query(query, (ci,), role='readonly')


def add_program_to_participante(ci: int, nombre_programa: str, rol: str) -> int:
    """Asocia un participante a un programa académico con un rol ('alumno'|'docente').

    Reglas:
    - Valida que el programa existe en `programa_academico`.
    - Valida que `rol` sea 'alumno' o 'docente'.
    - Usa INSERT ... ON DUPLICATE KEY UPDATE para permitir re-asignar el programa/rol si ya existe.
    """
    if not nombre_programa or not nombre_programa.strip():
        raise ValueError("nombre_programa es requerido para asociar un programa")

    rol_norm = rol.lower() if rol else ''
    if rol_norm not in ('alumno', 'docente'):
        raise ValueError("rol inválido: debe ser 'alumno' o 'docente'")

    # Comprobar que el programa existe
    exists = execute_query(
        "SELECT 1 FROM programa_academico WHERE nombre_programa = %s LIMIT 1",
        (nombre_programa,),
        role='readonly'
    )
    if not exists:
        raise ValueError(f"Programa académico no encontrado: {nombre_programa}")

    # Insertar o actualizar la asociación. La columna ci_participante es UNIQUE por diseño.
    query = (
        "INSERT INTO participante_programa_academico (ci_participante, nombre_programa, rol) "
        "VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE nombre_programa = VALUES(nombre_programa), rol = VALUES(rol)"
    )
    return execute_non_query(query, (ci, nombre_programa, rol_norm), role='user')
