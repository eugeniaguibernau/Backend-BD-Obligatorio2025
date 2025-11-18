-- Reset and seed script: truncates data tables and inserts controlled seed data
-- BACKUP before running! This script will remove existing data.

SET @OLD_FK_CHECKS = @@FOREIGN_KEY_CHECKS;
SET FOREIGN_KEY_CHECKS = 0;

-- Truncate dependent tables in safe order
TRUNCATE TABLE reserva_participante;
TRUNCATE TABLE reserva;
TRUNCATE TABLE sancion_participante;
TRUNCATE TABLE participante_programa_academico;
TRUNCATE TABLE login;
TRUNCATE TABLE participante;
TRUNCATE TABLE sala;
TRUNCATE TABLE edificio;
TRUNCATE TABLE participante_programa_academico;
TRUNCATE TABLE programa_academico;
TRUNCATE TABLE facultad;
TRUNCATE TABLE turno;

-- Facultades y programas
INSERT INTO facultad (id_facultad, nombre) VALUES (1, 'Facultad de Ingeniería');
INSERT INTO facultad (id_facultad, nombre) VALUES (2, 'Facultad de Ciencias');

INSERT INTO programa_academico (nombre_programa, id_facultad, tipo) VALUES ('Ingeniería Informática', 1, 'grado');
INSERT INTO programa_academico (nombre_programa, id_facultad, tipo) VALUES ('Maestría en CS', 1, 'postgrado');
INSERT INTO programa_academico (nombre_programa, id_facultad, tipo) VALUES ('Licenciatura en Física', 2, 'grado');

-- Edificios y salas
INSERT INTO edificio (nombre_edificio, direccion, departamento) VALUES ('Central', 'Av. Principal 1000', 'Montevideo');
INSERT INTO edificio (nombre_edificio, direccion, departamento) VALUES ('Campus Este', 'Calle Falsa 123', 'Montevideo');

INSERT INTO sala (nombre_sala, edificio, capacidad, tipo_sala) VALUES ('Lab 101', 'Central', 10, 'libre');
INSERT INTO sala (nombre_sala, edificio, capacidad, tipo_sala) VALUES ('Aula Magna', 'Central', 200, 'libre');
INSERT INTO sala (nombre_sala, edificio, capacidad, tipo_sala) VALUES ('Sala Docente', 'Campus Este', 30, 'docente');

-- Participantes y logins
INSERT INTO participante (ci, nombre, apellido, email) VALUES (11111111, 'Fabrizio', 'Rodriguez', 'fabrizio@ucu.edu.uy');
INSERT INTO participante (ci, nombre, apellido, email) VALUES (22222222, 'Lucia', 'Fernandez', 'lucia@ucu.edu.uy');
INSERT INTO participante (ci, nombre, apellido, email) VALUES (33333333, 'Mateo', 'Perez', 'mateo@ucu.edu.uy');
INSERT INTO participante (ci, nombre, apellido, email) VALUES (44444444, 'Eugenia', 'Guibernau', 'eugenia@domain.com');
INSERT INTO participante (ci, nombre, apellido, email) VALUES (55555555, 'Docente', 'Profesor', 'docente@ucu.edu.uy');

-- Simple logins (passwords are placeholders, hashed in app normally).
-- Use positional INSERT to avoid issues with special characters in column names.
INSERT INTO login VALUES ('fabrizio@ucu.edu.uy', '$2b$12$aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa');
INSERT INTO login VALUES ('lucia@ucu.edu.uy', '$2b$12$bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb');
INSERT INTO login VALUES ('mateo@ucu.edu.uy', '$2b$12$cccccccccccccccccccccccccccccccccccccccccccccc');
INSERT INTO login VALUES ('eugenia@domain.com', '$2b$12$dddddddddddddddddddddddddddddddddddddddddddddd');
INSERT INTO login VALUES ('docente@ucu.edu.uy', '$2b$12$eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee');

