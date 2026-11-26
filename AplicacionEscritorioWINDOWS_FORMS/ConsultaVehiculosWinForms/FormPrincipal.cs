using System.ComponentModel;
using System.Globalization;

namespace ConsultaVehiculosWinForms;

/// <summary>
/// Cliente de administracion: crea vehiculos y compradores; lista vehiculos, compradores y ventas.
/// NO registra ventas (eso es exclusivo de la PWA). La interfaz se construye por codigo.
/// </summary>
public sealed class FormPrincipal : Form
{
    private readonly ApiClient _api = new();
    private readonly TextBox _usuario = new() { Width = 130 };
    private readonly TextBox _clave = new() { Width = 130, UseSystemPasswordChar = true };
    private readonly Button _entrar = new() { Text = "Iniciar sesión", AutoSize = true };
    private readonly Button _salir = new() { Text = "Cerrar sesión", AutoSize = true, Enabled = false };
    private readonly Label _estado = new() { Dock = DockStyle.Bottom, Height = 28, Padding = new Padding(8, 6, 0, 0), Text = "Inicie sesión para continuar." };
    private readonly TabControl _tabs = new() { Dock = DockStyle.Fill, Enabled = false };

    private readonly DataGridView _gVeh = Grid(), _gCom = Grid(), _gVen = Grid();
    private readonly TextBox _fMarca = new(), _vMarca = new(), _vModelo = new(), _vPlaca = new(), _vChasis = new(), _vAnio = new(), _vColor = new(), _vPrecio = new();
    private readonly TextBox _cDoc = new(), _cNombre = new(), _cCorreo = new();
    private readonly ComboBox _fEstado = new() { DropDownStyle = ComboBoxStyle.DropDownList, Width = 160 };

    public FormPrincipal()
    {
        Text = "Administración de vehículos — Windows Forms";
        Width = 1050; Height = 700; StartPosition = FormStartPosition.CenterScreen;

        var barra = new FlowLayoutPanel { Dock = DockStyle.Top, Height = 44, Padding = new Padding(8, 8, 0, 0) };
        barra.Controls.AddRange(new Control[] { new Label { Text = "Usuario", AutoSize = true, Padding = new Padding(0, 5, 0, 0) }, _usuario,
            new Label { Text = "Contraseña", AutoSize = true, Padding = new Padding(0, 5, 0, 0) }, _clave, _entrar, _salir });

        _tabs.TabPages.Add(PestanaVehiculos());
        _tabs.TabPages.Add(PestanaCompradores());
        _tabs.TabPages.Add(PestanaVentas());

        Controls.Add(_tabs); Controls.Add(barra); Controls.Add(_estado);
        AcceptButton = _entrar;

        _entrar.Click += async (_, _) => await Ejecutar(Entrar);
        _salir.Click += (_, _) => Salir();
        FormClosed += (_, _) => _api.Dispose();
    }

    private static DataGridView Grid() => new()
    {
        Dock = DockStyle.Fill, ReadOnly = true, AllowUserToAddRows = false, AllowUserToDeleteRows = false,
        AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill, SelectionMode = DataGridViewSelectionMode.FullRowSelect,
        RowHeadersVisible = false,
    };

    private static Control Fila(string etiqueta, Control c)
    {
        c.Width = 140;
        var p = new FlowLayoutPanel { AutoSize = true, FlowDirection = FlowDirection.TopDown, Margin = new Padding(4) };
        p.Controls.Add(new Label { Text = etiqueta, AutoSize = true });
        p.Controls.Add(c);
        return p;
    }

    private TabPage PestanaVehiculos()
    {
        var pag = new TabPage("Vehículos");
        var filtro = new FlowLayoutPanel { Dock = DockStyle.Top, Height = 40, Padding = new Padding(4) };
        var btnBuscar = new Button { Text = "Buscar por marca", AutoSize = true };
        var btnTodos = new Button { Text = "Todos", AutoSize = true };
        filtro.Controls.AddRange(new Control[] { new Label { Text = "Marca", AutoSize = true, Padding = new Padding(0, 6, 0, 0) }, _fMarca, btnBuscar, btnTodos });
        btnBuscar.Click += async (_, _) => await Ejecutar(() => CargarVehiculos(_fMarca.Text));
        btnTodos.Click += async (_, _) => { _fMarca.Clear(); await Ejecutar(() => CargarVehiculos(null)); };

        var form = new FlowLayoutPanel { Dock = DockStyle.Bottom, Height = 95, Padding = new Padding(4) };
        var btnCrear = new Button { Text = "Crear vehículo", AutoSize = true, Margin = new Padding(8, 22, 0, 0) };
        form.Controls.AddRange(new[] { Fila("Marca", _vMarca), Fila("Modelo", _vModelo), Fila("Placa", _vPlaca), Fila("Chasis (17)", _vChasis),
            Fila("Año", _vAnio), Fila("Color", _vColor), Fila("Precio", _vPrecio), btnCrear });
        btnCrear.Click += async (_, _) => await Ejecutar(CrearVehiculo);

        pag.Controls.Add(_gVeh); pag.Controls.Add(filtro); pag.Controls.Add(form);
        return pag;
    }

    private TabPage PestanaCompradores()
    {
        var pag = new TabPage("Compradores");
        var form = new FlowLayoutPanel { Dock = DockStyle.Bottom, Height = 95, Padding = new Padding(4) };
        var btnCrear = new Button { Text = "Crear comprador", AutoSize = true, Margin = new Padding(8, 22, 0, 0) };
        var btnAct = new Button { Text = "Actualizar lista", AutoSize = true, Margin = new Padding(8, 22, 0, 0) };
        form.Controls.AddRange(new Control[] { Fila("Documento", _cDoc), Fila("Nombre", _cNombre), Fila("Correo", _cCorreo), btnCrear, btnAct });
        btnCrear.Click += async (_, _) => await Ejecutar(CrearComprador);
        btnAct.Click += async (_, _) => await Ejecutar(CargarCompradores);
        pag.Controls.Add(_gCom); pag.Controls.Add(form);
        return pag;
    }

