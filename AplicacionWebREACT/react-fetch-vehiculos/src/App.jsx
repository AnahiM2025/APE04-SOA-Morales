import { useCallback, useMemo, useState } from 'react';
import './App.css';
import { cerrarSesion, haySesion, iniciarSesion, listarVehiculos, listarVentas } from './api/api.js';

const dinero = new Intl.NumberFormat('es-EC', { style: 'currency', currency: 'USD' });
const mostrar = (v) => (v === null || v === undefined || v === '' ? '—' : String(v));
const precio = (v) => (Number.isFinite(Number(v)) && v !== null && v !== '' ? dinero.format(Number(v)) : '—');

function Login({ alEntrar }) {
  const [usuario, setUsuario] = useState('');
  const [clave, setClave] = useState('');
  const [error, setError] = useState('');
  const [cargando, setCargando] = useState(false);

  async function enviar(e) {
    e.preventDefault();
    setCargando(true); setError('');
    try { await iniciarSesion(usuario, clave); setClave(''); alEntrar(); }
    catch (err) { setError(err.message); }
    finally { setCargando(false); }
  }

  return (
    <section className="panel">
      <p className="marca-producto">Cliente web · solo consulta</p>
      <h1>Consulta de vehículos y ventas</h1>
      <form onSubmit={enviar}>
        <label htmlFor="usuario">Usuario</label>
        <input id="usuario" value={usuario} onChange={(e) => setUsuario(e.target.value)} autoComplete="username" autoCapitalize="none" />
        <label htmlFor="clave">Contraseña</label>
        <input id="clave" type="password" value={clave} onChange={(e) => setClave(e.target.value)} autoComplete="current-password" />
        <div className="acciones"><button type="submit" disabled={cargando}>{cargando ? 'Entrando…' : 'Iniciar sesión'}</button></div>
      </form>
      {error && <p className="nota error" role="alert">{error}</p>}
      <p className="ayuda">El token permanece en memoria; no se guarda en el navegador. Este cliente no registra ventas.</p>
    </section>
  );
}

