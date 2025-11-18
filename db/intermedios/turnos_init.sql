-- Inserta turnos horarios de 1 hora entre 08:00 y 23:00
-- Este script añade los turnos que faltan sin eliminar existentes.
-- Compara solo TIME(hora_inicio) y TIME(hora_fin) para evitar duplicados funcionales.

START TRANSACTION;

-- Insertar cada bloque si no existe ya uno con las mismas horas
INSERT INTO turno (hora_inicio, hora_fin)
SELECT '2000-01-01 08:00:00', '2000-01-01 09:00:00'
WHERE NOT EXISTS (SELECT 1 FROM turno WHERE TIME(hora_inicio) = '08:00:00' AND TIME(hora_fin) = '09:00:00');

INSERT INTO turno (hora_inicio, hora_fin)
SELECT '2000-01-01 09:00:00', '2000-01-01 10:00:00'
WHERE NOT EXISTS (SELECT 1 FROM turno WHERE TIME(hora_inicio) = '09:00:00' AND TIME(hora_fin) = '10:00:00');

INSERT INTO turno (hora_inicio, hora_fin)
SELECT '2000-01-01 10:00:00', '2000-01-01 11:00:00'
WHERE NOT EXISTS (SELECT 1 FROM turno WHERE TIME(hora_inicio) = '10:00:00' AND TIME(hora_fin) = '11:00:00');

INSERT INTO turno (hora_inicio, hora_fin)
SELECT '2000-01-01 11:00:00', '2000-01-01 12:00:00'
WHERE NOT EXISTS (SELECT 1 FROM turno WHERE TIME(hora_inicio) = '11:00:00' AND TIME(hora_fin) = '12:00:00');

INSERT INTO turno (hora_inicio, hora_fin)
SELECT '2000-01-01 12:00:00', '2000-01-01 13:00:00'
WHERE NOT EXISTS (SELECT 1 FROM turno WHERE TIME(hora_inicio) = '12:00:00' AND TIME(hora_fin) = '13:00:00');

INSERT INTO turno (hora_inicio, hora_fin)
SELECT '2000-01-01 13:00:00', '2000-01-01 14:00:00'
WHERE NOT EXISTS (SELECT 1 FROM turno WHERE TIME(hora_inicio) = '13:00:00' AND TIME(hora_fin) = '14:00:00');

INSERT INTO turno (hora_inicio, hora_fin)
SELECT '2000-01-01 14:00:00', '2000-01-01 15:00:00'
WHERE NOT EXISTS (SELECT 1 FROM turno WHERE TIME(hora_inicio) = '14:00:00' AND TIME(hora_fin) = '15:00:00');

INSERT INTO turno (hora_inicio, hora_fin)
SELECT '2000-01-01 15:00:00', '2000-01-01 16:00:00'
WHERE NOT EXISTS (SELECT 1 FROM turno WHERE TIME(hora_inicio) = '15:00:00' AND TIME(hora_fin) = '16:00:00');

INSERT INTO turno (hora_inicio, hora_fin)
SELECT '2000-01-01 16:00:00', '2000-01-01 17:00:00'
WHERE NOT EXISTS (SELECT 1 FROM turno WHERE TIME(hora_inicio) = '16:00:00' AND TIME(hora_fin) = '17:00:00');

INSERT INTO turno (hora_inicio, hora_fin)
SELECT '2000-01-01 17:00:00', '2000-01-01 18:00:00'
WHERE NOT EXISTS (SELECT 1 FROM turno WHERE TIME(hora_inicio) = '17:00:00' AND TIME(hora_fin) = '18:00:00');

INSERT INTO turno (hora_inicio, hora_fin)
SELECT '2000-01-01 18:00:00', '2000-01-01 19:00:00'
WHERE NOT EXISTS (SELECT 1 FROM turno WHERE TIME(hora_inicio) = '18:00:00' AND TIME(hora_fin) = '19:00:00');

INSERT INTO turno (hora_inicio, hora_fin)
SELECT '2000-01-01 19:00:00', '2000-01-01 20:00:00'
WHERE NOT EXISTS (SELECT 1 FROM turno WHERE TIME(hora_inicio) = '19:00:00' AND TIME(hora_fin) = '20:00:00');

INSERT INTO turno (hora_inicio, hora_fin)
SELECT '2000-01-01 20:00:00', '2000-01-01 21:00:00'
WHERE NOT EXISTS (SELECT 1 FROM turno WHERE TIME(hora_inicio) = '20:00:00' AND TIME(hora_fin) = '21:00:00');

INSERT INTO turno (hora_inicio, hora_fin)
SELECT '2000-01-01 21:00:00', '2000-01-01 22:00:00'
WHERE NOT EXISTS (SELECT 1 FROM turno WHERE TIME(hora_inicio) = '21:00:00' AND TIME(hora_fin) = '22:00:00');

INSERT INTO turno (hora_inicio, hora_fin)
SELECT '2000-01-01 22:00:00', '2000-01-01 23:00:00'
WHERE NOT EXISTS (SELECT 1 FROM turno WHERE TIME(hora_inicio) = '22:00:00' AND TIME(hora_fin) = '23:00:00');

COMMIT;
