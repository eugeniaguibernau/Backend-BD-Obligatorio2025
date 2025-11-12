# src/models/sancion_model.py
from datetime import datetime, timedelta
from src.config.database import get_connection

def _to_date(val):
    if isinstance(val, str):
        return datetime.strptime(val, "%Y-%m-%d").date()
    return val

def crear_sancion(ci_participante: int, fecha_inicio, fecha_fin):
    """
    Crea una sanción. Usa INSERT IGNORE para no duplicar si existe una restricción única.
    Retorna filas afectadas (0 si ya existía, 1 si se insertó).
    """
    fecha_inicio = _to_date(fecha_inicio)
    fecha_fin = _to_date(fecha_fin)

    conexion = get_connection(role='user')
    cursor = conexion.cursor()
    cursor.execute("""
        INSERT IGNORE INTO sancion_participante (ci_participante, fecha_inicio, fecha_fin)
        VALUES (%s, %s, %s)
    """, (ci_participante, fecha_inicio, fecha_fin))
    conexion.commit()
    filas = cursor.rowcount
    cursor.close()
    conexion.close()
    return filas

def listar_sanciones(ci_participante: int | None = None, solo_activas: bool = False):
    """
    Lista sanciones. Si solo_activas=True filtra por fecha_fin >= CURDATE().
    """
    conexion = get_connection(role='readonly')
    cursor = conexion.cursor()
    where = []
    params = []

    if ci_participante is not None:
        where.append("ci_participante = %s")
        params.append(ci_participante)
    if solo_activas:
        where.append("fecha_fin >= CURDATE()")

    # Devolvemos también campos calculados para que el frontend muestre valores consistentes:
    # - duracion_dias: número entero de días entre fecha_inicio y fecha_fin
    # - dias_restantes: número entero de días desde hoy hasta fecha_fin (puede ser negativo si ya venció)
    sql = (
        "SELECT ci_participante, fecha_inicio, fecha_fin, "
        "DATEDIFF(fecha_fin, fecha_inicio) AS duracion_dias, "
        "DATEDIFF(fecha_fin, CURDATE()) AS dias_restantes "
        "FROM sancion_participante"
    )
    if where:
        sql += " WHERE " + " AND ".join(where)

    cursor.execute(sql, params)
    filas = cursor.fetchall()
    cursor.close()
    conexion.close()
    return filas

def eliminar_sancion(ci_participante: int, fecha_inicio, fecha_fin):
    """
    Elimina una sanción identificada por su clave natural (ci + rango de fechas).
    Retorna filas afectadas.
    """
    fecha_inicio = _to_date(fecha_inicio)
    fecha_fin = _to_date(fecha_fin)

    conexion = get_connection(role='admin')
    cursor = conexion.cursor()
    cursor.execute("""
        DELETE FROM sancion_participante
        WHERE ci_participante = %s AND fecha_inicio = %s AND fecha_fin = %s
    """, (ci_participante, fecha_inicio, fecha_fin))
    conexion.commit()
    filas = cursor.rowcount
    cursor.close()
    conexion.close()
    return filas

def aplicar_sanciones_por_reserva(id_reserva: int, sancion_dias: int = 60):
    """
    Regla pedida: SOLO hay sanción si NADIE asistió a la reserva.
    - Si al menos un participante marcó asistencia=1, NO se sanciona a nadie.
    - Si nadie asistió, se sanciona a TODOS los inscriptos en la reserva.

    Retorna: dict con {'sancionados': [...], 'insertadas': N, 'fecha_inicio': date, 'fecha_fin': date}
    """
    conexion = get_connection(role='user')
    cursor = conexion.cursor()

    # 1) Obtener fecha de la reserva (para usar como inicio de sanción)
    cursor.execute("SELECT fecha FROM reserva WHERE id_reserva = %s", (id_reserva,))
    fila_reserva = cursor.fetchone()
    if not fila_reserva:
        cursor.close()
        conexion.close()
        raise ValueError("Reserva no encontrada")

    fecha_reserva = _to_date(fila_reserva["fecha"])
    fecha_fin = fecha_reserva + timedelta(days=sancion_dias)

    # 2) Ver cuántos asistieron
    cursor.execute("""
        SELECT COUNT(*) AS asistieron
        FROM reserva_participante
        WHERE id_reserva = %s AND asistencia = 1
    """, (id_reserva,))
    asistieron = cursor.fetchone()["asistieron"] or 0

    # 3) Si hubo al menos uno, no sancionar
    if asistieron > 0:
        cursor.close()
        conexion.close()
        return {
            "sancionados": [],
            "insertadas": 0,
            "fecha_inicio": fecha_reserva,
            "fecha_fin": fecha_fin,
            "motivo": "Hubo al menos un asistente. No corresponde sanción."
        }

    # 4) Nadie asistió -> sancionar a todos los participantes de la reserva
    cursor.execute("""
        SELECT ci_participante
        FROM reserva_participante
        WHERE id_reserva = %s
    """, (id_reserva,))
    participantes = [r["ci_participante"] for r in cursor.fetchall()]

    insertadas = 0
    for ci in participantes:
        cursor.execute("""
            INSERT IGNORE INTO sancion_participante (ci_participante, fecha_inicio, fecha_fin)
            VALUES (%s, %s, %s)
        """, (ci, fecha_reserva, fecha_fin))
        insertadas += cursor.rowcount

    conexion.commit()
    cursor.close()
    conexion.close()

    return {
        "sancionados": participantes,
        "insertadas": insertadas,
        "fecha_inicio": fecha_reserva,
        "fecha_fin": fecha_fin,
        "motivo": "Nadie asistió a la reserva."
    }


