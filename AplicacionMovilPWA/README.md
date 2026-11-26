# PWA móvil · registro de ventas (único cliente que vende)

Flujo: usuario/contraseña → JWT (en memoria) → elegir vehículo DISPONIBLE y comprador → `POST /api/ventas` con `Idempotency-Key` → ver estado.

## Ejecución (PowerShell)
```powershell
$env:APP_CLIENT_ID     = "<client-id de la API Java>"
$env:APP_CLIENT_SECRET = "<client-secret de la API Java>"   # vive solo en el servidor Node, nunca en el navegador
$env:API_BASE_URL      = "http://127.0.0.1:8090"            # NGINX
npm start                                                    # http://localhost:5173
```
Pruebas: `npm test` (12 pruebas, sin dependencias).

## Decisiones de seguridad
- El navegador solo habla con `server.mjs` (mismo origen). Este reenvía una **lista cerrada** de rutas: `POST /oauth/token`, `GET /api/vehiculos`, `GET /api/compradores`, `POST /api/ventas`, `GET /api/ventas/{id}`.
- El `client-secret` se agrega en el servidor; el JWT no se guarda en almacenamiento del navegador.
- Reintentos: si el resultado de una venta es incierto (corte de red o 5xx) se reutiliza la misma `Idempotency-Key`; ante un rechazo definitivo (4xx) se genera otra.
