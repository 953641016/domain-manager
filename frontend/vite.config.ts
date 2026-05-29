/** @type {import('vite').UserConfig} */
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  
  return {
    plugins: [react()],
    
    base: env.VITE_BASE_PATH || '/domainmgr',
    
    server: {
      port: 3000,
      proxy: {
        '/domainmgr/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/domainmgr/, ''),
        },
      },
    },
    
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    
    build: {
      outDir: 'dist',
      sourcemap: mode === 'development',
    },
  };
});
