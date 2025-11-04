USE proyecto;

-- Agregar Ana Silva al login como admin
-- Email: ana.silva@ucu.edu.uy
-- Contraseña: AnaSilva123! (hasheada con bcrypt)
INSERT INTO login (correo, contraseña) 
VALUES ('ana.silva@ucu.edu.uy', '$2b$12$FejbkwVJRhvTEow4V05GIuKamP.zcKQAMwLSv3urDzMGIpKw.Im6y');

-- Verificar que se agregó correctamente
SELECT * FROM login WHERE correo = 'ana.silva@ucu.edu.uy';
