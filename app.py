from flask import Flask, jsonify


def create_app(config_object=None):
	app = Flask(__name__)

	if config_object:
		app.config.from_object(config_object)

	# Blueprints: registrar rutas de los módulos (esto es a lo que después llamamos como endpoints del front)
	from src.routes.sala_routes import sala_bp
	from src.routes.participante_routes import participante_bp
	app.register_blueprint(sala_bp, url_prefix='/salas')
	app.register_blueprint(participante_bp, url_prefix='/participantes')

	# Registrar rutas de reserva
	from src.routes.reserva_routes import reserva_bp
	app.register_blueprint(reserva_bp, url_prefix='/reservas')

	# Registrar rutas de auth (register/login)
	from src.routes.auth_routes import auth_bp
	app.register_blueprint(auth_bp, url_prefix='/api/auth')

	# Registrar rutas de reportes (métricas BI)
	from src.routes.reports_routes import reports_bp
	app.register_blueprint(reports_bp, url_prefix='/api/reports')

	@app.route('/health')
	def health():
		return jsonify({'status': 'ok'}), 200

	return app


if __name__ == '__main__':
	app = create_app()
	app.run(host='0.0.0.0', port=5000, debug=True)
