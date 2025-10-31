from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Limiter instance: init_app(app) in app.create_app()
limiter = Limiter(key_func=get_remote_address)
