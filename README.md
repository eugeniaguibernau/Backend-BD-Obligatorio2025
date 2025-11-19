# 🎓 Backend – Sistema de Reservas de Salas (UCU)

Backend del sistema de gestión de reservas de salas universitarias desarrollado en **Flask + MySQL**, con autenticación JWT, control de roles, reportes y sanciones automáticas.

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-orange.svg)](https://www.mysql.com/)
[![Docker](https://img.shields.io/badge/Docker-ready-blue.svg)](https://www.docker.com/)

---

## 📋 Tabla de Contenidos

- [Instalación Rápida](#-instalación-rápida-docker)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Seguridad del Sistema](#-seguridad-del-sistema)
- [Endpoints Principales](#-endpoints-principales)
- [Sanciones Automáticas](#-sanciones-automáticas-cronjob)
- [Troubleshooting](#-troubleshooting)

---

## Instalación (Docker)

### 1. Clonar el repositorio
```bash
git clone https://github.com/eugeniaguibernau/Backend-BD-Obligatorio2025.git
cd Backend-BD-Obligatorio2025
```

### 2. Verificar `.env`

El archivo `.env` debe contener los parámetros de conexión a MySQL y JWT.

**Valores por defecto para entorno local:**
```ini
DB_HOST=db
DB_PORT=3306
DB_USER=root
DB_PASSWORD=rootpassword
DB_NAME=proyecto
JWT_SECRET=tu_secreto_seguro
JWT_EXP_HOURS=24
```

> **Importante:** Modificar contraseñas para producción.

### 3. Levantar los servicios
```bash
docker-compose up -d
```

Este comando:
- Construye el backend
- Inicia MySQL
- Ejecuta automáticamente todos los scripts dentro de `docker-entrypoint-initdb.d`

| Script | Función |
|--------|---------|
| `001_creacionDeTablas.sql` | Crea las tablas |
| `002_SEED_FINAL_DATOS.sql` | Inserta datos de ejemplo |
| `003_create_mysql_users.sql` | Crea usuarios con permisos diferenciados |
| `004_arreglo_turnos.sql` | Ajusta turnos iniciales |

### Ejecutar manualmente
```bash
docker exec -it flask_app bash
Y DENTRO DE LA TERMINAL
python scripts/hasheador.py
```


### 4. Verificar funcionamiento
```bash
curl http://localhost:5000/api/reports/most-reserved-rooms
```

---

## Estructura del Proyecto
```
src/
├── auth/           # Login, JWT, autorización
├── config/         # Conexión MySQL y roles
├── middleware/     # Permisos de acceso
├── models/         # Consultas a BD
├── routes/         # Endpoints REST
├── services/       # Lógica de negocio
└── utils/          # Validaciones y helpers
```

---

## Seguridad del Sistema

### 1. Usuarios MySQL con permisos diferenciados

| Usuario | Permisos |
|---------|----------|
| `app_readonly` | Solo lectura |
| `app_user` | Operaciones normales |
| `app_admin` | Privilegios administrativos |

### 2. Autenticación JWT

- Tokens firmados con `JWT_SECRET`
- Incluyen `user_type` y `user_id`
- Expiran según `JWT_EXP_HOURS`

### 3. Middleware de permisos

- `@jwt_required` - Requiere autenticación
- `@require_admin` - Solo administradores
- Validación de propiedad de recursos

---

## Endpoints Principales

### Autenticación

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/api/auth/login` | Iniciar sesión |
| `POST` | `/api/auth/register` | Registrar usuario |

### Participantes

- Listado general
- Obtener participante por CI
- Crear, actualizar, eliminar

### Salas

- CRUD completo (solo administradores)

### Reservas

- Crear reserva
- Editar reserva
- Eliminar
- Registrar asistencia
- Consultar reservas

### Sanciones

- Crear / eliminar sanciones (admin)
- Aplicación automática diaria
- Consultar sanciones

### Reportes

**Incluye 8 reportes obligatorios + 3 adicionales:**

1. Salas más reservadas
2. Turnos más demandados
3. Promedio de participantes
4. Reservas por programa académico
5. Ocupación por edificio
6. Profesores vs alumnos
7. Sanciones por rol
8. Reservas usadas vs canceladas
9. Horas pico
10. Ocupación por tipo de sala
11. Participantes reincidentes

---

## Sanciones Automáticas (Cronjob)

El sistema ejecuta **diariamente** un proceso que:

1. Revisa reservas del día anterior
2. Detecta inasistencia
3. Aplica sanción automática de **60 días**
4. Registra actividad en: `/var/log/sanciones.log`

### Ejecutar manualmente
```bash
docker exec flask_app python3 /app/scripts/procesar_sanciones_diarias.py
```
