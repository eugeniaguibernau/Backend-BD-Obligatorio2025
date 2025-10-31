import os
import pymysql
from dotenv import load_dotenv
from typing import Any, Dict, List, Tuple, Optional

load_dotenv()

def _env_or_raise(key: str) -> str:
    val = os.getenv(key)
    if val is None or val == "":
        raise RuntimeError(f"Falta la variable de entorno {key} en .env")
    return val

# Configuraciones para diferentes roles de base de datos
DB_USERS = {
    'readonly': {
        'user': os.getenv('DB_READONLY_USER', 'app_readonly'),
        'password': os.getenv('DB_READONLY_PASSWORD', 'readonly_pass_2025')
    },
    'user': {
        'user': os.getenv('DB_APP_USER', 'app_user'),
        'password': os.getenv('DB_APP_PASSWORD', 'user_pass_2025')
    },
    'admin': {
        'user': os.getenv('DB_ADMIN_USER', 'app_admin'),
        'password': os.getenv('DB_ADMIN_PASSWORD', 'admin_pass_2025')
    },
    'root': {  # Mantener compatibilidad con setup actual
        'user': _env_or_raise('DB_USER'),
        'password': os.getenv('DB_PASSWORD', '')
    }
}

def get_db_config(role: str = 'user') -> Dict[str, Any]:
    """
    Obtiene la configuración de base de datos según el rol.
    
    Args:
        role: 'readonly', 'user', 'admin', o 'root'
    """
    if role not in DB_USERS:
        raise ValueError(f"Rol de BD inválido: {role}. Usar: readonly, user, admin, root")
    
    user_config = DB_USERS[role]
    
    return {
        'host': _env_or_raise('DB_HOST'),
        'port': int(os.getenv('DB_PORT', '3306')), 
        'user': user_config['user'],
        'password': user_config['password'],    
        'database': _env_or_raise('DB_NAME'),
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor,
    }


def get_connection(role: str = 'user'):
    """
    Crea una conexión con el usuario MySQL apropiado.
    
    Args:
        role: 'readonly' (solo SELECT), 'user' (SELECT/INSERT/UPDATE), 
              'admin' (todo incluyendo DELETE)
    """
    cfg = get_db_config(role)
    conn = pymysql.connect(**cfg)
    return conn


def execute_query(query: str, params: Optional[Tuple] = None, role: str = 'readonly') -> List[Dict[str, Any]]:
    """
    Ejecuta una query de lectura y devuelve filas como dicts.
    
    Args:
        query: SQL query
        params: Parámetros para la query
        role: Rol de BD a usar ('readonly' por defecto para consultas)
    """
    conn = get_connection(role)
    try:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            result = cur.fetchall()
        return result
    finally:
        conn.close()


def execute_non_query(query: str, params: Optional[Tuple] = None, role: str = 'user') -> int:
    """
    Ejecuta INSERT/UPDATE/DELETE y devuelve el número de filas afectadas.
    
    Args:
        query: SQL query
        params: Parámetros para la query
        role: Rol de BD a usar ('user' por defecto, 'admin' para DELETE)
    """
    conn = get_connection(role)
    try:
        with conn.cursor() as cur:
            affected = cur.execute(query, params or ())
            conn.commit()
        return affected
    finally:
        conn.close()


