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
#comprobar contenedores
docker ps --filter "name=mysql_db" --filter "name=flask_app"
#comprobar health endpoint
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

# Scripts: Migración y verificación de hashes

Este archivo explica las utilidades administrativas relacionadas con el hashing de contraseñas.

Archivos disponibles

- `migrate_passwords_to_bcrypt.py` — re-hashea contraseñas en la tabla `login` que estén en texto plano. Dry-run por defecto; pasar `--apply` para aplicar cambios. Crea una tabla backup `login_backup_YYYYMMDDHHMMSS` antes de actualizar.
- `check_hashes.py` — muestra conteos y ejemplos de hashes en la tabla `login` (útil para comprobar el resultado de la migración).

Por qué existen

- Seguridad: almacenar contraseñas en texto plano es inseguro. Bcrypt es un algoritmo adecuado para contraseñas (salt+cost). Estos scripts permiten migrar datos de ejemplo o BD locales donde las seeds vinieran con contraseñas en claro.
- Reproducibilidad: permiten repetir la migración en entornos locales y automatizar verificaciones.

Cómo usar (ejemplos)

1) Preparar variables de entorno (ejemplo PowerShell local):

```powershell
$env:PYTHONPATH='.'
$env:DB_HOST='127.0.0.1'
$env:DB_PORT='3307'
$env:DB_USER='root'
$env:DB_PASSWORD='rootpassword'
$env:DB_NAME='proyecto'
```

2) Dry-run (no modifica la BD):

```powershell
python scripts\migrate_passwords_to_bcrypt.py
```

3) Verificar estado:

```powershell
python scripts\check_hashes.py
```

4) Aplicar la migración (crea backup y actualiza filas):

```powershell
# opcional: mysqldump -u root -p proyecto > proyecto_dump.sql
python scripts\migrate_passwords_to_bcrypt.py --apply
python scripts\check_hashes.py
```

Buenas prácticas

- No versionar archivos con credenciales (.env). Los scripts usan variables de entorno.
- Hacer backup externo antes de operaciones destructivas si los datos son críticos.
- Si la BD contiene hashes en otros formatos (por ejemplo `pbkdf2:`), adaptá el script antes de ejecutar `--apply` para no re-hashear hashes.
- Considerar colocar herramientas administrativas en una rama `ops` si preferís mantener la rama principal limpia.

Soporte en la app

- La lógica de la aplicación para crear/verificar contraseñas se encuentra en `src/auth/login.py`.
- Siempre hasheá la contraseña con `hash_password()` antes de hacer `INSERT`/`UPDATE`.

Si querés, puedo intentar insertar automáticamente un puntero en la parte final del `README.md` para enlazar a este archivo (si preferís que quede centralizado). Si preferís, puedo también crear una rama `ops/migrations` y mover `migrate_passwords_to_bcrypt.py` allí.


# Cómo funciona el login y cómo crear nuevos usuarios con contraseñas hasheadas


- Contrato mínimo (qué hace el código):
  - Input: `correo` (string) y `contraseña` (string sin hash) para el flujo de creación; para login el endpoint/función recibe `correo` + `contraseña` en claro.
  - Output: `authenticate_user(correo, contraseña)` retorna `(True, {"correo": ...})` si ok o `(False, "mensaje")` si falla.
  - Modos de error: usuario no encontrado, credenciales incorrectas, valores nulos.

- Dónde está la lógica:
  - `src/auth/login.py` contiene `hash_password(plain_password)`, `verify_password(...)` y `authenticate_user(...)`.
  - `hash_password` usa `bcrypt` y devuelve un string listo para guardar en la DB.

- Reglas importantes:
  - La tabla `login` tiene una FK `login.correo` -> `participante.email`. Debe existir el participante antes de insertar el login.
  - Guardá siempre el resultado de `hash_password()` en la columna `contraseña` (se usa el nombre con la ñ tal cual en la DB).
  - La columna debe tener suficiente longitud (recomendado VARCHAR(128)).

Ejemplos (PowerShell, desde la raíz del repo):

