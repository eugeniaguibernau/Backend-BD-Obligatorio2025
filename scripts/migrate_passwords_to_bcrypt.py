#!/usr/bin/env python3
"""Script para migrar contraseñas en la tabla `login` a bcrypt.

Modo de uso:
  # dry-run (no modifica la BD)
  python scripts/migrate_passwords_to_bcrypt.py

  # aplicar cambios (crea backup y actualiza filas)
  python scripts/migrate_passwords_to_bcrypt.py --apply

Requisitos:
  - Ejecutar desde la raíz del proyecto (para que importe src.* funcione)
  - Tener `bcrypt` instalado (requirements.txt ya actualizado)
  - Hacer backup externo antes de usar --apply (el script creará una copia simple)

Este script asume que la columna de la tabla `login` se llama `contraseña` y que hay
una columna `id` (clave primaria). Si tu esquema es distinto, ajusta las consultas.
"""
import argparse
import datetime
import sys
from src.auth.login import hash_password
from src.config.database import execute_query, execute_non_query


def is_bcrypt_hash(s: str) -> bool:
    return isinstance(s, str) and s.startswith('$2')


def backup_table():
    ts = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')
    backup_name = f'login_backup_{ts}'
    print(f"Creando backup de la tabla 'login' como '{backup_name}'...")
    # CREATE TABLE ... AS SELECT ...
    execute_non_query(f"CREATE TABLE {backup_name} AS SELECT * FROM login")
    print("Backup creado.")
    return backup_name


def migrate(apply: bool = False):
    # Seleccionamos por 'correo' (PK en este esquema) porque no siempre existe una columna 'id'
    rows = execute_query("SELECT correo, `contraseña` FROM login")
    to_update = []
    for row in rows:
        correo = row.get('correo') if isinstance(row, dict) else row[0]
        pwd = row.get('contraseña') if isinstance(row, dict) else row[1]
        if pwd is None or (isinstance(pwd, str) and pwd.strip() == ''):
            # contraseña vacía/null: no intentamos hashearla
            continue
        if not is_bcrypt_hash(pwd):
            to_update.append((correo, pwd))

    if not to_update:
        print("No se encontraron contraseñas en texto plano o no-bcrypt. Nada que hacer.")
        return

    print(f"Filas detectadas para migrar: {len(to_update)}")
    for correo, plain in to_update:
        print(f"- correo={correo}")

    if not apply:
        print("\nDry-run: no se aplicaron cambios. Ejecuta con --apply para re-hashear y actualizar la BD.")
        return

    # Aplicar: primero backup
    backup_table()

    # Actualizar cada fila
    for correo, plain in to_update:
        try:
            new_hash = hash_password(plain)
            execute_non_query("UPDATE login SET `contraseña` = %s WHERE correo = %s", (new_hash, correo))
            print(f"Actualizada correo={correo}")
        except Exception as exc:
            print(f"Error actualizando correo={correo}: {exc}")


def main():
    parser = argparse.ArgumentParser(description='Migrar contraseñas a bcrypt (desde texto plano almacenado).')
    parser.add_argument('--apply', action='store_true', help='Aplica los cambios en la base de datos (por defecto dry-run).')
    args = parser.parse_args()

    # Confirmación sencilla
    if args.apply:
        print("MODO: aplicar cambios en la base de datos")
    else:
        print("MODO: dry-run (no se harán cambios). Use --apply para aplicar")

    migrate(apply=args.apply)


if __name__ == '__main__':
    main()
