#!/usr/bin/env python3
"""
Script para procesar sanciones automáticas diariamente.
Se ejecuta vía cronjob y busca reservas del día anterior sin asistencia.
"""
import sys
import os
from datetime import date, timedelta

# Agregar el directorio raíz al path para importar módulos
sys.path.insert(0, '/app')

from src.models.sancion_model import aplicar_sanciones_por_reserva
from src.config.database import get_connection


def procesar_sanciones_diarias():
    """
    Busca todas las reservas del día anterior que están activas
    y aplica sanciones si corresponde (nadie asistió).
    """
    ayer = date.today() - timedelta(days=1)
    
    print(f"[{date.today()}] Iniciando procesamiento de sanciones para reservas del {ayer}")
    
    try:
        # Obtener reservas activas del día anterior
        conn = get_connection('readonly')
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id_reserva, nombre_sala, edificio, fecha
            FROM reserva
            WHERE fecha = %s 
            AND estado = 'activa'
        """, (ayer,))
        
        reservas = cur.fetchall()
        cur.close()
        conn.close()
        
        if not reservas:
            print(f"No hay reservas activas del día {ayer}")
            return
        
        print(f"Encontradas {len(reservas)} reservas activas del día {ayer}")
        
        # Procesar cada reserva
        total_sanciones = 0
        for reserva in reservas:
            id_reserva = reserva['id_reserva']
            nombre_sala = reserva['nombre_sala']
            
            try:
                resultado = aplicar_sanciones_por_reserva(id_reserva, sancion_dias=60)
                
                if resultado['insertadas'] > 0:
                    print(f"  ✓ Reserva {id_reserva} ({nombre_sala}): {resultado['insertadas']} sanción(es) aplicada(s)")
                    print(f"    - Sancionados: {resultado['sancionados']}")
                    print(f"    - Motivo: {resultado['motivo']}")
                    total_sanciones += resultado['insertadas']
                else:
                    print(f"  - Reserva {id_reserva} ({nombre_sala}): Sin sanciones ({resultado['motivo']})")
                    
            except Exception as e:
                print(f"  ✗ Error procesando reserva {id_reserva}: {str(e)}")
        
        print(f"\nResumen: {total_sanciones} sanción(es) aplicada(s) en total")
        
    except Exception as e:
        print(f"Error en procesamiento: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    procesar_sanciones_diarias()
