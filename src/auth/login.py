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
	- Si ok=True -> data_or_message es el diccionario del usuario con tipo y ID
	- Si ok=False -> data_or_message es un mensaje de error
	"""
	if not correo or not plain_password:
		return False, "correo y contraseña requeridos"

	conn = get_connection('readonly')
	cur = conn.cursor()
	cur.execute("SELECT correo, contraseña FROM login WHERE correo = %s", (correo,))
	row = cur.fetchone()

	if not row:
		cur.close()
		conn.close()
		return False, "Usuario no encontrado"

	hashed = row.get('contraseña') if isinstance(row, dict) else row[1]
	if not verify_password(plain_password, hashed):
		cur.close()
		conn.close()
		return False, "Credenciales incorrectas"
	
	# Determinar si es admin o participante
	cur.execute("SELECT ci FROM admin WHERE email = %s", (correo,))
	admin_row = cur.fetchone()
	
	if admin_row:
		# Es admin
		user_type = 'admin'
		user_id = admin_row.get('ci') if isinstance(admin_row, dict) else admin_row[0]
	else:
		# Es participante
		cur.execute("SELECT ci FROM participante WHERE email = %s", (correo,))
		part_row = cur.fetchone()
		user_type = 'participante'
		user_id = part_row.get('ci') if part_row and isinstance(part_row, dict) else (part_row[0] if part_row else None)
	
	cur.close()
	conn.close()

	return True, {
		"correo": correo,
		"user_type": user_type,
		"user_id": user_id
	}
