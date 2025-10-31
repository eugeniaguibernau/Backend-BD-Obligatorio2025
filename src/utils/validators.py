import re

EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'


def is_valid_email(email: str) -> bool:
    if not email or not isinstance(email, str):
        return False
    return re.match(EMAIL_REGEX, email) is not None


def is_strong_password(password: str) -> bool:
    """Simple password policy: at least 8 chars, max 128."""
    if not password or not isinstance(password, str):
        return False
    pw = password.strip()
    if len(pw) < 8 or len(pw) > 128:
        return False
    return True


def validate_participante(part: dict) -> (bool, str):
    """Validate optional participante payload. Returns (ok, message)."""
    # Ahora requerimos que el objeto `participante` exista y contenga `ci` válido.
    if not part:
        return False, 'participante requerido'
    if not isinstance(part, dict):
        return False, 'participante debe ser un objeto'

    nombre = part.get('nombre', '')
    apellido = part.get('apellido', '')
    # `ci` es obligatorio y debe ser un entero positivo
    if 'ci' not in part:
        return False, 'ci requerido en participante'
    ci = part.get('ci')

    if nombre and (not isinstance(nombre, str) or len(nombre) > 100):
        return False, 'nombre inválido'
    if apellido and (not isinstance(apellido, str) or len(apellido) > 100):
        return False, 'apellido inválido'
    try:
        ci_int = int(ci)
        if ci_int <= 0:
            return False, 'ci inválido'
    except Exception:
        return False, 'ci inválido'
    return True, ''
