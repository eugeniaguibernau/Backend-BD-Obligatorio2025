USE proyecto;
-- Rename the login column to a temporary ASCII name and back to force metadata re-encoding
ALTER TABLE `login` CHANGE `contraseña` `__tmp_contrasena` VARCHAR(100) NOT NULL UNIQUE;
ALTER TABLE `login` CHANGE `__tmp_contrasena` `contraseña` VARCHAR(100) NOT NULL UNIQUE;
