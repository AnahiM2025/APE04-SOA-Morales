import {
  iniciarSesion, cerrarSesion, haySesion, listarVehiculos, listarCompradores,
  registrarVenta, consultarVenta, nuevaClave,
} from './api.js';

const $ = (s) => document.querySelector(s);
const formLogin = $('#formLogin'), formVenta = $('#formVenta'), formConsulta = $('#formConsulta');
const mensaje = $('#mensaje'), resultado = $('#resultado'), detalle = $('#detalle');
const selVehiculo = $('#vehiculo'), selComprador = $('#comprador');
const contenedor = $('#vehiculos'), contador = $('#contador');
const paneles = ['#panelVenta', '#panelConsulta', '#panelVehiculos'].map($);
const moneda = new Intl.NumberFormat('es-EC', { style: 'currency', currency: 'USD' });

const poner = (el, texto, tipo = 'neutro') => { el.textContent = texto; el.className = `mensaje ${tipo}`; };
const txt = (v) => (v === null || v === undefined || v === '' ? '—' : String(v));
function el(etiqueta, clase, contenido) {
  const e = document.createElement(etiqueta);
  if (clase) e.className = clase;
  if (contenido !== undefined) e.textContent = String(contenido); // textContent: nunca HTML de la API
  return e;
}

function pintarVehiculos(lista) {
  contenedor.replaceChildren();
  contador.textContent = `${lista.length} vehículo${lista.length === 1 ? '' : 's'}`;
  if (!lista.length) { contenedor.append(el('p', 'vacio', 'No hay vehículos registrados.')); return; }
  for (const v of lista) {
    const t = el('article', 'vehiculo'), cab = el('div', 'vehiculo-cabecera'), enc = el('div');
    enc.append(el('h3', 'vehiculo-titulo', `${txt(v.marca)} ${txt(v.modelo)}`), el('span', 'vehiculo-id', `ID: ${txt(v.idVehiculo)}`));
    const est = txt(v.estado).toUpperCase();
    cab.append(enc, el('span', `estado ${est === 'DISPONIBLE' ? 'disponible' : est === 'VENDIDO' ? 'vendido' : ''}`, est));
    const g = el('div', 'datos');
    for (const [e, val, x] of [['Placa', txt(v.placa)], ['Año', txt(v.anio)], ['Color', txt(v.color)],
      ['Precio', Number.isFinite(Number(v.precio)) ? moneda.format(Number(v.precio)) : '—', 'dato-precio']]) {
      const d = el('div', x || ''); d.append(el('span', 'dato-etiqueta', e), el('span', 'dato-valor', val)); g.append(d);
    }
    t.append(cab, g); contenedor.append(t);
  }
}

function llenar(select, items, etiqueta, vacio) {
  select.replaceChildren();
  if (!items.length) { const o = el('option', '', vacio); o.value = ''; select.append(o); return; }
  for (const it of items) { const o = el('option', '', etiqueta(it)); o.value = it.id ?? it.idVehiculo; select.append(o); }
}

async function cargarDatos() {
  poner(mensaje, 'Cargando vehículos y compradores…');
  try {
    const [v, c] = await Promise.all([listarVehiculos(), listarCompradores()]);
    pintarVehiculos(v.vehiculos);
    llenar(selVehiculo, v.vehiculos.filter((x) => String(x.estado).toUpperCase() === 'DISPONIBLE'),
      (x) => `${x.marca} ${x.modelo} · ${x.placa} · ${moneda.format(Number(x.precio))}`, 'No hay vehículos disponibles');
    llenar(selComprador, c.compradores, (x) => `${x.nombre} · ${x.documento}`, 'No hay compradores registrados');
    poner(mensaje, `Sesión activa. ${v.vehiculos.length} vehículo(s), ${c.compradores.length} comprador(es).`, 'exito');
  } catch (e) {
    poner(mensaje, e.message, 'error');
    if (e.codigoHttp === 401) cerrar();
  }
}

function mostrarSesion(activa) {
  paneles.forEach((p) => { p.hidden = !activa; });
  $('#salir').hidden = !activa; $('#entrar').hidden = activa;
}

function cerrar() {
  cerrarSesion(); mostrarSesion(false); $('#clave').value = '';
  poner(mensaje, 'Sesión cerrada.');
}

formLogin.addEventListener('submit', async (ev) => {
  ev.preventDefault();
  $('#entrar').disabled = true; poner(mensaje, 'Iniciando sesión…');
  try {
    await iniciarSesion($('#usuario').value, $('#clave').value);
    $('#clave').value = ''; mostrarSesion(true); await cargarDatos();
  } catch (e) { poner(mensaje, e.message, 'error'); } finally { $('#entrar').disabled = false; }
});
$('#salir').addEventListener('click', cerrar);
$('#recargar').addEventListener('click', cargarDatos);

// Idempotencia: si el resultado de un intento es incierto (corte de red, 5xx) el reintento
// con la MISMA seleccion reutiliza la MISMA clave, de modo que nunca se duplica la venta.
let intento = null; // { firma, clave }
formVenta.addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const vId = selVehiculo.value, cId = selComprador.value;
  if (!vId || !cId) { poner(resultado, 'Seleccione un vehículo disponible y un comprador.', 'error'); return; }
  const firma = `${vId}:${cId}`;
  if (!intento || intento.firma !== firma) intento = { firma, clave: nuevaClave() };
  $('#vender').disabled = true; poner(resultado, 'Registrando venta…');
  try {
    const r = await registrarVenta(vId, cId, intento.clave);
    const v = r.venta;
    const nota = r.codigoHttp === 200 ? ' (operación repetida: se devolvió la misma venta)' : '';
    poner(resultado, `HTTP ${r.codigoHttp}: venta ${v.id} ${v.estado} · notificación ${v.notificacion} · ${moneda.format(Number(v.precioAcordado))}${nota}`,
      v.estado === 'COMPLETADA' ? 'exito' : 'neutro');
    $('#idVenta').value = v.id; intento = null; await cargarDatos();
  } catch (e) {
    if (!e.incierto) intento = null; // rechazo definitivo: la proxima vez se genera otra clave
    poner(resultado, e.incierto ? `${e.message} Puede reintentar: se conserva la clave para no duplicar la venta.` : e.message, 'error');
    if (e.codigoHttp === 401) cerrar();
  } finally { $('#vender').disabled = false; }
});

formConsulta.addEventListener('submit', async (ev) => {
  ev.preventDefault();
  try {
    const r = await consultarVenta($('#idVenta').value);
    poner(detalle, `HTTP ${r.codigoHttp}: venta ${r.venta.id} · ${r.venta.estado} · vehículo ${r.venta.vehiculoId} · notificación ${r.venta.notificacion}`, 'exito');
  } catch (e) { poner(detalle, e.message, 'error'); }
});

const conexion = $('#conexion');
const actualizar = () => { conexion.textContent = navigator.onLine ? 'Navegador conectado' : 'Sin conexión de red'; };
window.addEventListener('online', actualizar); window.addEventListener('offline', actualizar); actualizar();

mostrarSesion(haySesion());
if ('serviceWorker' in navigator && window.isSecureContext) {
  window.addEventListener('load', () => { navigator.serviceWorker.register('/sw.js').catch(() => {}); });
}
