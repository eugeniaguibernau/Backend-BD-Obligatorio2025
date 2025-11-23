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

    conexion = get_connection(role='readonly')
    cursor = conexion.cursor()

    cursor.execute("SELECT capacidad, tipo_sala FROM sala WHERE nombre_sala=%s AND edificio=%s", (nombre_sala, edificio))
    sala = cursor.fetchone()
    if not sala:
        return False, "La sala no existe."

    if len(participantes) > sala['capacidad']:
        return False, f"La sala solo permite {sala['capacidad']} participantes."

    tipo_sala = sala['tipo_sala']
    # Normalizar tipo_sala por seguridad
    try:
        tipo_sala = (tipo_sala or '').strip().lower()
        nombre_sala = datos['nombre_sala']
        edificio = datos['edificio']
        participantes = datos['participantes']

        # Support multiple requested reservations/dates in the same request.
        # Priority:
        # - if 'reservas' in datos: expect list of {fecha: 'YYYY-MM-DD', id_turno: X}
        # - elif 'fechas' in datos: list of date strings
        # - else: use single 'fecha' field
        requested_dates = []
        if isinstance(datos.get('reservas'), list) and len(datos.get('reservas')) > 0:
            for r in datos.get('reservas'):
                f = r.get('fecha') if isinstance(r, dict) else None
                if f:
                    requested_dates.append(str(f))
        elif isinstance(datos.get('fechas'), list) and len(datos.get('fechas')) > 0:
            for f in datos.get('fechas'):
                requested_dates.append(str(f))
        else:
            # fallback to single fecha
            if 'fecha' in datos:
                requested_dates.append(str(datos.get('fecha')))

        # normalize requested_dates to YYYY-MM-DD strings and remove empties
        parsed_dates = []
        for d in requested_dates:
            try:
                dt = datetime.strptime(d, '%Y-%m-%d').date()
                parsed_dates.append(dt.strftime('%Y-%m-%d'))
            except Exception:
                # ignore invalid dates - validation of date format should be handled earlier
                pass

        # open readonly connection
        conexion = get_connection(role='readonly')
        cursor = conexion.cursor()

        # Validate sala exists and capacity
        cursor.execute("SELECT capacidad, tipo_sala FROM sala WHERE nombre_sala=%s AND edificio=%s", (nombre_sala, edificio))
        sala = cursor.fetchone()
        if not sala:
            cursor.close(); conexion.close()
            return False, "La sala no existe."

        if len(participantes) > sala.get('capacidad', 0):
            cursor.close(); conexion.close()
            return False, f"La sala solo permite {sala.get('capacidad')} participantes."

        tipo_sala = (sala.get('tipo_sala') or '').strip().lower()

        # Check turno existence if a single id_turno provided (retrocompat)
        if 'id_turno' in datos:
            try:
                cursor.execute("SELECT 1 FROM turno WHERE id_turno = %s LIMIT 1", (datos.get('id_turno'),))
                if not cursor.fetchone():
                    cursor.close(); conexion.close()
                    return False, "Turno inválido."
            except Exception:
                # ignore and proceed; deeper validation elsewhere
                pass

        # Sanctions check
        for ci in participantes:
            cursor.execute("""
                SELECT COUNT(*) AS cantidad
                FROM sancion_participante
                WHERE ci_participante = %s
                  AND fecha_inicio <= CURDATE()
                  AND fecha_fin >= CURDATE()
            """, (ci,))
            sanciones = cursor.fetchone()['cantidad']
            if sanciones and sanciones > 0:
                cursor.close(); conexion.close()
                return False, f"El participante {ci} tiene sanciones vigentes y no puede reservar."

        # Gather roles per participant
        roles_por_ci = {}
        for ci in participantes:
            cursor.execute("""
                SELECT pa.tipo as tipo_programa, ppa.rol as rol
                FROM participante_programa_academico ppa
                JOIN programa_academico pa ON ppa.nombre_programa = pa.nombre_programa
                WHERE ci_participante = %s
            """, (ci,))
            filas = cursor.fetchall()
            if not filas:
                cursor.close(); conexion.close()
                return False, f"El participante {ci} no tiene programa académico asignado."

            roles = set()
            tipos_prog = set()
            for f in filas:
                try:
                    roles.add((f.get('rol') or '').strip().lower())
                except Exception:
                    pass
                try:
                    tipos_prog.add((f.get('tipo_programa') or '').strip().lower())
                except Exception:
                    pass

            effective_role = 'alumno'
            if 'docente' in roles:
                effective_role = 'docente'
            elif 'postgrado' in roles or 'posgrado' in roles:
                effective_role = 'postgrado'
            elif 'alumno' in roles:
                effective_role = 'alumno'
            else:
                if 'postgrado' in tipos_prog or 'posgrado' in tipos_prog:
                    effective_role = 'postgrado'

            roles_por_ci[ci] = effective_role

            # exclusivity checks
            if tipo_sala == 'docente' and effective_role != 'docente':
                cursor.close(); conexion.close()
                return False, f"La sala {nombre_sala} es exclusiva de docentes."
            if tipo_sala == 'posgrado' and effective_role != 'postgrado':
                cursor.close(); conexion.close()
                return False, f"La sala {nombre_sala} es exclusiva de posgrado."

        # Build requested counts per week and per date
        # week key: YYYY-MM-DD (start of week Monday)
        from collections import defaultdict

        def week_start_for_date(dt_date):
            d = datetime.strptime(dt_date, '%Y-%m-%d').date()
            start = d - timedelta(days=d.weekday())
            return start.strftime('%Y-%m-%d')

        # requested per-week and per-date (same for all participants in this request)
        requested_per_week = defaultdict(int)
        requested_per_date = defaultdict(int)
        for d in parsed_dates:
            wk = week_start_for_date(d)
            requested_per_week[wk] += 1
            requested_per_date[d] += 1

        # For each participant, apply daily and weekly checks (unless exempt)
        for ci in participantes:
            eff = roles_por_ci.get(ci)
            is_exempt = (eff == 'docente' and tipo_sala == 'docente') or (eff == 'postgrado' and tipo_sala == 'posgrado')
            if is_exempt:
                continue

            # Daily (2 hours) check: for each date in requested_per_date, count existing hours + requested on that date
            for date_str, req_cnt_on_date in requested_per_date.items():
                # Contar sólo horas en salas libres (excluir 'docente' y 'posgrado/postgrado')
                cursor.execute("""
                    SELECT COALESCE(SUM(TIMESTAMPDIFF(HOUR, t.hora_inicio, t.hora_fin)),0) AS horas_reservadas
                    FROM reserva_participante rp
                    JOIN reserva r ON rp.id_reserva = r.id_reserva
                    JOIN turno t ON r.id_turno = t.id_turno
                    JOIN sala s ON r.nombre_sala = s.nombre_sala AND r.edificio = s.edificio
                    WHERE rp.ci_participante = %s
                      AND r.fecha = %s
                      AND r.estado = 'activa'
                      AND TRIM(LOWER(COALESCE(s.tipo_sala, ''))) NOT IN ('docente','posgrado','postgrado')
                """, (ci, date_str))
                horas_reservadas = cursor.fetchone()['horas_reservadas'] or 0
                # requested hours on that date = req_cnt_on_date * 1 (each turno 1h)
                if (horas_reservadas + req_cnt_on_date) > 2:
                    cursor.close(); conexion.close()
                    return False, f"El participante {ci} excede el límite diario en {date_str} ({horas_reservadas} existentes + {req_cnt_on_date} solicitadas). Máximo permitido: 2 horas."

            for wk_start, req_cnt in requested_per_week.items():
                wk_start_date = datetime.strptime(wk_start, '%Y-%m-%d').date()
                wk_end_date = wk_start_date + timedelta(days=6)

                # Contar sólo reservas en salas libres: excluir salas con tipo 'docente' o 'posgrado/postgrado'
                cursor.execute("""
                    SELECT COUNT(DISTINCT r.id_reserva) AS cantidad
                    FROM reserva_participante rp
                    JOIN reserva r ON rp.id_reserva = r.id_reserva
                    JOIN sala s ON r.nombre_sala = s.nombre_sala AND r.edificio = s.edificio
                    WHERE rp.ci_participante = %s
                      AND r.fecha BETWEEN %s AND %s
                      AND r.estado = 'activa'
                      AND TRIM(LOWER(COALESCE(s.tipo_sala, ''))) NOT IN ('docente','posgrado','postgrado')
                """, (ci, wk_start_date, wk_end_date))
                existentes = cursor.fetchone()['cantidad'] or 0

                total = existentes + req_cnt
                if total > 3:
                    cursor.close(); conexion.close()
                    return False, f"El participante {ci} excede el límite semanal en la semana {wk_start} ({existentes} existentes + {req_cnt} solicitadas = {total}). Máximo permitido: 3."

        cursor.close()
        conexion.close()
        return True, "OK"
    except Exception:
        # Catch-all para asegurar que el try exterior no deje la función sin un bloque except/finally.
        try:
            cursor.close()
            conexion.close()
        except Exception:
            pass
        return False, "Error interno en validar_reglas_negocio"

