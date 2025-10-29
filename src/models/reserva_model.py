from datetime import datetime, timedelta
from src.config.database import get_connection


def validar_reglas_negocio(datos):
    """
    Verifica las reglas de negocio antes de crear una reserva.
    """
    nombre_sala = datos['nombre_sala']
    edificio = datos['edificio']
    participantes = datos['participantes'] 
    fecha = datos['fecha']
    id_turno = datos['id_turno']

    conexion = get_connection()
    cursor = conexion.cursor()

    cursor.execute("SELECT capacidad, tipo_sala FROM sala WHERE nombre_sala=%s AND edificio=%s", (nombre_sala, edificio))
    sala = cursor.fetchone()
    if not sala:
        return False, "La sala no existe."

    if len(participantes) > sala['capacidad']:
        return False, f"La sala solo permite {sala['capacidad']} participantes."

    tipo_sala = sala['tipo_sala']

    # Verificar disponibilidad de sala/turno (no debe haber otra reserva activa)
    cursor.execute("""
        SELECT COUNT(*) AS cantidad
        FROM reserva
        WHERE nombre_sala=%s AND edificio=%s AND fecha=%s AND id_turno=%s AND estado = 'activa'
    """, (nombre_sala, edificio, fecha, id_turno))
    conflicto = cursor.fetchone()['cantidad']
    if conflicto and conflicto > 0:
        return False, "La sala/turno ya está reservada en ese horario."

    # Verificar sanciones vigentes por participante
    for ci in participantes:
        cursor.execute("""
            SELECT COUNT(*) AS cantidad
            FROM sancion_participante
            WHERE ci_participante = %s AND fecha_fin >= CURDATE()
        """, (ci,))
        sanciones = cursor.fetchone()['cantidad']
        if sanciones and sanciones > 0:
            return False, f"El participante {ci} tiene sanciones vigentes y no puede reservar."

    for ci in participantes:
        cursor.execute("""
            SELECT pa.tipo, ppa.rol
            FROM participante_programa_academico ppa
            JOIN programa_academico pa ON ppa.nombre_programa = pa.nombre_programa
            WHERE ci_participante = %s
        """, (ci,))
        programa = cursor.fetchone()
        if not programa:
            return False, f"El participante {ci} no tiene programa académico asignado."

        if tipo_sala == 'docente' and programa['rol'] != 'docente':
            return False, f"La sala {nombre_sala} es exclusiva de docentes."
        if tipo_sala == 'posgrado' and programa['tipo'] != 'posgrado':
            return False, f"La sala {nombre_sala} es exclusiva de posgrado."

    if tipo_sala == 'libre':
        for ci in participantes:
            cursor.execute("""
                SELECT COUNT(*) AS cantidad
                FROM reserva_participante rp
                JOIN reserva r ON rp.id_reserva = r.id_reserva
                WHERE rp.ci_participante = %s AND r.fecha = %s AND r.estado = 'activa'
            """, (ci, fecha))
            horas = cursor.fetchone()['cantidad']
            if horas >= 2:
                return False, f"El participante {ci} ya tiene 2 horas reservadas ese día."

            fecha_base = datetime.strptime(fecha, '%Y-%m-%d').date()
            inicio_semana = fecha_base - timedelta(days=fecha_base.weekday())
            fin_semana = inicio_semana + timedelta(days=6)
            cursor.execute("""
                SELECT COUNT(*) AS cantidad
                FROM reserva_participante rp
                JOIN reserva r ON rp.id_reserva = r.id_reserva
                WHERE rp.ci_participante = %s
                AND r.fecha BETWEEN %s AND %s
                AND r.estado = 'activa'
            """, (ci, inicio_semana, fin_semana))
            activas = cursor.fetchone()['cantidad']
            if activas >= 3:
                return False, f"El participante {ci} ya tiene 3 reservas activas esta semana."

    cursor.close()
    conexion.close()
    return True, "OK"

def crear_reserva(nombre_sala, edificio, fecha, id_turno, participantes):
    conexion = get_connection()
    cursor = conexion.cursor()
    cursor.execute("""
        INSERT INTO reserva (nombre_sala, edificio, fecha, id_turno, estado)
        VALUES (%s, %s, %s, %s, 'activa')
    """, (nombre_sala, edificio, fecha, id_turno))
    id_reserva = cursor.lastrowid

    for ci in participantes:
        cursor.execute("""
            INSERT INTO reserva_participante (ci_participante, id_reserva, fecha_solicitud_reserva, asistencia)
            VALUES (%s, %s, NOW(), NULL)
        """, (ci, id_reserva))

    conexion.commit()
    cursor.close()
    conexion.close()
    return id_reserva