    private TabPage PestanaVentas()
    {
        var pag = new TabPage("Ventas (solo lectura)");
        _fEstado.Items.AddRange(new object[] { "(todos)", "COMPLETADA", "PENDIENTE", "EN_REVISION", "FALLIDA" });
        _fEstado.SelectedIndex = 0;
        var barra = new FlowLayoutPanel { Dock = DockStyle.Top, Height = 40, Padding = new Padding(4) };
        var btn = new Button { Text = "Listar ventas", AutoSize = true };
        barra.Controls.AddRange(new Control[] { new Label { Text = "Estado", AutoSize = true, Padding = new Padding(0, 6, 0, 0) }, _fEstado, btn });
        btn.Click += async (_, _) => await Ejecutar(CargarVentas);
        pag.Controls.Add(_gVen); pag.Controls.Add(barra);
        return pag;
    }

    // ---- acciones ----
    private async Task Entrar()
    {
        if (string.IsNullOrWhiteSpace(_usuario.Text) || string.IsNullOrEmpty(_clave.Text))
        { Mensaje("Ingrese usuario y contraseña.", true); return; }
        await _api.IniciarSesionAsync(_usuario.Text.Trim(), _clave.Text);
        _clave.Clear(); _tabs.Enabled = true; _salir.Enabled = true; _entrar.Enabled = false;
        await CargarVehiculos(null); await CargarCompradores();
        Mensaje("Sesión iniciada.", false);
    }

    private void Salir()
    {
        _api.CerrarSesion(); _tabs.Enabled = false; _salir.Enabled = false; _entrar.Enabled = true;
        _gVeh.DataSource = _gCom.DataSource = _gVen.DataSource = null;
        Mensaje("Sesión cerrada.", false);
    }

    private async Task CargarVehiculos(string? marca)
    {
        var l = await _api.ListarVehiculosAsync(marca);
        _gVeh.DataSource = new BindingList<Vehiculo>(l);
        Mensaje($"{l.Count} vehículo(s).", false);
    }

    private async Task CargarCompradores()
    {
        var l = await _api.ListarCompradoresAsync();
        _gCom.DataSource = new BindingList<Comprador>(l);
        Mensaje($"{l.Count} comprador(es).", false);
    }

    private async Task CargarVentas()
    {
        var e = _fEstado.SelectedIndex <= 0 ? null : _fEstado.SelectedItem?.ToString();
        var l = await _api.ListarVentasAsync(e);
        _gVen.DataSource = new BindingList<Venta>(l);
        Mensaje($"{l.Count} venta(s).", false);
    }

    private async Task CrearVehiculo()
    {
        if (_vMarca.Text.Trim() == "" || _vModelo.Text.Trim() == "" || _vPlaca.Text.Trim() == "")
        { Mensaje("Marca, modelo y placa son obligatorios.", true); return; }
        if (_vChasis.Text.Trim().Length != 17) { Mensaje("El chasis debe tener exactamente 17 caracteres.", true); return; }
        if (!int.TryParse(_vAnio.Text.Trim(), out var anio) || anio < 1900 || anio > DateTime.Now.Year + 1)
        { Mensaje("Año inválido.", true); return; }
        if (!decimal.TryParse(_vPrecio.Text.Trim().Replace(',', '.'), NumberStyles.Number, CultureInfo.InvariantCulture, out var precio) || precio <= 0)
        { Mensaje("El precio debe ser un número mayor que cero.", true); return; }

        var v = await _api.CrearVehiculoAsync(new VehiculoNuevo(_vMarca.Text.Trim(), _vModelo.Text.Trim(), _vPlaca.Text.Trim(),
            _vChasis.Text.Trim(), anio, string.IsNullOrWhiteSpace(_vColor.Text) ? null : _vColor.Text.Trim(), precio));
        foreach (var t in new[] { _vMarca, _vModelo, _vPlaca, _vChasis, _vAnio, _vColor, _vPrecio }) t.Clear();
        await CargarVehiculos(null);
        Mensaje($"Vehículo creado (ID {v?.IdVehiculo}).", false);
    }

    private async Task CrearComprador()
    {
        if (_cDoc.Text.Trim().Length < 3 || _cNombre.Text.Trim().Length < 2 || !_cCorreo.Text.Contains('@'))
        { Mensaje("Documento (mín. 3), nombre (mín. 2) y correo válido son obligatorios.", true); return; }
        var c = await _api.CrearCompradorAsync(new CompradorNuevo(_cDoc.Text.Trim(), _cNombre.Text.Trim(), _cCorreo.Text.Trim()));
        _cDoc.Clear(); _cNombre.Clear(); _cCorreo.Clear();
        await CargarCompradores();
        Mensaje($"Comprador creado (ID {c?.Id}).", false);
    }

    // Envoltura comun: bloquea la UI, muestra errores HTTP legibles y cierra sesion si vence (401).
    private async Task Ejecutar(Func<Task> accion)
    {
        UseWaitCursor = true;
        try { await accion(); }
        catch (ApiException ex)
        {
            Mensaje(ex.Message, true);
            if (ex.Codigo == 401 && _api.HaySesion) Salir();
        }
        finally { UseWaitCursor = false; }
    }

    private void Mensaje(string texto, bool error)
    {
        _estado.Text = texto;
        _estado.ForeColor = error ? Color.Firebrick : SystemColors.ControlText;
    }
}
