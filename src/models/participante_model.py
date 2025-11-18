from typing import Any, Dict, List, Optional
from src.config.database import execute_query, execute_non_query, get_connection
import pymysql
import re

EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

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
            elif tipo_norm == 'postgrado':
                tipo_db = 'postgrado'
            elif tipo_norm in ('docente', 'profesor'):
                tipo_db = 'docente'
            else:
                raise ValueError("tipo_participante inválido: debe ser 'alumno', 'postgrado' o 'docente' (ej. 'Estudiante'/'Postgrado'/'Docente').")

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
    """Obtiene un participante por CI, incluyendo TODOS sus programas y roles."""
    # Primero obtener datos básicos del participante
    query_participante = """
        SELECT ci, nombre, apellido, email
        FROM participante
        WHERE ci = %s
    """
    rows = execute_query(query_participante, (ci,), role='readonly')
    if not rows:
        return None
    
    result = rows[0].copy()
    
    # Luego obtener TODOS sus programas y roles
    query_programas = """
        SELECT nombre_programa, rol
        FROM participante_programa_academico
        WHERE ci_participante = %s
        ORDER BY nombre_programa, rol
    """
    programas_rows = execute_query(query_programas, (ci,), role='readonly')
    
    # Construir array de programas con roles normalizados
    programas = []
    for row in programas_rows:
        rol_db = row.get('rol')
        # Normalizar rol para el frontend
        if rol_db == 'alumno':
            rol_display = 'Estudiante'
        elif rol_db == 'postgrado':
            rol_display = 'Postgrado'
        elif rol_db == 'docente':
            rol_display = 'Docente'
        else:
            rol_display = rol_db
        
        programas.append({
            'programa': row.get('nombre_programa'),
            'tipo': rol_display
        })
    
    result['programas'] = programas
    
    # Retrocompatibilidad: si solo tiene un programa, incluir campos legacy
    if len(programas) == 1:
        result['programa'] = programas[0]['programa']
        result['tipo_participante'] = programas[0]['tipo']
    elif len(programas) == 0:
        result['programa'] = None
        result['tipo_participante'] = None
    else:
        # Múltiples programas: no hay un único programa/tipo
        result['programa'] = None
        result['tipo_participante'] = None
    
    return result


