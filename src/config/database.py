import os
import pymysql
from dotenv import load_dotenv
from typing import Any, Dict, List, Tuple, Optional

load_dotenv()


def get_db_config() -> Dict[str, Any]:
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 3306)),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),
        'database': os.getenv('DB_NAME', 'obligatorio'),
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

