ALTER TABLE turno 
MODIFY hora_inicio TIME NOT NULL,
MODIFY hora_fin TIME NOT NULL;

INSERT INTO turno (hora_inicio, hora_fin) 
SELECT '18:00:00', '20:00:00'
WHERE NOT EXISTS (SELECT 1 FROM turno WHERE hora_inicio='18:00:00' AND hora_fin='20:00:00');

UPDATE turno SET hora_inicio = '08:00:00', hora_fin = '10:00:00' WHERE id_turno = 1;
UPDATE turno SET hora_inicio = '10:00:00', hora_fin = '12:00:00' WHERE id_turno = 2;
UPDATE turno SET hora_inicio = '12:00:00', hora_fin = '14:00:00' WHERE id_turno = 3;
UPDATE turno SET hora_inicio = '14:00:00', hora_fin = '16:00:00' WHERE id_turno = 4;
UPDATE turno SET hora_inicio = '16:00:00', hora_fin = '18:00:00' WHERE id_turno = 5;
UPDATE turno SET hora_inicio = '18:00:00', hora_fin = '20:00:00' WHERE id_turno = 6;