def listar_reservas(ci_participante=None, nombre_sala=None):
    conexion = get_connection()
    cursor = conexion.cursor()
    consulta = "SELECT * FROM reserva"
    parametros = []
    filtros = []

    if ci_participante:
        filtros.append("id_reserva IN (SELECT id_reserva FROM reserva_participante WHERE ci_participante = %s)")
        parametros.append(ci_participante)
    if nombre_sala:
        filtros.append("nombre_sala = %s")
        parametros.append(nombre_sala)
    if filtros:
        consulta += " WHERE " + " AND ".join(filtros)

    cursor.execute(consulta, parametros)
    filas = cursor.fetchall()
    cursor.close()
    conexion.close()
    return filas


def obtener_reserva(id_reserva):
    conexion = get_connection()
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM reserva WHERE id_reserva = %s", (id_reserva,))
    fila = cursor.fetchone()
    cursor.close()
    conexion.close()
    return fila


def actualizar_reserva(id_reserva, datos):
    CANCEL_DIAS = 2
    SANCION_DIAS = 7

    conexion = get_connection()
    cursor = conexion.cursor()

    # Obtener reserva actual
    cursor.execute("SELECT * FROM reserva WHERE id_reserva = %s", (id_reserva,))
    reserva_actual = cursor.fetchone()
    if not reserva_actual:
        cursor.close()
        conexion.close()
        raise ValueError("Reserva no encontrada")

    # Si se solicita cancelar, verificar ventana mínima
    if 'estado' in datos and datos.get('estado') == 'cancelada':
        fecha_reserva = reserva_actual['fecha']
        if isinstance(fecha_reserva, str):
            fecha_reserva = datetime.strptime(fecha_reserva, '%Y-%m-%d').date()
        dias_anticipacion = (fecha_reserva - datetime.now().date()).days
        if dias_anticipacion < CANCEL_DIAS:
            cursor.close()
            conexion.close()
            raise ValueError(f"No se puede cancelar con menos de {CANCEL_DIAS} días de anticipación")

    # Construir y ejecutar UPDATE
    campos = []
    valores = []
    for clave, valor in datos.items():
        campos.append(f"{clave}=%s")
        valores.append(valor)
    valores.append(id_reserva)
    sql = f"UPDATE reserva SET {', '.join(campos)} WHERE id_reserva=%s"
    cursor.execute(sql, valores)
    conexion.commit()
    filas_afectadas = cursor.rowcount

    # Si se marcó como 'sin asistencia', crear sanciones automáticas para participantes sin asistencia
    if 'estado' in datos and datos.get('estado') == 'sin asistencia':
        # obtener participantes de la reserva con asistencia = FALSE or NULL
        cursor.execute("""
            SELECT rp.ci_participante, rp.asistencia
            FROM reserva_participante rp
            WHERE rp.id_reserva = %s
        """, (id_reserva,))
        rows = cursor.fetchall()
        fecha_reserva = reserva_actual['fecha']
        if isinstance(fecha_reserva, str):
            fecha_reserva = datetime.strptime(fecha_reserva, '%Y-%m-%d').date()
        fecha_fin = fecha_reserva + timedelta(days=SANCION_DIAS)
        for row in rows:
            asistencia = row.get('asistencia')
            ci = row.get('ci_participante')
            if asistencia is None or asistencia is False:
                # insertar sancion si no existe
                cursor.execute("""
                    INSERT IGNORE INTO sancion_participante (ci_participante, fecha_inicio, fecha_fin)
                    VALUES (%s, %s, %s)
                """, (ci, fecha_reserva, fecha_fin))
        conexion.commit()

    cursor.close()
    conexion.close()
    return filas_afectadas


def eliminar_reserva(id_reserva):
    conexion = get_connection()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM reserva_participante WHERE id_reserva=%s", (id_reserva,))
    cursor.execute("DELETE FROM reserva WHERE id_reserva=%s", (id_reserva,))
    conexion.commit()
    filas_afectadas = cursor.rowcount
    cursor.close()
    conexion.close()
    return filas_afectadas


def marcar_asistencia(id_reserva, ci_participante, asistencia: bool):
    """Marcar asistencia (True/False) para un participante en una reserva."""
    conexion = get_connection()
    cursor = conexion.cursor()
    cursor.execute(
        "UPDATE reserva_participante SET asistencia=%s WHERE id_reserva=%s AND ci_participante=%s",
        (1 if asistencia else 0, id_reserva, ci_participante)
    )
    conexion.commit()
    filas_afectadas = cursor.rowcount
    cursor.close()
    conexion.close()
    return filas_afectadas
