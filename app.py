from flask import Flask, jsonify


def create_app(config_object=None):
	app = Flask(__name__)

	if config_object:
		app.config.from_object(config_object)

	# Blueprints: registrar rutas de los módulos (esto es a lo que después llamamos como endpoints del front)
	from src.routes.sala_routes import sala_bp
	app.register_blueprint(sala_bp, url_prefix='/salas')

	@app.route('/health')
	def health():
		return jsonify({'status': 'ok'}), 200

	return app


if __name__ == '__main__':
	app = create_app()
	app.run(host='0.0.0.0', port=5000, debug=True)