def get_participante_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Obtiene un participante por email, incluyendo TODOS sus programas y roles."""
    # Primero obtener datos básicos del participante
    query_participante = """
        SELECT ci, nombre, apellido, email
        FROM participante
        WHERE email = %s
    """
    rows = execute_query(query_participante, (email,), role='readonly')
    if not rows:
        return None
    
    result = rows[0].copy()
    ci = result['ci']
    
    # Luego obtener TODOS sus programas y roles
    query_programas = """
        SELECT nombre_programa, rol
        FROM participante_programa_academico
        WHERE ci_participante = %s
        ORDER BY nombre_programa, rol
    """
    programas_rows = execute_query(query_programas, (ci,), role='readonly')
    
    # Construir array de programas con roles normalizados
    programas = []
    for row in programas_rows:
        rol_db = row.get('rol')
        # Normalizar rol para el frontend
        if rol_db == 'alumno':
            rol_display = 'Estudiante'
        elif rol_db == 'postgrado':
            rol_display = 'Postgrado'
        elif rol_db == 'docente':
            rol_display = 'Docente'
        else:
            rol_display = rol_db
        
        programas.append({
            'programa': row.get('nombre_programa'),
            'tipo': rol_display
        })
    
    result['programas'] = programas
    
    # Retrocompatibilidad: si solo tiene un programa, incluir campos legacy
    if len(programas) == 1:
        result['programa'] = programas[0]['programa']
        result['tipo_participante'] = programas[0]['tipo']
    elif len(programas) == 0:
        result['programa'] = None
        result['tipo_participante'] = None
    else:
        # Múltiples programas: no hay un único programa/tipo
        result['programa'] = None
        result['tipo_participante'] = None
    
    return result


def list_participantes(limit: Optional[int] = None, offset: Optional[int] = None) -> List[Dict[str, Any]]:
    """Lista todos los participantes con paginación opcional, incluyendo TODOS sus programas y roles."""
    # Primero obtener todos los participantes
    query_participantes = """
        SELECT ci, nombre, apellido, email
        FROM participante
    """
    params = []
    
    if limit is not None:
        query_participantes += " LIMIT %s"
        params.append(limit)
        if offset is not None:
            query_participantes += " OFFSET %s"
            params.append(offset)
    
    rows = execute_query(query_participantes, tuple(params) if params else None, role='readonly')
    
    if not rows:
        return []
    
    # Obtener todos los programas de una vez
    cis = [row['ci'] for row in rows]
    placeholders = ','.join(['%s'] * len(cis))
    query_programas = f"""
        SELECT ci_participante, nombre_programa, rol
        FROM participante_programa_academico
        WHERE ci_participante IN ({placeholders})
        ORDER BY ci_participante, nombre_programa, rol
    """
    programas_rows = execute_query(query_programas, tuple(cis), role='readonly')
    
    # Agrupar programas por CI
    programas_por_ci = {}
    for row in programas_rows:
        ci = row['ci_participante']
        if ci not in programas_por_ci:
            programas_por_ci[ci] = []
        
        rol_db = row.get('rol')
        if rol_db == 'alumno':
            rol_display = 'Estudiante'
        elif rol_db == 'postgrado':
            rol_display = 'Postgrado'
        elif rol_db == 'docente':
            rol_display = 'Docente'
        else:
            rol_display = rol_db
        
        programas_por_ci[ci].append({
            'programa': row.get('nombre_programa'),
            'tipo': rol_display
        })
    
    # Construir resultado final
    result = []
    for row in rows:
        item = row.copy()
        ci = item['ci']
        programas = programas_por_ci.get(ci, [])
        item['programas'] = programas
        
        # Retrocompatibilidad: si solo tiene un programa, incluir campos legacy
        if len(programas) == 1:
            item['programa'] = programas[0]['programa']
            item['tipo_participante'] = programas[0]['tipo']
        else:
            item['programa'] = None
            item['tipo_participante'] = None
        
        result.append(item)
    
    return result


def update_participante(ci: int, nombre: Optional[str] = None, 
                       apellido: Optional[str] = None, 
                       email: Optional[str] = None,
                       tipo_participante: Optional[str] = None,
                       programa_academico: Optional[str] = None) -> int:
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
        participant_updates = 0
    else:
        participant_updates = None
    
    params.append(ci)
    query = f"UPDATE participante SET {', '.join(sets)} WHERE ci=%s" if sets else None

    total_affected = 0
    try:
        if query:
            total_affected += execute_non_query(query, tuple(params), role='user')

        program_ops = 0
        if tipo_participante is not None or programa_academico is not None:
            role_db = None
            if tipo_participante is not None:
                t = tipo_participante.lower()
                if t in ('estudiante', 'alumno'):
                    role_db = 'alumno'
                elif t == 'postgrado':
                    role_db = 'postgrado'
                elif t in ('docente', 'profesor'):
                    role_db = 'docente'
                elif t == 'otro':
                    role_db = 'otro'
                else:
                    raise ValueError("tipo_participante inválido: debe ser 'alumno', 'postgrado' o 'docente' (ej. 'Estudiante'/'Postgrado'/'Docente').")

            # Check existing association
            existing = execute_query(
                "SELECT nombre_programa, rol FROM participante_programa_academico WHERE ci_participante = %s",
                (ci,),
                role='readonly'
            )

            if existing:
                existing_row = existing[0]
                new_program = programa_academico if programa_academico is not None else existing_row.get('nombre_programa')
                new_role = role_db if role_db is not None else existing_row.get('rol')

                if new_program is None:
                    raise ValueError("programa_academico no encontrado y no se proveyó uno nuevo")

                exists_program = execute_query(
                    "SELECT 1 FROM programa_academico WHERE nombre_programa = %s LIMIT 1",
                    (new_program,),
                    role='readonly'
                )
                if not exists_program:
                    raise ValueError(f"Programa académico no encontrado: {new_program}")

                query_up = "UPDATE participante_programa_academico SET nombre_programa = %s, rol = %s WHERE ci_participante = %s"
                program_ops = execute_non_query(query_up, (new_program, new_role, ci), role='user')
            else:
                if not programa_academico or not role_db:
                    raise ValueError("Para asociar un programa se requieren 'programa_academico' y 'tipo_participante'.")
                program_ops = add_program_to_participante(ci, programa_academico, role_db)

            total_affected += program_ops

        return total_affected
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
                elif row['rol'] == 'postgrado':
                    participante['tipo_participante'] = 'Postgrado'
                elif row['rol'] == 'docente':
                    participante['tipo_participante'] = 'Docente'
            
            participante['programas'].append({
                'id_alumno_programa': row['id_alumno_programa'],
                'nombre_programa': row['nombre_programa'],
                'rol': 'Estudiante' if row['rol'] == 'alumno' else 'Postgrado' if row['rol'] == 'postgrado' else 'Docente' if row['rol'] == 'docente' else row['rol']
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
    """Asocia un participante a un programa académico con un rol ('alumno'|'docente'|'postgrado').

    Reglas:
    - Valida que el programa existe en `programa_academico`.
    - Valida que `rol` sea 'alumno', 'docente' o 'postgrado'.
    - La nueva PK es (ci_participante, nombre_programa, rol), permitiendo múltiples combinaciones.
    - Si la combinación ya existe, NO hace nada (INSERT IGNORE).
    """
    if not nombre_programa or not nombre_programa.strip():
        raise ValueError("nombre_programa es requerido para asociar un programa")

    rol_norm = rol.lower() if rol else ''
    if rol_norm not in ('alumno', 'docente', 'postgrado'):
        raise ValueError("rol inválido: debe ser 'alumno', 'postgrado' o 'docente'")

    # Comprobar que el programa existe
    exists = execute_query(
        "SELECT 1 FROM programa_academico WHERE nombre_programa = %s LIMIT 1",
        (nombre_programa,),
        role='readonly'
    )
    if not exists:
        raise ValueError(f"Programa académico no encontrado: {nombre_programa}")

    # Insertar la asociación. Si ya existe la combinación (ci, programa, rol), no hace nada.
    query = (
        "INSERT IGNORE INTO participante_programa_academico (ci_participante, nombre_programa, rol) "
        "VALUES (%s, %s, %s)"
    )
    return execute_non_query(query, (ci, nombre_programa, rol_norm), role='user')
