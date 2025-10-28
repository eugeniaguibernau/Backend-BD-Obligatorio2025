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

def get_db_config() -> Dict[str, Any]:
    return {
        'host': _env_or_raise('DB_HOST'),
        'port': int(os.getenv('DB_PORT', '3306')), 
        'user': _env_or_raise('DB_USER'),
        'password': os.getenv('DB_PASSWORD', ''),    
        'database': _env_or_raise('DB_NAME'),
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor,
    }


def get_connection():
    cfg = get_db_config()
    conn = pymysql.connect(**cfg)
    return conn


def execute_query(query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
    """Ejecuta una query de lectura y devuelve filas como dicts."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            result = cur.fetchall()
        return result
    finally:
        conn.close()


def execute_non_query(query: str, params: Optional[Tuple] = None) -> int:
    """Ejecuta INSERT/UPDATE/DELETE y devuelve el número de filas afectadas."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            affected = cur.execute(query, params or ())
            conn.commit()
        return affected
    finally:
        conn.close()

