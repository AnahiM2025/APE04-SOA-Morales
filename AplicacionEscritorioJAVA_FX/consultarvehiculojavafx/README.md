# JavaFX · notificaciones de venta

Login (JWT en memoria) y tabla de notificaciones. Consulta `GET /api/notificaciones` cada 4 s y pide solo las nuevas (`despuesDeId`).
Si el servicio cae muestra el error y reintenta; si el JWT vence (401) cierra la sesión.

```powershell
$env:APP_CLIENT_ID     = "<client-id de la API Java>"
$env:APP_CLIENT_SECRET = "<client-secret de la API Java>"
$env:API_BASE_URL      = "http://127.0.0.1:8090"   # NGINX
mvn clean javafx:run
```
