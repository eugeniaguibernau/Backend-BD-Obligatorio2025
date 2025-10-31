import bcrypt
from src.config.database import get_connection


def hash_password(plain_password: str) -> str:
	"""Genera un hash usando bcrypt y devuelve un string listo para guardar.

	bcrypt genera y almacena la salt dentro del propio hash, por lo que no hace
	falta guardarla por separado.
	"""
	if plain_password is None:
		raise ValueError("La contraseña no puede ser nula")
	# rounds/cost: 12 es un valor razonable; ajústalo si tu servidor es muy lento/rápido
	hashed = bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt(rounds=12))
	return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
	"""Verifica la contraseña usando exclusivamente bcrypt.

	Requiere que `hashed_password` sea un hash bcrypt (empieza con '$2').
	"""
	if plain_password is None or hashed_password is None:
		return False
	try:
		# bcrypt hashes son bytes; usamos encoding utf-8
		return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
	except Exception:
		return False


def authenticate_user(correo: str, plain_password: str):
	"""Comprueba credenciales contra la tabla `login`.

	Retorna una tupla (ok: bool, data_or_message).
	- Si ok=True -> data_or_message es el diccionario del usuario (correo)
	- Si ok=False -> data_or_message es un mensaje de error
	"""
	if not correo or not plain_password:
		return False, "correo y contraseña requeridos"

	conn = get_connection()
	cur = conn.cursor()
	cur.execute("SELECT correo, contraseña FROM login WHERE correo = %s", (correo,))
	row = cur.fetchone()
	cur.close()
	conn.close()

	if not row:
		return False, "Usuario no encontrado"

	hashed = row.get('contraseña') if isinstance(row, dict) else row[1]
	if not verify_password(plain_password, hashed):
		return False, "Credenciales incorrectas"

	return True, {"correo": correo}
