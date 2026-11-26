import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

// El client-id/secret OAuth se leen SOLO aqui (servidor de Vite). No llevan prefijo VITE_,
// por lo que Vite jamas los incluye en el codigo que descarga el navegador.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const destino = env.API_BASE_URL || 'http://127.0.0.1:8090'; // NGINX
  const basic = env.APP_CLIENT_ID && env.APP_CLIENT_SECRET
    ? 'Basic ' + Buffer.from(`${env.APP_CLIENT_ID}:${env.APP_CLIENT_SECRET}`).toString('base64')
    : null;

  return {
    plugins: [react()],
    server: {
      port: 5173,
      strictPort: true,
      proxy: {
        '/api': { target: destino, changeOrigin: true },
        '/oauth': {
          target: destino,
          changeOrigin: true,
          configure: (proxy) => {
            proxy.on('proxyReq', (req) => { if (basic) req.setHeader('Authorization', basic); });
          },
        },
      },
    },
    preview: { port: 4173, strictPort: true },
  };
});
