-- Script para recrear la base de datos completa
-- Ejecuta este archivo en DataGrip o con el cliente mysql para recrear las tablas y datos de ejemplo.

DROP DATABASE IF EXISTS `proyecto`;

CREATE DATABASE `proyecto` DEFAULT CHARACTER SET utf8 COLLATE utf8_spanish_ci;
USE proyecto;


CREATE TABLE participante   (
                                        ci int,
                                        nombre VARCHAR(20),
                                        apellido VARCHAR(20),
                                        email VARCHAR(30) NOT NULL UNIQUE ,
                                        PRIMARY KEY (ci)
);

CREATE TABLE admin (
                                ci int,
                                nombre VARCHAR(20),
                                apellido VARCHAR(20),
                                email VARCHAR(30) NOT NULL,
                                PRIMARY KEY (ci)
);

CREATE TABLE login (
                                correo VARCHAR(30),
                                contraseña VARCHAR(128) NOT NULL UNIQUE,
                                PRIMARY KEY (correo),
                                FOREIGN KEY (correo) references participante(email)
);

CREATE TABLE facultad (
                                   id_facultad int AUTO_INCREMENT,
                                   nombre VARCHAR(20),
                                   PRIMARY KEY (id_facultad)
);


CREATE TABLE programa_academico (
                                             nombre_programa VARCHAR(20),
                                             id_facultad int,
                                             tipo enum ('grado', 'postgrado') NOT NULL,
                                             PRIMARY KEY (nombre_programa),
                                             FOREIGN KEY (id_facultad) references  facultad(id_facultad)
);

CREATE TABLE participante_programa_academico (
                                                         id_alumno_programa int AUTO_INCREMENT,
                                                         ci_participante int NOT NULL UNIQUE ,
                                                         nombre_programa VARCHAR(20) NOT NULL ,
                                                         rol enum ('alumno', 'docente', 'postgrado') NOT NULL ,
                                                         PRIMARY KEY (id_alumno_programa),
                                                         FOREIGN KEY (ci_participante) references  participante(ci),
                                                         FOREIGN KEY (nombre_programa) references programa_academico(nombre_programa)
);

CREATE TABLE edificio(
        nombre_edificio VARCHAR(20),
        direccion VARCHAR(50) NOT NULL,
        departamento VARCHAR(20),
        PRIMARY KEY (nombre_edificio)
);
CREATE TABLE sala(
    nombre_sala VARCHAR(20),
    edificio VARCHAR(20) NOT NULL,
    capacidad INT,
    tipo_sala enum('libre','posgrado','docente') NOT NULL,
    PRIMARY KEY (nombre_sala,edificio),
    FOREIGN KEY(edificio) REFERENCES edificio(nombre_edificio)
);


CREATE TABLE turno(
    id_turno INT AUTO_INCREMENT,
    hora_inicio DATETIME DEFAULT CURRENT_TIMESTAMP,
    hora_fin DATETIME NOT NULL,
    PRIMARY KEY (id_turno)
);

CREATE TABLE reserva(
    id_reserva INT AUTO_INCREMENT,
    nombre_sala VARCHAR(20) NOT NULL ,
    edificio VARCHAR(20) NOT NULL,
    fecha DATE NOT NULL,
    id_turno INT,
    estado enum('activa','cancelada','sin asistencia','asistida','finalizada') NOT NULL,
    PRIMARY KEY(id_reserva),
    FOREIGN KEY (nombre_sala,edificio) REFERENCES sala(nombre_sala,edificio),
    FOREIGN KEY (id_turno) REFERENCES  turno(id_turno)
);

CREATE TABLE reserva_participante(
    ci_participante INT,
    id_reserva INT AUTO_INCREMENT,
    fecha_solicitud_reserva DATE NOT NULL,
    asistencia BOOLEAN DEFAULT false,
    PRIMARY KEY (ci_participante, id_reserva),
    FOREIGN KEY (ci_participante) REFERENCES participante_programa_academico(ci_participante),
    FOREIGN KEY (id_reserva) REFERENCES  reserva(id_reserva)
);

CREATE TABLE sancion_participante(
    id_sancion INT AUTO_INCREMENT PRIMARY KEY,
    ci_participante INT,
    fecha_inicio DATE,
    fecha_fin DATE,
    creado_por VARCHAR(100) NULL,
    creado_en TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(100) NULL,
    updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY ux_sancion_unique (ci_participante, fecha_inicio, fecha_fin),
    FOREIGN KEY (ci_participante) REFERENCES participante_programa_academico(ci_participante)
);

-- Datos de ejemplo
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