function Vehiculos({ alExpirar }) {
  const [marca, setMarca] = useState('');
  const [datos, setDatos] = useState(null);
  const [seleccionado, setSeleccionado] = useState(null);
  const [estado, setEstado] = useState({ cargando: false, error: '' });

  const consultar = useCallback(async (filtro) => {
    setEstado({ cargando: true, error: '' }); setSeleccionado(null);
    try { setDatos(await listarVehiculos(filtro)); setEstado({ cargando: false, error: '' }); }
    catch (e) { setDatos(null); setEstado({ cargando: false, error: e.message }); if (e.codigoHttp === 401) alExpirar(); }
  }, [alExpirar]);

  return (
    <section className="panel">
      <h2 className="titulo-listado">Vehículos <span className="contador">{datos ? `${datos.length} resultado(s)` : ''}</span></h2>
      <form className="linea-token" onSubmit={(e) => { e.preventDefault(); consultar(marca); }}>
        <input aria-label="Filtrar por marca" placeholder="Filtrar por marca (ej. Kia)" value={marca} onChange={(e) => setMarca(e.target.value)} />
        <button type="submit" disabled={estado.cargando}>Consultar</button>
        <button type="button" className="secundario" disabled={estado.cargando} onClick={() => { setMarca(''); consultar(''); }}>Todos</button>
      </form>
      {estado.cargando && <p className="nota" role="status">Consultando vehículos…</p>}
      {estado.error && <p className="nota error" role="alert">{estado.error}</p>}
      {datos && datos.length === 0 && <p className="sin-datos">No hay vehículos para ese filtro.</p>}
      {datos && datos.length > 0 && (
        <div className="tabla-scroll">
          <table>
            <thead><tr><th>ID</th><th>Marca</th><th>Modelo</th><th>Placa</th><th>Año</th><th>Precio</th><th>Estado</th></tr></thead>
            <tbody>
              {datos.map((v) => (
                <tr key={v.idVehiculo}>
                  <td><button type="button" className="enlace-id" onClick={() => setSeleccionado(v)}>{v.idVehiculo}</button></td>
                  <td>{mostrar(v.marca)}</td><td>{mostrar(v.modelo)}</td><td>{mostrar(v.placa)}</td>
                  <td>{mostrar(v.anio)}</td><td>{precio(v.precio)}</td><td>{mostrar(v.estado)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {seleccionado && (
        <aside className="detalle" aria-label="Detalle del vehículo">
          <h3>{mostrar(seleccionado.marca)} {mostrar(seleccionado.modelo)}</h3>
          <dl>
            {[['ID', seleccionado.idVehiculo], ['Placa', seleccionado.placa], ['Chasis', seleccionado.chasis], ['Año', seleccionado.anio],
              ['Color', seleccionado.color], ['Precio', precio(seleccionado.precio)], ['Estado', seleccionado.estado]].map(([k, v]) => (
              <div key={k}><dt>{k}</dt><dd>{mostrar(v)}</dd></div>
            ))}
          </dl>
        </aside>
      )}
    </section>
  );
}

function Ventas({ alExpirar }) {
  const [filtro, setFiltro] = useState('');
  const [datos, setDatos] = useState(null);
  const [estado, setEstado] = useState({ cargando: false, error: '' });

  const consultar = useCallback(async (f) => {
    setEstado({ cargando: true, error: '' });
    try { setDatos(await listarVentas(f)); setEstado({ cargando: false, error: '' }); }
    catch (e) { setDatos(null); setEstado({ cargando: false, error: e.message }); if (e.codigoHttp === 401) alExpirar(); }
  }, [alExpirar]);

  // Panel web: resumen calculado solo con los datos devueltos por la API.
  const resumen = useMemo(() => {
    if (!datos) return null;
    const completadas = datos.filter((v) => v.estado === 'COMPLETADA');
    return { total: datos.length, completadas: completadas.length,
      monto: completadas.reduce((s, v) => s + (Number(v.precioAcordado) || 0), 0) };
  }, [datos]);

  return (
    <section className="panel">
      <h2 className="titulo-listado">Ventas <span className="contador">{datos ? `${datos.length} resultado(s)` : ''}</span></h2>
      <form className="linea-token" onSubmit={(e) => { e.preventDefault(); consultar(filtro); }}>
        <select aria-label="Filtrar por estado" value={filtro} onChange={(e) => setFiltro(e.target.value)}>
          <option value="">Todos los estados</option>
          {['COMPLETADA', 'PENDIENTE', 'EN_REVISION', 'FALLIDA'].map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <button type="submit" disabled={estado.cargando}>Consultar ventas</button>
      </form>
      {estado.cargando && <p className="nota" role="status">Consultando ventas…</p>}
      {estado.error && <p className="nota error" role="alert">{estado.error}</p>}
      {resumen && (
        <p className="nota" role="status">Ventas: {resumen.total} · completadas: {resumen.completadas} · monto completado: {dinero.format(resumen.monto)}</p>
      )}
      {datos && datos.length === 0 && <p className="sin-datos">No hay ventas para ese filtro.</p>}
      {datos && datos.length > 0 && (
        <div className="tabla-scroll">
          <table>
            <thead><tr><th>ID</th><th>Vehículo</th><th>Comprador</th><th>Precio</th><th>Estado</th><th>Notificación</th></tr></thead>
            <tbody>
              {datos.map((v) => (
                <tr key={v.id}><td>{v.id}</td><td>{mostrar(v.vehiculoId)}</td><td>{mostrar(v.compradorId)}</td>
                  <td>{precio(v.precioAcordado)}</td><td>{mostrar(v.estado)}</td><td>{mostrar(v.notificacion)}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export default function App() {
  const [activa, setActiva] = useState(haySesion());
  const [vista, setVista] = useState('vehiculos');
  const salir = useCallback(() => { cerrarSesion(); setActiva(false); }, []);

  return (
    <main className="contenedor">
      {!activa ? <Login alEntrar={() => setActiva(true)} /> : (
        <>
          <header className="cabecera">
            <nav className="acciones" aria-label="Secciones">
              <button type="button" className={vista === 'vehiculos' ? '' : 'secundario'} onClick={() => setVista('vehiculos')}>Vehículos</button>
              <button type="button" className={vista === 'ventas' ? '' : 'secundario'} onClick={() => setVista('ventas')}>Ventas</button>
              <button type="button" className="secundario" onClick={salir}>Cerrar sesión</button>
            </nav>
          </header>
          {vista === 'vehiculos' ? <Vehiculos alExpirar={salir} /> : <Ventas alExpirar={salir} />}
        </>
      )}
    </main>
  );
}
