# Windows Forms · administración (crea y lista; NO vende)

Funciones: login (JWT en memoria), crear vehículos, crear compradores, listar vehículos (filtro por marca), compradores y ventas (solo lectura).

```powershell
$env:APP_CLIENT_ID     = "<client-id de la API Java>"
$env:APP_CLIENT_SECRET = "<client-secret de la API Java>"
$env:API_BASE_URL      = "http://127.0.0.1:8090"   # NGINX
dotnet run --project ConsultaVehiculosWinForms
```
Usar un usuario con rol ADMIN u OPERADOR para crear. Un usuario CONSULTA solo puede listar (el backend responde 403 al crear).
La interfaz está construida por código (no hay `.Designer.cs`); el registro de ventas no existe en esta aplicación.
