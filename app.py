from flask import Flask, jsonify, request
import os
from flask_cors import CORS

# Extensions
from src.extensions import limiter
from src.auth.jwt_utils import JWT_SECRET


def create_app(config_object=None):
	app = Flask(__name__)

	# Aceptar rutas con o sin slash final para evitar redirecciones que rompen
	# las peticiones CORS preflight en algunos navegadores.
	app.url_map.strict_slashes = False

	if config_object:
		app.config.from_object(config_object)

	# Habilitar CORS para que el frontend pueda conectarse
	# Habilitar CORS únicamente para orígenes explícitos. No usar '*' cuando se envían credenciales.
	CORS(
		app,
		resources={r"/*": {"origins": ["http://localhost:5173", "http://localhost:5174", "http://localhost:3000", "http://localhost:8080"]}},
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

	# Blueprints: registrar rutas de los módulos (esto es a lo que después llamamos como endpoints del front)
	from src.routes.sala_routes import sala_bp
	from src.routes.participante_routes import participante_bp
	app.register_blueprint(sala_bp, url_prefix='/salas')
	app.register_blueprint(participante_bp, url_prefix='/participantes')

	# Registrar rutas de reserva
	from src.routes.reserva_routes import reserva_bp
	app.register_blueprint(reserva_bp, url_prefix='/reservas')

	# Registrar rutas de sanciones
	from src.routes.sancion_routes import sancion_bp
	app.register_blueprint(sancion_bp, url_prefix='/sanciones')

	# Registrar rutas de auth (register/login)
	from src.routes.auth_routes import auth_bp
	app.register_blueprint(auth_bp, url_prefix='/api/auth')

	# Registrar rutas de turnos
	from src.routes.turno_routes import turno_bp
	app.register_blueprint(turno_bp, url_prefix='/turnos')

	# Registrar rutas de reportes (métricas BI)
	from src.routes.reports_routes import reports_bp
	app.register_blueprint(reports_bp, url_prefix='/api/reports')

	@app.route('/health')
	def health():
		return jsonify({'status': 'ok'}), 200

	# Fallback seguro: asegurar que las respuestas incluyen los headers CORS
	# necesarios en caso de que Flask-CORS no los agregue por alguna razón.
	@app.after_request
	def _add_cors_headers(response):
		allowed_origins = ["http://localhost:5173", "http://localhost:5174", "http://localhost:3000", "http://localhost:8080"]
		origin = request.headers.get('Origin')
		if origin and origin in allowed_origins:
			response.headers['Access-Control-Allow-Origin'] = origin
			response.headers['Access-Control-Allow-Credentials'] = 'true'
			response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
			response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
		return response

	return app


if __name__ == '__main__':
	app = create_app()
	app.run(host='0.0.0.0', port=5000, debug=True)