1) Generar un hash bcrypt para la contraseña (imprime el hash en stdout):

```powershell
$env:PYTHONPATH='.'; python -c "from src.auth.login import hash_password; print(hash_password('secreto123'))"
```

2) Insertar el participante (si no existe) y luego el login usando el hash obtenido:

```sql
-- Con un cliente MySQL conectado a la BD 'proyecto'
INSERT INTO participante (email, ci, nombre, apellido) VALUES ('eugenia123@gmail.com', 12345678, 'Eugenia', 'Perez');
INSERT INTO login (correo, `contraseña`) VALUES ('eugenia123@gmail.com', '<PEGAR_HASH_ACÁ>');
```

3) Alternativamente, generar el hash e insertar desde Python (usa la helper de conexión del proyecto):

```powershell
$env:PYTHONPATH='.'; python - <<'PY'
from src.auth.login import hash_password
from src.config.database import get_connection

correo = 'eugenia123@gmail.com'
hash_ = hash_password('secreto123')
conn = get_connection()
cur = conn.cursor()
# Asegurate de que el participante exista; si no, crear uno antes.
cur.execute("INSERT INTO login (correo, `contraseña`) VALUES (%s, %s)", (correo, hash_))
conn.commit()
cur.close()
conn.close()
print('Usuario creado o actualizado:', correo)
PY
```

Notas y edge-cases (rápido):
  - Si la tabla `login` ya tiene un registro para ese `correo`, preferí usar `UPDATE` en lugar de `INSERT` para no violar la PK/FK.
  - Si recibís errores de encoding al pegar hashes en SQL desde Windows, usá el cliente dentro del contenedor Docker o pegá el hash vía un script Python como en el ejemplo anterior.
  - Si tu BD contiene otros formatos de hash (pbkdf2, sha1, etc.), no llames al migrador `--apply` sin revisar: podrías re-hashear hashes por accidente.

Si querés, puedo:
- agregar un endpoint `/api/auth/login` que invoque `authenticate_user` y devuelva un JWT,
- o implementar un helper `create_user(correo, contraseña, participante_data)` en `src/auth` para centralizar la creación segura.

## Cómo crear un usuario con contraseña desde Postman

Si preferís crear usuarios vía HTTP (por ejemplo con Postman) en lugar de ejecutar comandos en la terminal, podés usar el endpoint que añadimos: `POST /api/auth/register`.

1) Asegurate de que la app esté corriendo localmente y que las variables de entorno apunten al servidor MySQL correcto (ej. `DB_HOST=127.0.0.1`, `DB_PORT=3307` si usás Docker con mapeo). Probá `GET /health` para confirmar.

2) En Postman:
  - Método: POST
  - URL: http://127.0.0.1:5000/api/auth/register
  - Headers: `Content-Type: application/json`
  - Body (raw JSON):

```json
{
  "correo": "eugenia123@gmail.com",
  "contraseña": "secreto123",
  "participante": { "ci": 44444444, "nombre": "Eugenia", "apellido": "Guibernau" }
}
```

3) Respuesta esperada:
  - 201 Created
  - Body: `{ "ok": true, "mensaje": "Usuario creado/actualizado" }`

4) Notas de seguridad y buenas prácticas:
  - No expongas `/api/auth/register` sin protección en producción: implementá autenticación/roles o limitá el endpoint a entornos de desarrollo.
  - Validá campos en el servidor (email válido, longitud de contraseña mínima) antes de crear registros.
  - No incluyas ni retornes el hash en las respuestas.

### Para qué sirve `auth_routes` y el cambio en `app.py`

- `src/routes/auth_routes.py` contiene un blueprint (`auth_bp`) que agrupa rutas relacionadas con autenticación y administración de cuentas (en nuestro caso, la ruta `POST /register`). Separar estas rutas en un blueprint mantiene el código organizado y modular.
- En `app.py` registramos ese blueprint con `app.register_blueprint(auth_bp, url_prefix='/api/auth')`. Eso hace que todas las rutas del blueprint estén disponibles bajo el prefijo `/api/auth`, por ejemplo `/api/auth/register`.
- Ventajas de usar un blueprint y registrar en `create_app()`:
  - Las rutas se cargan de forma consistente cuando se crea la app (factory pattern).
  - Evita definir rutas globales fuera del factory (menos problemas al importar y para testing).
  - Facilita aplicar middlewares, autenticación o políticas por prefijo.

