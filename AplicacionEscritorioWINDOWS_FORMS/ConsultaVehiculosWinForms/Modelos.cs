namespace ConsultaVehiculosWinForms;

// DTOs que coinciden con el JSON de las APIs (camelCase; System.Text.Json en modo Web).
public sealed class Vehiculo
{
    public int IdVehiculo { get; set; }
    public string? Marca { get; set; }
    public string? Modelo { get; set; }
    public string? Placa { get; set; }
    public string? Chasis { get; set; }
    public int Anio { get; set; }
    public string? Color { get; set; }
    public decimal Precio { get; set; }
    public string? Estado { get; set; }
}

public sealed record VehiculoNuevo(string Marca, string Modelo, string Placa, string Chasis,
                                   int Anio, string? Color, decimal Precio);

public sealed class Comprador
{
    public int Id { get; set; }
    public string? Documento { get; set; }
    public string? Nombre { get; set; }
    public string? Correo { get; set; }
}

public sealed record CompradorNuevo(string Documento, string Nombre, string Correo);

public sealed class Venta
{
    public int Id { get; set; }
    public int VehiculoId { get; set; }
    public int CompradorId { get; set; }
    public decimal? PrecioAcordado { get; set; }
    public string? Moneda { get; set; }
    public string? Estado { get; set; }
    public string? Notificacion { get; set; }
}

public sealed class TokenRespuesta
{
    public string? Access_token { get; set; }
    public long Expires_in { get; set; }
}
