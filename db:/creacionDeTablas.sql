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
                                contraseña VARCHAR(20) NOT NULL UNIQUE,
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
                                                          rol enum ('alumno', 'docente') NOT NULL ,
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
    estado enum('activa','cancelada','sin asistencia','finalizada') NOT NULL,
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
    ci_participante INT,
    fecha_inicio DATE,
    fecha_fin DATE,
    PRIMARY KEY (ci_participante,fecha_inicio,fecha_fin),
    FOREIGN KEY (ci_participante) REFERENCES participante_programa_academico(ci_participante)
);
