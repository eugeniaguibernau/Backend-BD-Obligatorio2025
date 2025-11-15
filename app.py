from flask import Flask, jsonify, request, make_response
import os
from flask_cors import CORS

# Extensions
from src.extensions import limiter
from src.auth.jwt_utils import JWT_SECRET


def create_app(config_object=None):
    """
    Factory de la app Flask.
    - config_object: objeto de configuración opcional
    """

    app = Flask(__name__)

    # Evitar redirecciones por trailing slash que rompan preflight CORS
    app.url_map.strict_slashes = False

    # Asegurar que jsonify no escape caracteres unicode y que el JSON se sirva en UTF-8
    # Esto evita problemas con tildes/ñ en el frontend.
    app.config.setdefault('JSON_AS_ASCII', False)

    if config_object:
        app.config.from_object(config_object)

    # Habilitar CORS para los orígenes dev conocidos.
    # IMPORTANT: no usar '*' en Access-Control-Allow-Origin si se envían credenciales.
    allowed_origins = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://localhost:8080",
    ]

    CORS(
        app,
        resources={r"/*": {"origins": allowed_origins}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    )

    # Inicializar extensiones
    limiter.init_app(app)

    # Safety check: evitar arrancar en producción con la clave por defecto
    env = os.environ.get('FLASK_ENV') or app.config.get('ENV')
    if (env and env.lower() == 'production') and JWT_SECRET == 'dev-secret':
        raise RuntimeError('JWT_SECRET no debe ser el valor por defecto en producción. Configure la variable de entorno JWT_SECRET')

    # Registrar blueprints (rutas)
    from src.routes.sala_routes import sala_bp
    from src.routes.participante_routes import participante_bp
    app.register_blueprint(sala_bp, url_prefix='/salas')
    app.register_blueprint(participante_bp, url_prefix='/participantes')

    from src.routes.reserva_routes import reserva_bp
    app.register_blueprint(reserva_bp, url_prefix='/reservas')

    from src.routes.sancion_routes import sancion_bp
    app.register_blueprint(sancion_bp, url_prefix='/sanciones')

    from src.routes.auth_routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/api/auth')

    from src.routes.turno_routes import turno_bp
    app.register_blueprint(turno_bp, url_prefix='/turnos')

    from src.routes.reports_routes import reports_bp
    app.register_blueprint(reports_bp, url_prefix='/api/reports')

    # Registrar rutas de programas académicos
    # Asegurate de que src.routes.programas_routes exista y exporte programas_bp
    try:
        from src.routes.programas_routes import programas_bp
        app.register_blueprint(programas_bp, url_prefix='/programas')
    except Exception:
        # Si el blueprint no existe o da error, lo ignoramos aquí para no romper la app;
        # es preferible ver el error en los logs y corregir el módulo de rutas.
        app.logger.debug('No se pudo registrar programas_bp (archivo src.routes.programas_routes faltante o con errores)')

    @app.route('/health')
    def health():
        return jsonify({'status': 'ok'}), 200

    # Fallback seguro: asegurar que las respuestas incluyan los headers CORS
    # necesarios en caso de que Flask-CORS no los agregue por alguna razón.
    @app.after_request
    def _add_cors_headers(response):
        origin = request.headers.get('Origin')
        if origin and origin in allowed_origins:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'

        # Forzar charset utf-8 para respuestas JSON si no está presente
        content_type = response.headers.get('Content-Type', '')
        if 'application/json' in content_type.lower() and 'charset' not in content_type.lower():
            response.headers['Content-Type'] = 'application/json; charset=utf-8'

        return response

    return app


if __name__ == '__main__':
    app = create_app()
    # En dev, correr en 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000, debug=True)