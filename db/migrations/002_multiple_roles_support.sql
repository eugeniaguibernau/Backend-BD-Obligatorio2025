-- ============================================
-- Migración: Soporte para múltiples roles
-- Permite que un participante tenga múltiples
-- combinaciones de programa + rol
-- ============================================
-- Fecha: 2025-11-16
-- Autor: Sistema
-- Descripción:
--   - Elimina UNIQUE constraint de ci_participante
--   - Cambia PK de id_alumno_programa a (ci_participante, nombre_programa, rol)
--   - Mantiene todos los datos existentes
--   - Actualiza FKs en reserva_participante y sancion_participante
-- ============================================

USE proyecto;

-- Verificación inicial
SELECT 'Iniciando migración 002: Soporte múltiples roles' as mensaje;
SELECT 'Estructura ANTES de la migración:' as mensaje;
SHOW CREATE TABLE participante_programa_academico;

-- ============================================
-- PASO 1: Eliminar Foreign Keys temporalmente
-- ============================================
SELECT 'PASO 1: Eliminando Foreign Keys...' as mensaje;

ALTER TABLE reserva_participante 
DROP FOREIGN KEY reserva_participante_ibfk_1;

ALTER TABLE sancion_participante 
DROP FOREIGN KEY sancion_participante_ibfk_1;

-- ============================================
-- PASO 2: Modificar participante_programa_academico
-- ============================================
SELECT 'PASO 2: Modificando tabla participante_programa_academico...' as mensaje;

-- 2.1: Eliminar la PK actual (id_alumno_programa)
ALTER TABLE participante_programa_academico 
DROP PRIMARY KEY;

-- 2.2: Eliminar el UNIQUE constraint de ci_participante
ALTER TABLE participante_programa_academico 
DROP INDEX ci_participante;

-- 2.3: Eliminar la columna id_alumno_programa (ya no la necesitamos)
ALTER TABLE participante_programa_academico 
DROP COLUMN id_alumno_programa;

-- 2.4: Crear nueva PK compuesta (permite misma persona con diferentes programa+rol)
ALTER TABLE participante_programa_academico 
ADD PRIMARY KEY (ci_participante, nombre_programa, rol);

-- ============================================
-- PASO 3: Recrear las Foreign Keys
-- ============================================
SELECT 'PASO 3: Recreando Foreign Keys...' as mensaje;

ALTER TABLE reserva_participante 
ADD CONSTRAINT reserva_participante_ibfk_1 
FOREIGN KEY (ci_participante) 
REFERENCES participante_programa_academico(ci_participante);

ALTER TABLE sancion_participante 
ADD CONSTRAINT sancion_participante_ibfk_1 
FOREIGN KEY (ci_participante) 
REFERENCES participante_programa_academico(ci_participante);

-- ============================================
-- PASO 4: Verificación final
-- ============================================
SELECT 'PASO 4: Verificación final...' as mensaje;

SELECT 'Estructura DESPUÉS de la migración:' as mensaje;
SHOW CREATE TABLE participante_programa_academico;

SELECT 'Columnas de la tabla:' as mensaje;
SHOW COLUMNS FROM participante_programa_academico;

SELECT 'Datos existentes (sin cambios):' as mensaje;
SELECT ci_participante, nombre_programa, rol 
FROM participante_programa_academico 
ORDER BY ci_participante;

SELECT '✅ Migración 002 completada exitosamente' as mensaje;
SELECT 'Ahora un participante puede tener múltiples combinaciones de programa+rol' as mensaje;
