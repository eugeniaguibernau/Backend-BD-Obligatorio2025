# Backend-BD-Obligatorio2025

Backend del sistema de gestión de reservas de salas universitarias. Implementado con Flask y MySQL.

## � Índice
- [Guía de Instalación y Ejecución Local](#-guía-de-instalación-y-ejecución-local)
- [Inicio Rápido](#-inicio-rápido)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Sistema de Seguridad](#-sistema-de-seguridad-3-capas)
- [API Endpoints](#-api-endpoints)
- [Ejemplos de Uso](#-ejemplos-de-uso)
- [Scripts Administrativos](#-scripts-administrativos)
- [Troubleshooting](#-troubleshooting)

---

## 🛠️ Guía de Instalación y Ejecución Local

### Prerrequisitos

Antes de comenzar, asegúrate de tener instalado:

- **Docker Desktop** (recomendado)
  - [Descargar para Mac](https://www.docker.com/products/docker-desktop)
  - [Descargar para Windows](https://www.docker.com/products/docker-desktop)
  - [Descargar para Linux](https://docs.docker.com/desktop/install/linux-install/)
- **Git** - Para clonar el repositorio
- **Python 3.12+** (opcional, solo si quieres correr sin Docker)
- **MySQL 8.0+** (opcional, solo si quieres correr sin Docker)

### Opción 1: Instalación con Docker (Recomendado)

Esta es la forma más sencilla y garantiza que todo funcione correctamente.

#### Paso 1: Clonar el repositorio

```bash
git clone https://github.com/eugeniaguibernau/Backend-BD-Obligatorio2025.git
cd Backend-BD-Obligatorio2025
```

#### Paso 2: Verificar el archivo .env

El archivo `.env` ya está configurado con valores por defecto. Verifica que contenga:

```env
# Flask
FLASK_ENV=development
FLASK_DEBUG=1

# MySQL Root
DB_HOST=db
DB_PORT=3306
DB_USER=root
DB_PASSWORD=rootpassword
DB_NAME=proyecto

# Usuarios MySQL para seguridad
DB_READONLY_USER=app_readonly
DB_READONLY_PASSWORD=readonly_pass_2025

DB_APP_USER=app_user
DB_APP_PASSWORD=user_pass_2025

DB_ADMIN_USER=app_admin
DB_ADMIN_PASSWORD=admin_pass_2025

# JWT
JWT_SECRET=tu_secreto_seguro_aqui
JWT_EXP_HOURS=24
```

> **Nota para producción**: Cambia `JWT_SECRET` por un valor seguro antes de desplegar.

#### Paso 3: Levantar los contenedores Docker

```bash
# Construir y levantar los servicios
docker-compose up -d

# Verificar que los contenedores estén corriendo
docker ps
```

Deberías ver dos contenedores corriendo:
- `mysql_db` - Base de datos MySQL en puerto 3307
- `flask_app` - Aplicación Flask en puerto 5000

#### Paso 4: Crear la base de datos y las tablas

```bash
# Opción A: Crear desde archivo SQL (si tienes el dump completo)
docker exec -i mysql_db mysql -u root -prootpassword < db/creacionDeTablas.sql

# Opción B: Si ya tienes la BD creada, solo inserta datos de prueba
docker exec -i mysql_db mysql -u root -prootpassword proyecto < db/insterts.sql
```

#### Paso 5: Crear usuarios MySQL con privilegios diferenciados

```bash
docker exec -i mysql_db mysql -u root -prootpassword proyecto < db/create_mysql_users.sql
```

Este comando crea tres usuarios:
- `app_readonly` - Solo SELECT (para reportes)
- `app_user` - SELECT, INSERT, UPDATE (operaciones normales)
- `app_admin` - ALL PRIVILEGES (operaciones administrativas)

#### Paso 6: Verificar que la aplicación esté corriendo

```bash
# Opción 1: Con curl
curl http://localhost:5000/api/reports/most-reserved-rooms

# Opción 2: Abrir en el navegador
# Visita: http://localhost:5000/api/reports/most-reserved-rooms
```

Si ves una respuesta JSON, ¡la aplicación está funcionando correctamente! 🎉

#### 📌 Sobre el Cronjob de Sanciones Automáticas

**¿Necesitas configurar algo adicional?** ❌ **NO**

El sistema incluye un **cronjob automático** que procesa sanciones diariamente. Esto ya está configurado en el Dockerfile y **se activa automáticamente** cuando levantas los contenedores con `docker-compose up`.

**¿Qué hace el cronjob?**
- Se ejecuta todos los días a las **8:00 AM**
- Busca reservas del día anterior que no tuvieron asistencia
- Aplica automáticamente sanciones de 60 días a los participantes que no asistieron
- Registra toda la actividad en logs

**Verificar que funciona:**

```bash
# Ver logs del procesamiento de sanciones
docker exec flask_app cat /var/log/sanciones.log

# Ejecutar manualmente para pruebas (procesa reservas de ayer)
docker exec flask_app python3 /app/scripts/procesar_sanciones_diarias.py
```

**Nota:** El cronjob usa la hora del contenedor Docker. Si necesitas ajustar el horario, edita el archivo `Dockerfile` y reconstruye la imagen.

#### Paso 7: Ver logs (opcional)

```bash
# Ver logs de Flask
docker logs -f flask_app

# Ver logs de MySQL
docker logs -f mysql_db

# Para salir de los logs presiona: Ctrl+C
```

### Opción 2: Instalación Sin Docker (Avanzado)

Si prefieres correr la aplicación directamente en tu máquina sin Docker:

#### Paso 1: Instalar MySQL

```bash
# macOS (con Homebrew)
brew install mysql@8.0
brew services start mysql@8.0

# Ubuntu/Debian
sudo apt-get install mysql-server
sudo systemctl start mysql

# Windows
# Descargar instalador desde: https://dev.mysql.com/downloads/installer/
```

#### Paso 2: Crear la base de datos

```bash
# Conectarse a MySQL como root
mysql -u root -p

# Dentro de MySQL, ejecutar:
CREATE DATABASE proyecto CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
exit;

# Importar las tablas
mysql -u root -p proyecto < db/creacionDeTablas.sql

# Importar datos de prueba (opcional)
mysql -u root -p proyecto < db/insterts.sql

# Crear usuarios con privilegios
mysql -u root -p proyecto < db/create_mysql_users.sql
```

#### Paso 3: Configurar el entorno Python

```bash
# Crear entorno virtual
python3 -m venv venv

# Activar el entorno virtual
# En macOS/Linux:
source venv/bin/activate

# En Windows:
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

#### Paso 4: Configurar variables de entorno

Edita el archivo `.env` y actualiza las credenciales de MySQL:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=tu_contraseña_mysql
DB_NAME=proyecto

# ... resto de las variables igual
```

#### Paso 5: Ejecutar la aplicación

```bash
python app.py
```

La aplicación estará disponible en `http://localhost:5000`

### Comandos Útiles

#### Docker

```bash
# Detener los contenedores
docker-compose down

# Reiniciar los contenedores
docker-compose restart

# Reconstruir las imágenes (si cambias Dockerfile o requirements.txt)
docker-compose up -d --build

# Ver estado de los contenedores
docker-compose ps

# Acceder a la consola de MySQL
docker exec -it mysql_db mysql -u root -prootpassword proyecto

# Acceder a la consola del contenedor Flask
docker exec -it flask_app bash
```

#### Base de Datos

```bash
# Backup de la base de datos
docker exec mysql_db mysqldump -u root -prootpassword proyecto > backup.sql

# Restaurar backup
docker exec -i mysql_db mysql -u root -prootpassword proyecto < backup.sql

# Ver usuarios MySQL creados
docker exec mysql_db mysql -u root -prootpassword -e "SELECT user, host FROM mysql.user WHERE user LIKE 'app_%';"
```

### Verificación de la Instalación

Para verificar que todo está funcionando correctamente, ejecuta estos comandos:

```bash
# 1. Verificar contenedores Docker
docker ps | grep -E "mysql_db|flask_app"

# 2. Verificar conexión a MySQL
docker exec mysql_db mysql -u app_readonly -preadonly_pass_2025 proyecto -e "SELECT 1;"

# 3. Probar endpoint de reportes
curl http://localhost:5000/api/reports/most-reserved-rooms

# 4. Verificar usuarios MySQL
docker exec mysql_db mysql -u root -prootpassword proyecto -e "SELECT user FROM mysql.user WHERE user LIKE 'app_%';"
```

### Solución de Problemas Comunes en la Instalación

#### Error: "Port 3307 is already allocated"

```bash
# Ver qué está usando el puerto
lsof -i :3307  # macOS/Linux
netstat -ano | findstr :3307  # Windows

# Cambiar el puerto en docker-compose.yml:
ports:
  - "3308:3306"  # Usar otro puerto
```

#### Error: "Cannot connect to MySQL"

```bash
# Esperar a que MySQL esté listo (puede tomar 10-15 segundos)
docker logs mysql_db

# Si sigue fallando, reiniciar el contenedor
docker-compose restart db
```

#### Error: "Module not found" en Flask

```bash
# Reconstruir la imagen Docker
docker-compose down
docker-compose up -d --build
```

#### El puerto 5000 no responde

```bash
# Ver los logs de Flask
docker logs flask_app

# Verificar que Flask esté corriendo
docker exec flask_app ps aux | grep python
```

---

## �🚀 Inicio Rápido

### Requisitos Previos
- Docker y Docker Compose
- Python 3.12 (si se ejecuta sin Docker)

### Levantar el Sistema con Docker

```bash
# 1. Levantar los contenedores
docker-compose up -d

# 2. Crear usuarios MySQL (primera vez)
docker exec -i mysql_db mysql -u root -prootpassword proyecto < db/create_mysql_users.sql

# 3. Verificar que la aplicación está corriendo
curl http://localhost:5000/api/reports/most-reserved-rooms
```

La aplicación estará disponible en `http://localhost:5000` y MySQL en `localhost:3307`.

## 📁 Estructura del Proyecto

```
Backend-BD-Obligatorio2025/
├── app.py                      # Punto de entrada de la aplicación
├── docker-compose.yml          # Configuración de Docker
├── Dockerfile                  # Imagen Docker de la aplicación
├── requirements.txt            # Dependencias Python
├── .env                        # Variables de entorno (no versionado)
├── db/
│   ├── creacionDeTablas.sql   # Script de creación de tablas
│   └── create_mysql_users.sql # Script de usuarios MySQL
├── scripts/
│   ├── check_hashes.py        # Verificar hashes en BD
│   └── migrate_passwords_to_bcrypt.py  # Migrar contraseñas
└── src/
    ├── auth/                   # Autenticación y JWT
    │   ├── jwt_utils.py
    │   └── login.py
    ├── config/                 # Configuración
    │   └── database.py
    ├── middleware/             # Control de permisos
    │   └── permissions.py
    ├── models/                 # Lógica de datos
    │   ├── participante_model.py
    │   ├── reserva_model.py
    │   ├── sala_model.py
    │   └── sancion_model.py
    ├── routes/                 # Endpoints API
    │   ├── auth_routes.py
    │   ├── participante_routes.py
    │   ├── reports_routes.py
    │   ├── reserva_routes.py
    │   ├── sala_routes.py
    │   └── sancion_routes.py
    ├── services/               # Lógica de negocio
    │   ├── reserva_service.py
    │   └── sancion_service.py
    └── utils/                  # Utilidades
        ├── validators.py
        └── response.py
```

## 🔐 Sistema de Seguridad (3 Capas)

### 1. Usuarios MySQL con Permisos Diferenciados
- **app_readonly**: Solo SELECT (reportes y consultas)
- **app_user**: SELECT, INSERT, UPDATE (operaciones normales)
- **app_admin**: ALL PRIVILEGES (operaciones administrativas)

### 2. JWT (JSON Web Tokens)
- Tokens incluyen `user_type` (admin/participante) y `user_id`
- Expiración configurable vía `JWT_EXP_HOURS`

### 3. Middleware de Permisos
- `@jwt_required`: Requiere autenticación
- `@require_admin`: Solo administradores
- `can_modify_resource()`: Usuario solo modifica sus recursos

## 🔧 Configuración

### Variables de Entorno (.env)

```env
# Flask
FLASK_ENV=development
FLASK_DEBUG=1

# MySQL Root
DB_HOST=db
DB_PORT=3306
DB_USER=root
DB_PASSWORD=rootpassword
DB_NAME=proyecto

# Usuarios MySQL para seguridad
DB_READONLY_USER=app_readonly
DB_READONLY_PASSWORD=readonly_pass_2025

DB_APP_USER=app_user
DB_APP_PASSWORD=user_pass_2025

DB_ADMIN_USER=app_admin
DB_ADMIN_PASSWORD=admin_pass_2025

# JWT
JWT_SECRET=tu_secreto_seguro_aqui
JWT_EXP_HOURS=24
```

## 📡 API Endpoints

### Autenticación
- `POST /api/auth/register` - Registrar usuario
- `POST /api/auth/login` - Login (retorna JWT)

### Participantes
- `GET /api/participantes` - Listar participantes
- `GET /api/participantes/<ci>` - Obtener participante
- `POST /api/participantes` - Crear participante
- `PUT /api/participantes/<ci>` - Actualizar participante
- `DELETE /api/participantes/<ci>` - Eliminar participante (admin)

### Salas
- `GET /api/salas` - Listar salas
- `GET /api/salas/<edificio>/<nombre>` - Obtener sala
- `POST /api/salas` - Crear sala (admin)
- `PUT /api/salas/<edificio>/<nombre>` - Actualizar sala (admin)
- `DELETE /api/salas/<edificio>/<nombre>` - Eliminar sala (admin)

### Reservas
- `GET /api/reservas` - Listar reservas
- `GET /api/reservas/<id>` - Obtener reserva
- `POST /api/reservas` - Crear reserva
- `PUT /api/reservas/<id>` - Actualizar reserva
- `DELETE /api/reservas/<id>` - Eliminar reserva (admin)
- `POST /api/reservas/<id>/participantes/<ci>/asistencia` - Marcar asistencia (admin)

### Sanciones
- `GET /api/sanciones` - Listar sanciones
- `POST /api/sanciones` - Crear sanción (admin)
- `DELETE /api/sanciones` - Eliminar sanción (admin)
- `POST /api/sanciones/aplicar/<id_reserva>` - Aplicar sanciones por reserva (admin)

### Reportes (Todos requieren autenticación)

#### Reportes Requeridos (8)
- `GET /api/reports/most-reserved-rooms` - Salas más reservadas
- `GET /api/reports/most-demanded-turns` - Turnos más demandados
- `GET /api/reports/avg-participants-by-room` - Promedio de participantes por sala
- `GET /api/reports/reservations-by-program` - Reservas por programa académico y facultad
- `GET /api/reports/occupancy-by-building` - Porcentaje de ocupación por edificio
- `GET /api/reports/reservations-and-attendance-by-role` - Reservas y asistencia de profesores/alumnos
- `GET /api/reports/sanctions-by-role` - Sanciones de profesores/alumnos
- `GET /api/reports/used-vs-cancelled` - Porcentaje de reservas utilizadas vs canceladas

#### Reportes Adicionales Sugeridos (3)
- `GET /api/reports/peak-hours-by-room` - Horas pico por sala (turnos más demandados por cada espacio)
- `GET /api/reports/occupancy-by-room-type` - Porcentaje de ocupación por tipo de sala (eficiencia por categoría)
- `GET /api/reports/repeat-offenders` - Participantes sancionados por reincidencia (más de una sanción)

## 🧪 Ejemplos de Uso

### Login y obtención de JWT

```bash
# Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"secret123"}'

# Respuesta: { "token": "eyJ...", "user_type": "admin", "user_id": 123 }
```

### Uso del JWT en requests

```bash
# Listar participantes (requiere JWT)
curl http://localhost:5000/api/participantes \
  -H "Authorization: Bearer eyJ..."
```

### Crear una reserva

```bash
curl -X POST http://localhost:5000/api/reservas \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ..." \
  -d '{
    "nombre_sala": "Lab 101",
    "edificio": "Central",
    "fecha": "2025-11-15",
    "id_turno": 1,
    "participantes": [12345678, 87654321]
  }'
```

## 🛠️ Scripts Administrativos

### Procesar sanciones diariamente (Cronjob Automático)

El sistema incluye un **cronjob automático** que se ejecuta todos los días a las **8:00 AM** dentro del contenedor Docker. Este script busca reservas del día anterior sin asistencia y aplica sanciones automáticamente.

**Ejecución manual (para pruebas):**

```bash
# Dentro del contenedor Docker (recomendado)
docker exec flask_app python3 /app/scripts/procesar_sanciones_diarias.py

# Sin Docker (si estás corriendo localmente)
python scripts/procesar_sanciones_diarias.py
```

**Ver logs de ejecuciones automáticas:**

```bash
# Ver todas las ejecuciones del cronjob
docker exec flask_app cat /var/log/sanciones.log

# Ver últimas 20 líneas
docker exec flask_app tail -20 /var/log/sanciones.log
```

**¿Qué hace este script?**
- Busca reservas activas del día anterior (ayer)
- Verifica si hubo asistencia registrada
- Si nadie asistió → aplica sanción de 60 días a todos los participantes
- Si alguien asistió → no aplica sanciones
- Registra resultados en `/var/log/sanciones.log`

**Cambiar horario del cronjob:**

Si necesitas cambiar la hora de ejecución (por defecto 8:00 AM), edita el `Dockerfile` línea ~26:

```dockerfile
# Cambiar de "0 8" (8:00 AM) a "0 14" (2:00 PM), por ejemplo
RUN echo "0 14 * * * cd /app && /usr/local/bin/python3 /app/scripts/procesar_sanciones_diarias.py >> /var/log/sanciones.log 2>&1" > /etc/cron.d/sanciones-cron
```

Luego reconstruir la imagen:

```bash
docker-compose down
docker-compose up -d --build
```

### Migrar contraseñas a bcrypt

```bash
# Dry-run (no modifica la BD)
python scripts/migrate_passwords_to_bcrypt.py

# Aplicar cambios (crea backup automático)
python scripts/migrate_passwords_to_bcrypt.py --apply
```

### Verificar hashes en la BD

```bash
python scripts/check_hashes.py
```

## 🐛 Troubleshooting

### La aplicación no se conecta a MySQL
```bash
# Verificar que los contenedores estén corriendo
docker ps

# Ver logs
docker logs mysql_db
docker logs flask_app
```

### Error de autenticación MySQL
```bash
# Recrear usuarios MySQL
docker exec -i mysql_db mysql -u root -prootpassword proyecto < db/create_mysql_users.sql
```

### Reiniciar completamente el sistema
```bash
docker-compose down
docker-compose up -d
docker exec -i mysql_db mysql -u root -prootpassword proyecto < db/create_mysql_users.sql
```

## 📝 Notas de Desarrollo

- Las contraseñas se almacenan usando bcrypt (nunca en texto plano)
- Todos los reportes usan el usuario `app_readonly` para máxima seguridad
- Las operaciones de DELETE usan el usuario `app_admin`
- Los participantes solo pueden ver/modificar sus propios recursos
- Los administradores tienen acceso completo a todos los recursos

## 📄 Licencia

Proyecto académico - Universidad ORT Uruguay - 2025

## 📄 Licencia

Proyecto académico - Universidad ORT Uruguay - 2025