-- Asociaciones a programas (importante: participante_programa_academico.ci_participante es UNIQUE)
INSERT INTO participante_programa_academico (ci_participante, nombre_programa, rol) VALUES (11111111, 'Ingeniería Informática', 'alumno');
INSERT INTO participante_programa_academico (ci_participante, nombre_programa, rol) VALUES (22222222, 'Ingeniería Informática', 'alumno');
INSERT INTO participante_programa_academico (ci_participante, nombre_programa, rol) VALUES (33333333, 'Licenciatura en Física', 'alumno');
INSERT INTO participante_programa_academico (ci_participante, nombre_programa, rol) VALUES (44444444, 'Maestría en CS', 'alumno');
INSERT INTO participante_programa_academico (ci_participante, nombre_programa, rol) VALUES (55555555, 'Ingeniería Informática', 'docente');

-- Turnos: crear bloques de 1 hora entre 08:00 y 23:00 (fecha base 2000-01-01)
INSERT INTO turno (hora_inicio, hora_fin)
SELECT '2000-01-01 08:00:00', '2000-01-01 09:00:00' WHERE NOT EXISTS (SELECT 1 FROM turno WHERE TIME(hora_inicio)='08:00:00' AND TIME(hora_fin)='09:00:00');
INSERT INTO turno (hora_inicio, hora_fin)
SELECT '2000-01-01 09:00:00', '2000-01-01 10:00:00' WHERE NOT EXISTS (SELECT 1 FROM turno WHERE TIME(hora_inicio)='09:00:00' AND TIME(hora_fin)='10:00:00');
INSERT INTO turno (hora_inicio, hora_fin)
SELECT '2000-01-01 10:00:00', '2000-01-01 11:00:00' WHERE NOT EXISTS (SELECT 1 FROM turno WHERE TIME(hora_inicio)='10:00:00' AND TIME(hora_fin)='11:00:00');
INSERT INTO turno (hora_inicio, hora_fin)
SELECT '2000-01-01 11:00:00', '2000-01-01 12:00:00' WHERE NOT EXISTS (SELECT 1 FROM turno WHERE TIME(hora_inicio)='11:00:00' AND TIME(hora_fin)='12:00:00');
INSERT INTO turno (hora_inicio, hora_fin)
SELECT '2000-01-01 12:00:00', '2000-01-01 13:00:00' WHERE NOT EXISTS (SELECT 1 FROM turno WHERE TIME(hora_inicio)='12:00:00' AND TIME(hora_fin)='13:00:00');
INSERT INTO turno (hora_inicio, hora_fin)
SELECT '2000-01-01 13:00:00', '2000-01-01 14:00:00' WHERE NOT EXISTS (SELECT 1 FROM turno WHERE TIME(hora_inicio)='13:00:00' AND TIME(hora_fin)='14:00:00');
INSERT INTO turno (hora_inicio, hora_fin)
SELECT '2000-01-01 14:00:00', '2000-01-01 15:00:00' WHERE NOT EXISTS (SELECT 1 FROM turno WHERE TIME(hora_inicio)='14:00:00' AND TIME(hora_fin)='15:00:00');
INSERT INTO turno (hora_inicio, hora_fin)
SELECT '2000-01-01 15:00:00', '2000-01-01 16:00:00' WHERE NOT EXISTS (SELECT 1 FROM turno WHERE TIME(hora_inicio)='15:00:00' AND TIME(hora_fin)='16:00:00');
INSERT INTO turno (hora_inicio, hora_fin)
SELECT '2000-01-01 16:00:00', '2000-01-01 17:00:00' WHERE NOT EXISTS (SELECT 1 FROM turno WHERE TIME(hora_inicio)='16:00:00' AND TIME(hora_fin)='17:00:00');
INSERT INTO turno (hora_inicio, hora_fin)
SELECT '2000-01-01 17:00:00', '2000-01-01 18:00:00' WHERE NOT EXISTS (SELECT 1 FROM turno WHERE TIME(hora_inicio)='17:00:00' AND TIME(hora_fin)='18:00:00');
INSERT INTO turno (hora_inicio, hora_fin)
SELECT '2000-01-01 18:00:00', '2000-01-01 19:00:00' WHERE NOT EXISTS (SELECT 1 FROM turno WHERE TIME(hora_inicio)='18:00:00' AND TIME(hora_fin)='19:00:00');
INSERT INTO turno (hora_inicio, hora_fin)
SELECT '2000-01-01 19:00:00', '2000-01-01 20:00:00' WHERE NOT EXISTS (SELECT 1 FROM turno WHERE TIME(hora_inicio)='19:00:00' AND TIME(hora_fin)='20:00:00');
INSERT INTO turno (hora_inicio, hora_fin)
SELECT '2000-01-01 20:00:00', '2000-01-01 21:00:00' WHERE NOT EXISTS (SELECT 1 FROM turno WHERE TIME(hora_inicio)='20:00:00' AND TIME(hora_fin)='21:00:00');
INSERT INTO turno (hora_inicio, hora_fin)
SELECT '2000-01-01 21:00:00', '2000-01-01 22:00:00' WHERE NOT EXISTS (SELECT 1 FROM turno WHERE TIME(hora_inicio)='21:00:00' AND TIME(hora_fin)='22:00:00');
INSERT INTO turno (hora_inicio, hora_fin)
SELECT '2000-01-01 22:00:00', '2000-01-01 23:00:00' WHERE NOT EXISTS (SELECT 1 FROM turno WHERE TIME(hora_inicio)='22:00:00' AND TIME(hora_fin)='23:00:00');

