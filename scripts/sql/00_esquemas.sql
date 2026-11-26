-- Un MySQL, tres esquemas logicos separados (cada servicio usa solo el suyo).
-- Las TABLAS las crean los propios servicios:
--   venta_vehiculos           -> API Java de vehiculos (Hibernate, ddl-auto=update)
--   ventas_compradores        -> API Python (alembic upgrade head)
--   notificaciones_vehiculos  -> servicio de notificaciones (Hibernate, ddl-auto=update)
CREATE DATABASE IF NOT EXISTS venta_vehiculos          CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS ventas_compradores       CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS notificaciones_vehiculos CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