def crear_reserva(nombre_sala, edificio, fecha, id_turno, participantes):
    conexion = get_connection(role='user')
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


def crear_reservas_batch(nombre_sala, edificio, fecha, turnos, participantes):
    """Crear varias reservas (una por cada id_turno) en una sola transacción.

    Valida atómicamente el límite semanal por participante contando turnos existentes
    en la semana y sumando los turnos solicitados en este batch.
    """
    if not isinstance(turnos, list) or len(turnos) == 0:
        raise ValueError("turnos debe ser una lista no vacía")

    conn = get_connection(role='user')
    cur = conn.cursor()

    # Obtener tipo de sala y capacidad
    cur.execute("SELECT capacidad, tipo_sala FROM sala WHERE nombre_sala=%s AND edificio=%s", (nombre_sala, edificio))
    sala = cur.fetchone()
    if not sala:
        conn.close()
        raise ValueError("La sala no existe.")
    tipo_sala = (sala.get('tipo_sala') or '').strip().lower()
    if len(participantes) > sala.get('capacidad', 0):
        conn.close()
        raise ValueError(f"La sala solo permite {sala.get('capacidad')} participantes.")

    # Calcular semana de la fecha
    fecha_base = datetime.strptime(fecha, '%Y-%m-%d').date()
    inicio_semana = fecha_base - timedelta(days=fecha_base.weekday())
    fin_semana = inicio_semana + timedelta(days=6)

    # Recolectar roles y validar exclusividad inmediata
    roles_por_ci = {}
    for ci in participantes:
        cur.execute("""
            SELECT pa.tipo as tipo_programa, ppa.rol as rol
            FROM participante_programa_academico ppa
            JOIN programa_academico pa ON ppa.nombre_programa = pa.nombre_programa
            WHERE ci_participante = %s
        """, (ci,))
        filas = cur.fetchall()
        if not filas:
            conn.close()
            raise ValueError(f"El participante {ci} no tiene programa académico asignado.")

        roles = set()
        tipos_prog = set()
        for f in filas:
            try:
                roles.add((f.get('rol') or '').strip().lower())
            except Exception:
                pass
            try:
                tipos_prog.add((f.get('tipo_programa') or '').strip().lower())
            except Exception:
                pass

        effective_role = 'alumno'
        if 'docente' in roles:
            effective_role = 'docente'
        elif 'postgrado' in roles or 'posgrado' in roles:
            effective_role = 'postgrado'
        elif 'alumno' in roles:
            effective_role = 'alumno'
        else:
            if 'postgrado' in tipos_prog or 'posgrado' in tipos_prog:
                effective_role = 'postgrado'

        roles_por_ci[ci] = effective_role

        # Exclusividad de sala
        if tipo_sala == 'docente' and effective_role != 'docente':
            conn.close()
            raise ValueError(f"La sala {nombre_sala} es exclusiva de docentes.")
        if tipo_sala == 'posgrado' and effective_role != 'postgrado':
            conn.close()
            raise ValueError(f"La sala {nombre_sala} es exclusiva de posgrado.")

    # Validar límite semanal por participante (turnos existentes + turnos solicitados en este batch)
    turnos_solicitados = len(turnos)
    for ci in participantes:
        eff = roles_por_ci.get(ci)
        is_exempt = (eff == 'docente' and tipo_sala == 'docente') or (eff == 'postgrado' and tipo_sala == 'posgrado')
        if is_exempt:
            continue
        try:
            cur.execute("""
                SELECT COALESCE(SUM(TIMESTAMPDIFF(HOUR, t.hora_inicio, t.hora_fin)),0) AS horas_reservadas
                FROM reserva_participante rp
                JOIN reserva r ON rp.id_reserva = r.id_reserva
                JOIN turno t ON r.id_turno = t.id_turno
                JOIN sala s ON r.nombre_sala = s.nombre_sala AND r.edificio = s.edificio
                WHERE rp.ci_participante = %s
                  AND r.fecha = %s
                  AND r.estado = 'activa'
                  AND TRIM(LOWER(COALESCE(s.tipo_sala, ''))) NOT IN ('docente','posgrado','postgrado')
            """, (ci, fecha))
            horas_existentes = cur.fetchone().get('horas_reservadas') or 0
        except Exception:
            horas_existentes = 0
        if (horas_existentes + turnos_solicitados) > 2:
            conn.close()
            raise ValueError(f"El participante {ci} excede el límite diario en {fecha} ({horas_existentes} existentes + {turnos_solicitados} solicitadas). Máximo permitido: 2 horas.")

        cur.execute("""
            SELECT COUNT(DISTINCT r.id_reserva) AS cantidad
            FROM reserva_participante rp
            JOIN reserva r ON rp.id_reserva = r.id_reserva
            WHERE rp.ci_participante = %s
            AND r.fecha BETWEEN %s AND %s
            AND r.estado = 'activa'
        """, (ci, inicio_semana, fin_semana))
        # Contar sólo reservas en salas libres (excluir 'docente' y 'posgrado/postgrado')
        cur.execute("""
            SELECT COUNT(DISTINCT r.id_reserva) AS cantidad
            FROM reserva_participante rp
            JOIN reserva r ON rp.id_reserva = r.id_reserva
            JOIN sala s ON r.nombre_sala = s.nombre_sala AND r.edificio = s.edificio
            WHERE rp.ci_participante = %s
            AND r.fecha BETWEEN %s AND %s
            AND r.estado = 'activa'
            AND TRIM(LOWER(COALESCE(s.tipo_sala, ''))) NOT IN ('docente','posgrado','postgrado')
        """, (ci, inicio_semana, fin_semana))
        existentes = cur.fetchone()['cantidad']
        try:
            print(f"[BATCH_SEMANA] ci={ci} existentes={existentes} inicio={inicio_semana} fin={fin_semana} turnos_solicitados={turnos_solicitados}")
        except Exception:
            pass
        total = (existentes or 0) + turnos_solicitados
        try:
            print(f"[BATCH_SEMANA_TOTAL] ci={ci} existentes={existentes} total={total}")
        except Exception:
            pass
        if total > 3:
            conn.close()
            raise ValueError(f"El participante {ci} ya tiene reservas activas esta semana (máximo 3).")

    # Si pasaron las validaciones, crear todas las reservas e insertar participantes
    creadas = []
    try:
        for id_turno in turnos:
            cur.execute("""
                INSERT INTO reserva (nombre_sala, edificio, fecha, id_turno, estado)
                VALUES (%s, %s, %s, %s, 'activa')
            """, (nombre_sala, edificio, fecha, id_turno))
            id_res = cur.lastrowid
            for ci in participantes:
                cur.execute("""
                    INSERT INTO reserva_participante (ci_participante, id_reserva, fecha_solicitud_reserva, asistencia)
                    VALUES (%s, %s, NOW(), NULL)
                """, (ci, id_res))
            creadas.append({'id_reserva': id_res, 'id_turno': id_turno})
        conn.commit()
    except Exception:
        conn.rollback()
        conn.close()
        raise

    conn.close()
    return creadas