-- Crear varias reservas de ejemplo hasta 2025-12-09
-- Vamos a insertar algunos turnos para distintos participantes usando subselects para id_turno

-- Helper: fechas de muestra
INSERT INTO reserva (nombre_sala, edificio, fecha, id_turno, estado)
VALUES
('Lab 101', 'Central', '2025-11-20', (SELECT id_turno FROM turno WHERE TIME(hora_inicio)='08:00:00' LIMIT 1), 'activa'),
('Lab 101', 'Central', '2025-11-25', (SELECT id_turno FROM turno WHERE TIME(hora_inicio)='09:00:00' LIMIT 1), 'activa'),
('Aula Magna', 'Central', '2025-12-01', (SELECT id_turno FROM turno WHERE TIME(hora_inicio)='10:00:00' LIMIT 1), 'activa'),
('Lab 101', 'Central', '2025-12-05', (SELECT id_turno FROM turno WHERE TIME(hora_inicio)='11:00:00' LIMIT 1), 'activa'),
('Aula Magna', 'Central', '2025-12-09', (SELECT id_turno FROM turno WHERE TIME(hora_inicio)='12:00:00' LIMIT 1), 'activa');

-- Asociar participantes a las reservas (copiar participantes)
INSERT INTO reserva_participante (ci_participante, id_reserva, fecha_solicitud_reserva, asistencia)
SELECT 11111111, id_reserva, NOW(), NULL FROM reserva WHERE nombre_sala='Lab 101' AND fecha='2025-11-20' LIMIT 1;
INSERT INTO reserva_participante (ci_participante, id_reserva, fecha_solicitud_reserva, asistencia)
SELECT 22222222, id_reserva, NOW(), NULL FROM reserva WHERE nombre_sala='Lab 101' AND fecha='2025-11-25' LIMIT 1;
INSERT INTO reserva_participante (ci_participante, id_reserva, fecha_solicitud_reserva, asistencia)
SELECT 33333333, id_reserva, NOW(), NULL FROM reserva WHERE nombre_sala='Aula Magna' AND fecha='2025-12-01' LIMIT 1;
INSERT INTO reserva_participante (ci_participante, id_reserva, fecha_solicitud_reserva, asistencia)
SELECT 44444444, id_reserva, NOW(), NULL FROM reserva WHERE nombre_sala='Lab 101' AND fecha='2025-12-05' LIMIT 1;
INSERT INTO reserva_participante (ci_participante, id_reserva, fecha_solicitud_reserva, asistencia)
SELECT 55555555, id_reserva, NOW(), NULL FROM reserva WHERE nombre_sala='Aula Magna' AND fecha='2025-12-09' LIMIT 1;

SET FOREIGN_KEY_CHECKS = @OLD_FK_CHECKS;

-- End of seed
