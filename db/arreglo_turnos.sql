ALTER TABLE turno 
MODIFY hora_inicio TIME NOT NULL,
MODIFY hora_fin TIME NOT NULL;

UPDATE turno SET hora_inicio = '08:00:00', hora_fin = '09:00:00' WHERE id_turno = 1;
UPDATE turno SET hora_inicio = '09:00:00', hora_fin = '10:00:00' WHERE id_turno = 2;
UPDATE turno SET hora_inicio = '10:00:00', hora_fin = '11:00:00' WHERE id_turno = 3;
UPDATE turno SET hora_inicio = '11:00:00', hora_fin = '12:00:00' WHERE id_turno = 4;
UPDATE turno SET hora_inicio = '12:00:00', hora_fin = '13:00:00' WHERE id_turno = 5;
UPDATE turno SET hora_inicio = '13:00:00', hora_fin = '14:00:00' WHERE id_turno = 6;

INSERT IGNORE INTO turno (hora_inicio, hora_fin)
VALUES ('14:00:00', '15:00:00'),('15:00:00', '16:00:00'),('16:00:00', '17:00:00'),('17:00:00', '18:00:00'),('18:00:00', '19:00:00'),('19:00:00', '20:00:00'),('20:00:00', '21:00:00'),('21:00:00', '22:00:00'),('22:00:00', '23:00:00');

INSERT INTO participante (email, nombre, apellido, ci)
VALUES
 ('ana.admin@ucu.edu.uy',   'admin', 'ANA',   12345668),
 ('pedro.admin@ucu.edu.uy', 'admin', 'PEDRO', 23456789),
 ('laura.admin@ucu.edu.uy', 'admin', 'LAURA', 34567890);

INSERT INTO login (correo,contrasena)
VALUES
 ('ana.admin@ucu.edu.uy',   'admin'),
 ('pedro.admin@ucu.edu.uy', 'admin'),
 ('laura.admin@ucu.edu.uy', 'admin');