def procesar_reservas_vencidas(sancion_dias: int = 60):
    """
    Busca reservas con fecha anterior a la actual y estado 'activa'.
    Para cada reserva:
      - si hubo al menos 1 asistencia -> marca 'finalizada'
      - si nadie asistió -> crea sanciones para todos y marca 'sin asistencia'

    Retorna un resumen con listas de procesadas, finalizadas y sancionadas.
    """
    conexion = get_connection(role='user')
    cursor = conexion.cursor()

    # obtener reservas vencidas y aún activas
    cursor.execute("SELECT id_reserva, fecha FROM reserva WHERE fecha < CURDATE() AND estado = 'activa'")
    filas = cursor.fetchall()

    resumen = {
        'procesadas': 0,
        'finalizadas': [],
        'sancionadas': [],
        'insertadas_total': 0
    }

    for fila in filas:
        id_reserva = fila['id_reserva']
        fecha_reserva = _to_date(fila['fecha'])

        # contar asistentes
        cursor.execute("SELECT COUNT(*) AS asistieron FROM reserva_participante WHERE id_reserva = %s AND asistencia = 1", (id_reserva,))
        asistieron = cursor.fetchone().get('asistieron', 0) or 0

        if asistieron > 0:
            # marcar como finalizada
            cursor.execute("UPDATE reserva SET estado = 'finalizada' WHERE id_reserva = %s", (id_reserva,))
            resumen['finalizadas'].append(id_reserva)
        else:
            # aplicar sanciones (usa la función existente que inserta sanciones)
            resultado = aplicar_sanciones_por_reserva(id_reserva, sancion_dias=sancion_dias)
            # marcar como sin asistencia
            cursor.execute("UPDATE reserva SET estado = 'sin asistencia' WHERE id_reserva = %s", (id_reserva,))
            resumen['sancionadas'].append({'id_reserva': id_reserva, 'detalle': resultado})
            resumen['insertadas_total'] += resultado.get('insertadas', 0)

        resumen['procesadas'] += 1

    conexion.commit()
    cursor.close()
    conexion.close()
    return resumen


def extender_sanciones_existentes(min_dias: int = 60):
    """
    Actualiza sanciones existentes cuya duración sea menor a `min_dias`.

    - Calcula fecha_fin deseada = fecha_inicio + min_dias
    - Actualiza solo las filas donde fecha_fin < fecha_inicio + min_dias
    Retorna dict con filas_actualizadas.
    """
    conexion = get_connection(role='admin')
    cursor = conexion.cursor()

    # MySQL: actualizar aquellas sanciones cuya fecha_fin sea anterior a fecha_inicio + INTERVAL min_dias DAY
    cursor.execute(f"""
        UPDATE sancion_participante
        SET fecha_fin = DATE_ADD(fecha_inicio, INTERVAL %s DAY)
        WHERE fecha_fin < DATE_ADD(fecha_inicio, INTERVAL %s DAY)
    """, (min_dias, min_dias))

    filas_actualizadas = cursor.rowcount
    conexion.commit()
    cursor.close()
    conexion.close()

    return {"filas_actualizadas": filas_actualizadas, "min_dias": min_dias}
