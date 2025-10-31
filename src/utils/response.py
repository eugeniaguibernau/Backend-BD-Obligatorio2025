from flask import request


def with_auth_link(payload: dict) -> dict:
    """Attach a link to the auth login endpoint into the response payload.

    Uses the current request host to construct a full URL to /api/auth/login.
    """
    try:
        base = request.host_url.rstrip('/')
        payload['auth_login_url'] = f"{base}/api/auth/login"
    except RuntimeError:
        # no request context; skip
        payload['auth_login_url'] = '/api/auth/login'
    return payload