def listar_reservas(ci_participante=None, nombre_sala=None):
    conexion = get_connection(role='readonly')
    cursor = conexion.cursor()
    
    # Consulta base con JOIN a turno para obtener horarios
    consulta = """
        SELECT 
            r.id_reserva,
            r.nombre_sala,
            r.edificio,
            r.fecha,
            r.estado,
            t.hora_inicio,
            t.hora_fin
        FROM reserva r
        LEFT JOIN turno t ON r.id_turno = t.id_turno
    """
    
    parametros = []
    filtros = []

    if ci_participante:
        filtros.append("r.id_reserva IN (SELECT id_reserva FROM reserva_participante WHERE ci_participante = %s)")
        parametros.append(ci_participante)
    if nombre_sala:
        filtros.append("r.nombre_sala = %s")
        parametros.append(nombre_sala)
    if filtros:
        consulta += " WHERE " + " AND ".join(filtros)
    
    consulta += " ORDER BY r.fecha DESC, t.hora_inicio ASC"

    cursor.execute(consulta, parametros)
    filas = cursor.fetchall()
    cursor.close()
    conexion.close()
    
    # Agrupar por id_reserva para combinar múltiples turnos
    reservas_dict = {}
    for fila in filas:
        id_reserva = fila['id_reserva']
        if id_reserva not in reservas_dict:
            # Crear objeto turno singular con el primer turno encontrado
            turno = None
            if fila['hora_inicio'] and fila['hora_fin']:
                turno = {
                    'hora_inicio': str(fila['hora_inicio']).split(' ')[-1] if fila['hora_inicio'] else None,
                    'hora_fin': str(fila['hora_fin']).split(' ')[-1] if fila['hora_fin'] else None
                }
            
            reservas_dict[id_reserva] = {
                'id_reserva': id_reserva,
                'nombre_sala': fila['nombre_sala'],
                'edificio': fila['edificio'],
                'fecha': fila['fecha'].strftime('%Y-%m-%d') if fila['fecha'] else None,
                'estado': fila['estado'],
                'turno': turno  # Objeto singular en lugar de array
            }
    
    return list(reservas_dict.values())


