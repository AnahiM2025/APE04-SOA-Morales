using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;

namespace ConsultaVehiculosWinForms;

public sealed class ApiException : Exception
{
    public int? Codigo { get; }
    public ApiException(string mensaje, int? codigo = null) : base(mensaje) => Codigo = codigo;
}

/// <summary>
/// Cliente REST de Windows Forms. Habla solo con NGINX (puerto 8090). El JWT vive en memoria.
/// Credenciales OAuth del cliente: variables de entorno APP_CLIENT_ID y APP_CLIENT_SECRET
/// (nunca en el codigo ni en el repositorio).
/// </summary>
public sealed class ApiClient : IDisposable
{
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);
    private readonly HttpClient _http;
    private string? _jwt;

    public ApiClient()
    {
        var baseUrl = Environment.GetEnvironmentVariable("API_BASE_URL") ?? "http://127.0.0.1:8090";
        _http = new HttpClient { BaseAddress = new Uri(baseUrl.TrimEnd('/') + "/"), Timeout = TimeSpan.FromSeconds(15) };
    }

    public bool HaySesion => !string.IsNullOrEmpty(_jwt);
    public void CerrarSesion() => _jwt = null;

    public async Task IniciarSesionAsync(string usuario, string clave)
    {
        var id = Environment.GetEnvironmentVariable("APP_CLIENT_ID");
        var secreto = Environment.GetEnvironmentVariable("APP_CLIENT_SECRET");
        if (string.IsNullOrEmpty(id) || string.IsNullOrEmpty(secreto))
            throw new ApiException("Defina las variables de entorno APP_CLIENT_ID y APP_CLIENT_SECRET.");

        using var req = new HttpRequestMessage(HttpMethod.Post, "oauth/token")
        {
            Content = new FormUrlEncodedContent(new Dictionary<string, string>
            {
                ["grant_type"] = "password", ["username"] = usuario, ["password"] = clave,
            }),
        };
        req.Headers.Authorization = new AuthenticationHeaderValue("Basic",
            Convert.ToBase64String(Encoding.UTF8.GetBytes($"{id}:{secreto}")));

        var token = await EnviarAsync<TokenRespuesta>(req, autenticado: false, traducir401: "Usuario o contraseña incorrectos.");
        if (string.IsNullOrEmpty(token?.Access_token)) throw new ApiException("La respuesta no contiene un token.");
        _jwt = token.Access_token;
    }

    public Task<List<Vehiculo>> ListarVehiculosAsync(string? marca = null)
    {
        var ruta = string.IsNullOrWhiteSpace(marca) ? "api/vehiculos" : $"api/vehiculos?marca={Uri.EscapeDataString(marca.Trim())}";
        return ObtenerListaAsync<Vehiculo>(ruta);
    }

    public Task<Vehiculo?> CrearVehiculoAsync(VehiculoNuevo v) => PostAsync<VehiculoNuevo, Vehiculo>("api/vehiculos", v);
    public Task<List<Comprador>> ListarCompradoresAsync() => ObtenerListaAsync<Comprador>("api/compradores");
    public Task<Comprador?> CrearCompradorAsync(CompradorNuevo c) => PostAsync<CompradorNuevo, Comprador>("api/compradores", c);

    public Task<List<Venta>> ListarVentasAsync(string? estado = null) =>
        ObtenerListaAsync<Venta>(string.IsNullOrEmpty(estado) ? "api/ventas" : $"api/ventas?estado={Uri.EscapeDataString(estado)}");

    private async Task<List<T>> ObtenerListaAsync<T>(string ruta)
    {
        using var req = new HttpRequestMessage(HttpMethod.Get, ruta);
        return await EnviarAsync<List<T>>(req) ?? new List<T>();
    }

    private async Task<TOut?> PostAsync<TIn, TOut>(string ruta, TIn cuerpo)
    {
        using var req = new HttpRequestMessage(HttpMethod.Post, ruta)
        {
            Content = new StringContent(JsonSerializer.Serialize(cuerpo, Json), Encoding.UTF8, "application/json"),
        };
        return await EnviarAsync<TOut>(req);
    }

    private async Task<T?> EnviarAsync<T>(HttpRequestMessage req, bool autenticado = true, string? traducir401 = null)
    {
        if (autenticado && _jwt != null) req.Headers.Authorization = new AuthenticationHeaderValue("Bearer", _jwt);
        req.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));
        HttpResponseMessage resp;
        try { resp = await _http.SendAsync(req); }
        catch (Exception ex) when (ex is HttpRequestException or TaskCanceledException)
        {
            throw new ApiException("No se pudo conectar con el servicio (NGINX/backend no disponible).");
        }
        using (resp)
        {
            var cuerpo = await resp.Content.ReadAsStringAsync();
            if (!resp.IsSuccessStatusCode)
            {
                var codigo = (int)resp.StatusCode;
                if ((codigo == 400 || codigo == 401) && traducir401 != null) throw new ApiException(traducir401, codigo);
                string msg = codigo switch
                {
                    401 => "HTTP 401: sesión inválida o vencida. Inicie sesión de nuevo.",
                    403 => "HTTP 403: su usuario no tiene permiso para esta operación.",
                    409 => "HTTP 409: conflicto (dato duplicado).",
                    422 or 400 => "HTTP " + codigo + ": datos inválidos. " + Detalle(cuerpo),
                    502 or 503 or 504 => "HTTP " + codigo + ": backend no disponible.",
                    _ => "HTTP " + codigo + ": operación no completada. " + Detalle(cuerpo),
                };
                throw new ApiException(msg.Trim(), codigo);
            }
            if (string.IsNullOrWhiteSpace(cuerpo)) return default;
            try { return JsonSerializer.Deserialize<T>(cuerpo, Json); }
            catch (JsonException) { throw new ApiException("La API devolvió una respuesta que no es JSON válido."); }
        }
    }

    private static string Detalle(string cuerpo)
    {
        try
        {
            using var doc = JsonDocument.Parse(cuerpo);
            foreach (var clave in new[] { "mensaje", "message", "detail", "error" })
                if (doc.RootElement.ValueKind == JsonValueKind.Object && doc.RootElement.TryGetProperty(clave, out var v)
                    && v.ValueKind == JsonValueKind.String) return v.GetString() ?? "";
        }
        catch (JsonException) { }
        return "";
    }

    public void Dispose() => _http.Dispose();
}
