import os
import jwt
from datetime import datetime, timedelta

JWT_SECRET = os.environ.get('JWT_SECRET', 'dev-secret')
JWT_ALGORITHM = 'HS256'
JWT_EXP_HOURS = int(os.environ.get('JWT_EXP_HOURS', '2'))


def create_token(subject: str) -> str:
    now = datetime.utcnow()
    payload = {
        'sub': subject,
        'iat': now,
        'exp': now + timedelta(hours=JWT_EXP_HOURS)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    # In PyJWT >=2.x, jwt.encode returns a str
    return token


def verify_token(token: str):
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return True, data
    except Exception as e:
        return False, str(e)
