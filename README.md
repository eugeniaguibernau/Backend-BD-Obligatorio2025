# Backend-BD-Obligatorio2025

Proyecto backend para el trabajo práctico. Usando Flask y MySQL.

Setup rápido (macOS / zsh):

1. Crear y activar un entorno virtual

```zsh
python3 -m venv .venv
source .venv/bin/activate
```

2. Instalar dependencias

```zsh
pip install -r requirements.txt
```

3. Configurar variables de entorno (ejemplo con MySQL local)

```zsh
export DB_USER=root
export DB_PASSWORD=secret
export DB_HOST=127.0.0.1
export DB_PORT=3306
export DB_NAME=obligatorio
# o export DATABASE_URL='mysql+pymysql://user:pass@host:port/dbname'
```

4. Ejecutar la app

```zsh
python app.py
```

La app expondrá /health para comprobar que está levantada.

## Cómo probar los endpoints de Reserva (paso a paso)

Estos pasos asumen que usás el `docker-compose.yml` del proyecto (el servicio MySQL está mapeado en el puerto 3307 y la app en el puerto 5000). Ajustá host/puerto si corres la app de otra forma.

1) Levantar los servicios (en la carpeta del proyecto):

```powershell
docker-compose up -d
```

2) Comprobar que la app y la BD están arriba:

```powershell
# comprobar contenedores
docker ps --filter "name=mysql_db" --filter "name=flask_app"
# comprobar health endpoint
curl http://127.0.0.1:5000/health
```

3) Listar reservas (GET)

```powershell
curl -s http://127.0.0.1:5000/reservas/ | jq
```

4) Crear una reserva (POST)

Request (JSON) — campos requeridos:
- nombre_sala (string)
- edificio (string)
- fecha (YYYY-MM-DD)
- id_turno (int)
- participantes (array de CI, enteros)

Ejemplo:

```powershell
curl -X POST http://127.0.0.1:5000/reservas/ \
	-H "Content-Type: application/json" \
	-d '{"nombre_sala":"Lab 101","edificio":"Central","fecha":"2025-11-10","id_turno":1,"participantes":[11111111,22222222]}' | jq
```

Respuesta esperada (201):

```json
{ "reserva_creada": 123 }
```

5) Obtener una reserva por id (GET)

```powershell
curl http://127.0.0.1:5000/reservas/123
```

6) Actualizar una reserva (PUT)

Envía un JSON con los campos a actualizar (por ejemplo `estado`):

```powershell
curl -X PUT http://127.0.0.1:5000/reservas/123 \
	-H "Content-Type: application/json" \
	-d '{"estado":"cancelada"}' | jq
```

7) Eliminar una reserva (DELETE)

```powershell
curl -X DELETE http://127.0.0.1:5000/reservas/123
```

Notas importantes
- Si la DB está corriendo en Docker (como en este repo) el contenedor expone MySQL en el puerto 3307 del host — esa información está en `docker-compose.yml`.
- Si recibís errores de charset/ñ al ejecutar scripts SQL desde Windows, preferí copiar el archivo dentro del contenedor (`docker cp`) y usar `source` dentro del contenedor con `--default-character-set=utf8mb4`.
- Para probar rápidamente sin usar curl podés usar el cliente de pruebas de Flask dentro del contenedor (ya lo usamos para tests locales) o herramientas como Postman / Insomnia.
