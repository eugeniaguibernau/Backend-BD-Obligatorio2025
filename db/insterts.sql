USE proyecto;

INSERT INTO participante (ci, nombre, apellido, email) VALUES
(11111111, 'Fabrizio', 'Rodríguez', 'fabrizio@ucu.edu.uy'),
(22222222, 'Lucía', 'Fernández', 'lucia@ucu.edu.uy'),
(33333333, 'Mateo', 'Pérez', 'mateo@ucu.edu.uy');

INSERT INTO admin (ci, nombre, apellido, email) VALUES
(99999999, 'Ana', 'Silva', 'ana.silva@ucu.edu.uy');

INSERT INTO login (correo, contraseña) VALUES
('fabrizio@ucu.edu.uy', '$2b$12$FejbkwVJRhvTEow4V05GIuKamP.zcKQAMwLSv3urDzMGIpKw.Im6y'),
('lucia@ucu.edu.uy',    '$2b$12$lG.XpyXJRd4GnhEAlzfSeusjoNG.V5vKseTYPghO.G3JlJsNonC0S'),
('mateo@ucu.edu.uy',    '$2b$12$VChKZrpWtwo/Q04EQE1WqeRcdM85.mxDIaDGnk11PxgtUOkOUb1Bi');

INSERT INTO facultad (nombre) VALUES
('Ingeniería'),
('Ciencias Humanas'),
('Derecho');

INSERT INTO programa_academico (nombre_programa, id_facultad, tipo) VALUES
('Informática', 1, 'grado'),
('Psicología', 2, 'grado'),
('Derecho Penal', 3, 'postgrado');

INSERT INTO participante_programa_academico (ci_participante, nombre_programa, rol) VALUES
(11111111, 'Informática', 'alumno'),
(22222222, 'Psicología', 'alumno'),
(33333333, 'Informática', 'docente');

INSERT INTO edificio (nombre_edificio, direccion, departamento) VALUES
('Central', 'Av. 8 de Octubre 2738', 'Montevideo'),
('Campus Este', 'Ruta Interbalnearia Km 30', 'Canelones');

INSERT INTO sala (nombre_sala, edificio, capacidad, tipo_sala) VALUES
('Lab 101', 'Central', 25, 'libre'),
('Aula Magna', 'Central', 100, 'posgrado'),
('Sala Docente', 'Campus Este', 10, 'docente');

INSERT INTO turno (hora_inicio, hora_fin) VALUES
('2025-10-25 08:00:00', '2025-10-25 10:00:00'),
('2025-10-25 10:00:00', '2025-10-25 12:00:00'),
('2025-10-25 14:00:00', '2025-10-25 16:00:00');

INSERT INTO reserva (nombre_sala, edificio, fecha, id_turno, estado) VALUES
('Lab 101', 'Central', '2025-10-26', 1, 'activa'),
('Aula Magna', 'Central', '2025-10-27', 2, 'finalizada'),
('Sala Docente', 'Campus Este', '2025-10-28', 3, 'activa');

INSERT INTO reserva_participante (ci_participante, id_reserva, fecha_solicitud_reserva, asistencia) VALUES
(11111111, 1, '2025-10-20', true),
(22222222, 2, '2025-10-21', false),
(33333333, 3, '2025-10-22', true);

INSERT INTO sancion_participante (ci_participante, fecha_inicio, fecha_fin) VALUES
(22222222, '2025-09-01', '2025-09-15'),
(11111111, '2025-08-10', '2025-08-20');

