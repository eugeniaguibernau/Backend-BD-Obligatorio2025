-- Migration: add id_facultad to sala and FK to facultad
-- Safe migration: add nullable column, then add foreign key constraint

ALTER TABLE sala
ADD COLUMN id_facultad INT NULL;

ALTER TABLE sala
ADD CONSTRAINT fk_sala_facultad FOREIGN KEY (id_facultad) REFERENCES facultad(id_facultad) ON DELETE SET NULL ON UPDATE CASCADE;

-- Note: Backfill is not performed automatically. You can set id_facultad for existing salas via UPDATE statements or via the admin UI.
