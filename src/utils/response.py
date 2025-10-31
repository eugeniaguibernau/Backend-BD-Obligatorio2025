from flask import request


def with_auth_link(payload: dict) -> dict:

    try:
        base = request.host_url.rstrip('/')
        payload['auth_login_url'] = f"{base}/api/auth/login"
    except RuntimeError:
        payload['auth_login_url'] = '/api/auth/login'
    return payload
