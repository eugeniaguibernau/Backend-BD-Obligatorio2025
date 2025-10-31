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
    if not part:
        return True, ''
    if not isinstance(part, dict):
        return False, 'participante debe ser un objeto'
    nombre = part.get('nombre', '')
    apellido = part.get('apellido', '')
    ci = part.get('ci', 0)
    if nombre and (not isinstance(nombre, str) or len(nombre) > 100):
        return False, 'nombre inválido'
    if apellido and (not isinstance(apellido, str) or len(apellido) > 100):
        return False, 'apellido inválido'
    try:
        if ci and int(ci) < 0:
            return False, 'ci inválido'
    except Exception:
        return False, 'ci inválido'
    return True, ''
