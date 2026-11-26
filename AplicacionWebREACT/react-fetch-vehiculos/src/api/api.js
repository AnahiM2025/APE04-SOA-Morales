// Cliente REST de React. El JWT vive solo en memoria (variable del modulo).
let jwt = '';
export const haySesion = () => Boolean(jwt);
export const cerrarSesion = () => { jwt = ''; };

const MENSAJES = {
  401: 'HTTP 401: sesión ausente, inválida o vencida.',
  403: 'HTTP 403: su usuario no tiene permiso para consultar.',
  404: 'HTTP 404: recurso no encontrado.',
  502: 'HTTP 502: el backend no está disponible.',
  503: 'HTTP 503: servicio no disponible.',
  504: 'HTTP 504: el backend no respondió a tiempo.',
};

async function pedir(ruta, opciones = {}) {
  const headers = { Accept: 'application/json', ...(opciones.headers || {}) };
  if (jwt && !opciones.sinToken) headers.Authorization = `Bearer ${jwt}`;
  let r;
  try {
    r = await fetch(ruta, { ...opciones, headers, cache: 'no-store' });
  } catch {
    throw new Error('No se pudo conectar con el servicio. Compruebe la red y el backend.');
  }
  let datos = null;
  try { datos = await r.json(); } catch { /* sin cuerpo JSON */ }
  if (!r.ok) {
    const e = new Error(MENSAJES[r.status] || `HTTP ${r.status}: consulta no completada.`);
    e.codigoHttp = r.status;
    throw e;
  }
  return datos;
}

export async function iniciarSesion(usuario, clave) {
  if (!usuario || !clave) throw new Error('Ingrese usuario y contraseña.');
  try {
    const d = await pedir('/oauth/token', {
      method: 'POST', sinToken: true,
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ grant_type: 'password', username: usuario.trim(), password: clave }),
    });
    if (!d?.access_token) throw new Error('La respuesta de autenticación no contiene un token.');
    jwt = d.access_token;
  } catch (e) {
    if (e.codigoHttp === 400 || e.codigoHttp === 401) e.message = 'Usuario o contraseña incorrectos.';
    throw e;
  }
}

const arreglo = (d, que) => {
  if (!Array.isArray(d)) throw new Error(`La API debe devolver un arreglo de ${que}.`);
  return d;
};

export async function listarVehiculos(marca = '') {
  const q = marca.trim() ? `?marca=${encodeURIComponent(marca.trim())}` : '';
  return arreglo(await pedir(`/api/vehiculos${q}`), 'vehículos');
}

export async function listarVentas(estado = '') {
  const q = estado ? `?estado=${encodeURIComponent(estado)}` : '';
  return arreglo(await pedir(`/api/ventas${q}`), 'ventas');
}