## Endpoint: Login (/api/auth/login)

También añadimos un endpoint de login mínimo para autenticar usuarios usando la tabla `login`.

Uso desde Postman
- Método: POST
- URL: http://127.0.0.1:5000/api/auth/login
- Headers: `Content-Type: application/json`
- Body (raw JSON):

```json
{
  "correo": "eugenia123@gmail.com",
  "contraseña": "secreto123"
}
```

Respuestas esperadas
- 200 OK
  - Body: `{ "ok": true, "data": { "correo": "eugenia123@gmail.com" } }` cuando las credenciales son correctas.
- 401 Unauthorized
  - Body: `{ "ok": false, "mensaje": "Credenciales incorrectas" }` cuando la contraseña no coincide.
- 400 Bad Request
  - Body: `{ "ok": false, "mensaje": "correo y contraseña requeridos" }` si falta alguno de los campos.

Ejemplos rápidos desde PowerShell / curl
PowerShell (Invoke-RestMethod):

```powershell
$json = '{"correo":"eugenia123@gmail.com","contraseña":"secreto123"}'
Invoke-RestMethod -Method POST -Uri 'http://127.0.0.1:5000/api/auth/login' -Headers @{ 'Content-Type' = 'application/json' } -Body $json
```

curl:

```bash
curl -X POST http://127.0.0.1:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"correo":"eugenia123@gmail.com","contraseña":"secreto123"}'
```

Notas de seguridad
- En un sistema real conviene devolver un token (por ejemplo JWT) en lugar de sólo un ok/false y proteger endpoints sensibles.
- No expongas `/api/auth/register` ni `/api/auth/login` sin medidas de seguridad en producción (rate limiting, TLS, validación de inputs, autenticación para creación automática de usuarios, etc.).


# Cambios recientes: JWT y helper de respuesta

Se añadieron pequeñas utilidades y cambios orientados a facilitar la autenticación por token en entornos de desarrollo y pruebas:

- `src/auth/jwt_utils.py`: helpers para crear y verificar JSON Web Tokens (JWT). El token contiene el campo `sub` con el correo del usuario, `iat` y `exp`. La clave y tiempo de expiración están controlados por las variables de entorno `JWT_SECRET` y `JWT_EXP_HOURS`.
- `src/utils/response.py`: helper `with_auth_link(payload)` que inyecta en las respuestas GET un campo `auth_login_url` apuntando a `/api/auth/login` para facilitar la obtención del token desde clientes.
- `src/routes/auth_routes.py`: se añadió `POST /api/auth/register` y `POST /api/auth/login`. El `login` devuelve el JWT en el campo `token` junto con `ok`/`data`.

Notas operativas:
- Para generar/usar tokens en desarrollo, llamá `POST /api/auth/login` con `{ "correo":..., "contraseña":... }` y usá el JWT recibido en el header `Authorization: Bearer <token>` para endpoints que lo soporten.
- Por ahora los endpoints GET devuelven `auth_login_url` como pista; la protección real (verificar JWT en rutas) se puede añadir progresivamente según convenga.

Docker/requirements:
- Se actualizó el `Dockerfile` para instalar dependencias de compilación necesarias por `bcrypt` (por ejemplo `build-essential`, `libssl-dev`, `libffi-dev`) antes de `pip install`, ya que la imagen `python:3.12-slim` requiere estas librerías para compilar la extensión nativa.
- `requirements.txt` incluye `bcrypt` y `PyJWT` (entre otras). Si reconstruís la imagen, usá `docker-compose up --build app -d`.

Si preferís que esto vaya directamente en `README.md`, lo puedo mover/insertar allí después (tuviste un error al aplicar el parche; puedo intentarlo de nuevo o lo añadimos manualmente).