def obtener_reserva(id_reserva):
    conexion = get_connection(role='readonly')
    cursor = conexion.cursor()
    
    # Obtener datos de la reserva con información del turno
    cursor.execute("""
        SELECT 
            r.id_reserva,
            r.nombre_sala,
            r.edificio,
            r.fecha,
            r.estado,
            t.hora_inicio,
            t.hora_fin
        FROM reserva r
        LEFT JOIN turno t ON r.id_turno = t.id_turno
        WHERE r.id_reserva = %s
    """, (id_reserva,))
    fila = cursor.fetchone()
    cursor.close()
    conexion.close()
    
    if not fila:
        return None
    
    # Crear objeto turno singular
    turno = None
    if fila['hora_inicio'] and fila['hora_fin']:
        turno = {
            'hora_inicio': str(fila['hora_inicio']).split(' ')[-1] if fila['hora_inicio'] else None,
            'hora_fin': str(fila['hora_fin']).split(' ')[-1] if fila['hora_fin'] else None
        }
    
    # Formatear la respuesta con turno singular
    reserva = {
        'id_reserva': fila['id_reserva'],
        'nombre_sala': fila['nombre_sala'],
        'edificio': fila['edificio'],
        'fecha': fila['fecha'].strftime('%Y-%m-%d') if fila['fecha'] else None,
        'estado': fila['estado'],
        'turno': turno  # Objeto singular en lugar de array
    }
    
    return reserva



def actualizar_reserva(id_reserva, datos):
    CANCEL_DIAS = 2
    SANCION_DIAS = 60

    conexion = get_connection(role='user')
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
    conexion = get_connection(role='admin')
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
    conexion = get_connection(role='user')
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
