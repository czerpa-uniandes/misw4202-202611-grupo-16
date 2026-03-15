-- Seed mínimo ASR-19
INSERT INTO clientes (id, nombre, email, activo)
VALUES
  (1, 'Ana Torres', 'ana@example.com', true),
  (2, 'Carlos Ruiz', 'carlos@example.com', true),
  (3, 'Cliente Inactivo', 'inactivo@example.com', false)
ON CONFLICT (id) DO NOTHING;

INSERT INTO habitaciones (id, nombre, precio_base, disponible)
VALUES
  (101, 'Suite 101', 120000, true),
  (102, 'Deluxe 102', 180000, true)
ON CONFLICT (id) DO NOTHING;
