-- Script para crear usuarios MySQL con diferentes privilegios
-- Ejecutar como root en MySQL

-- 1. Usuario de solo lectura (para reportes y consultas)
CREATE USER IF NOT EXISTS 'app_readonly'@'%' IDENTIFIED BY 'readonly_pass_2025';
GRANT SELECT ON proyecto.* TO 'app_readonly'@'%';

-- 2. Usuario para operaciones normales (INSERT, UPDATE, SELECT)
CREATE USER IF NOT EXISTS 'app_user'@'%' IDENTIFIED BY 'user_pass_2025';
GRANT SELECT, INSERT, UPDATE ON proyecto.* TO 'app_user'@'%';

-- 3. Usuario administrador (todas las operaciones incluyendo DELETE)
CREATE USER IF NOT EXISTS 'app_admin'@'%' IDENTIFIED BY 'admin_pass_2025';
GRANT ALL PRIVILEGES ON proyecto.* TO 'app_admin'@'%';

-- Aplicar cambios
FLUSH PRIVILEGES;

-- Verificar usuarios creados
SELECT user, host FROM mysql.user WHERE user LIKE 'app_%';
