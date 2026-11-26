-- Consultas de verificacion para las capturas de MySQL (P02, P04, P09, P22).
SELECT id_vehiculo, marca, modelo, placa, estado FROM venta_vehiculos.vehiculos ORDER BY id_vehiculo DESC LIMIT 10;
SELECT id, documento, nombre FROM ventas_compradores.compradores ORDER BY id DESC LIMIT 10;
SELECT id, vehiculo_id, comprador_id, estado, notificacion FROM ventas_compradores.ventas ORDER BY id DESC LIMIT 10;
SELECT id, evento_id, tipo, venta_id, vehiculo_id, creada_en FROM notificaciones_vehiculos.notificaciones ORDER BY id DESC LIMIT 10;
-- No debe haber eventos duplicados (P22): esta consulta debe devolver 0 filas.
SELECT evento_id, COUNT(*) c FROM notificaciones_vehiculos.notificaciones GROUP BY evento_id HAVING c > 1;
