USE proyecto;

-- === FACULTADES ===
INSERT INTO facultad (id_facultad, nombre) VALUES
  (1, 'Ingenieria'),
  (2, 'C. Economicas'),
  (3, 'Derecho'),
  (4, 'Psicologia');

-- === PROGRAMAS ACADÉMICOS ===
INSERT INTO programa_academico (nombre_programa, id_facultad, tipo) VALUES
  ('Ing. Informatica', 1, 'grado'),
  ('Ing. Industrial', 1, 'grado'),
  ('Contador', 2, 'grado'),
  ('Administracion', 2, 'grado'),
  ('Der. Civil', 3, 'postgrado'),
  ('Psicologia', 4, 'grado');

-- === PARTICIPANTES ===
INSERT INTO participante (ci, nombre, apellido, email) VALUES
  (48000001, 'Fabrizio', 'Rodriguez', 'fabrizio@ucu.edu.uy'),
  (48000002, 'Eugenia', 'Guibernau', 'euge@ucu.edu.uy'),
  (48000003, 'Lucas', 'Perez', 'lucas.perez@ucu.edu.uy'),
  (48000004, 'Martina', 'Garcia', 'martina.garcia@ucu.edu.uy'),
  (48000005, 'Sofia', 'Lopez', 'sofia.lopez@ucu.edu.uy'),
  (48000006, 'Tomas', 'Silva', 'tomas.silva@ucu.edu.uy'),
  (48000007, 'Valentina', 'Suarez', 'valentina.suarez@ucu.edu.uy'),
  (48000008, 'Joaquín', 'Fernandez', 'joaquin.fernandez@ucu.edu.uy'),
  (48000009, 'Camila', 'Ruiz', 'camila.ruiz@ucu.edu.uy'),
  (48000010, 'Bruno', 'Castro', 'bruno.castro@ucu.edu.uy');

-- === ADMINS ===
INSERT INTO admin (ci, nombre, apellido, email) VALUES
  (10000001, 'Ana', 'Admin', 'ana.admin@ucu.edu.uy'),
  (10000002, 'Pedro', 'Admin', 'pedro.admin@ucu.edu.uy'),
  (10000003, 'Laura', 'Admin', 'laura.admin@ucu.edu.uy');

-- === LOGIN ===
INSERT INTO login (correo, `contrasena`) VALUES
  ('fabrizio@ucu.edu.uy',        'hash_pass_1'),
  ('euge@ucu.edu.uy',            'hash_pass_2'),
  ('lucas.perez@ucu.edu.uy',     'hash_pass_3'),
  ('martina.garcia@ucu.edu.uy',  'hash_pass_4'),
  ('sofia.lopez@ucu.edu.uy',     'hash_pass_5'),
  ('tomas.silva@ucu.edu.uy',     'hash_pass_6'),
  ('valentina.suarez@ucu.edu.uy','hash_pass_7'),
  ('joaquin.fernandez@ucu.edu.uy','hash_pass_8'),
  ('camila.ruiz@ucu.edu.uy',     'hash_pass_9'),
  ('bruno.castro@ucu.edu.uy',    'hash_pass_10');

-- === PARTICIPANTE_PROGRAMA_ACADEMICO ===
INSERT INTO participante_programa_academico (ci_participante, nombre_programa, rol) VALUES
  (48000001, 'Ing. Informatica', 'alumno'),
  (48000002, 'Ing. Informatica', 'alumno'),
  (48000003, 'Ing. Industrial',  'alumno'),
  (48000004, 'Contador',         'alumno'),
  (48000005, 'Administracion',   'alumno'),
  (48000006, 'Ing. Informatica', 'docente'),
  (48000007, 'Der. Civil',       'postgrado'),
  (48000008, 'Psicologia',       'alumno'),
  (48000009, 'Psicologia',       'alumno'),
  (48000010, 'Administracion',   'alumno');

-- === EDIFICIOS ===
INSERT INTO edificio (nombre_edificio, direccion, departamento) VALUES
  ('Sede Central', 'Av. Principal 1234', 'Montevideo'),
  ('Anexo Norte',  'Av. Norte 567',      'Montevideo'),
  ('Campus Este',  'Ruta 8 km 20',       'Canelones');

-- === SALAS ===
INSERT INTO sala (nombre_sala, edificio, capacidad, tipo_sala) VALUES
  ('Sala 101', 'Sede Central', 40, 'libre'),
  ('Sala 102', 'Sede Central', 30, 'libre'),
  ('Sala 201', 'Sede Central', 80, 'docente'),
  ('Aula Norte 1', 'Anexo Norte', 35, 'libre'),
  ('Aula Norte 2', 'Anexo Norte', 25, 'posgrado'),
  ('Lab 1', 'Campus Este', 20, 'docente'),
  ('Lab 2', 'Campus Este', 25, 'libre');

-- === TURNOS ===
INSERT INTO turno (hora_inicio, hora_fin) VALUES
  ('2025-11-17 08:00:00', '2025-11-17 10:00:00'),
  ('2025-11-17 10:00:00', '2025-11-17 12:00:00'),
  ('2025-11-17 14:00:00', '2025-11-17 16:00:00'),
  ('2025-11-18 08:00:00', '2025-11-18 10:00:00'),
  ('2025-11-18 18:00:00', '2025-11-18 20:00:00');

-- === RESERVAS ===
INSERT INTO reserva (nombre_sala, edificio, fecha, id_turno, estado) VALUES
  ('Sala 101', 'Sede Central', '2025-11-17', 1, 'activa'),
  ('Sala 101', 'Sede Central', '2025-11-17', 2, 'finalizada'),
  ('Sala 201', 'Sede Central', '2025-11-17', 3, 'activa'),
  ('Aula Norte 1', 'Anexo Norte', '2025-11-18', 4, 'activa'),
  ('Lab 1', 'Campus Este', '2025-11-18', 5, 'cancelada');

-- === RESERVA_PARTICIPANTE ===
INSERT INTO reserva_participante (ci_participante, id_reserva, fecha_solicitud_reserva, asistencia) VALUES
  (48000001, 1, '2025-11-10', false),
  (48000002, 1, '2025-11-10', true),
  (48000003, 2, '2025-11-11', true),
  (48000004, 3, '2025-11-12', false),
  (48000005, 4, '2025-11-13', false),
  (48000008, 5, '2025-11-14', false);

-- === SANCION_PARTICIPANTE ===
INSERT INTO sancion_participante (ci_participante, fecha_inicio, fecha_fin, creado_por) VALUES
  (48000001, '2025-11-18', '2025-11-25', 'sistema'),
  (48000004, '2025-11-15', '2025-11-22', 'ana.admin@ucu.edu.uy'),
  (48000005, '2025-11-20', '2025-11-27', 'pedro.admin@ucu.edu.uy');
