import { defineConfig } from 'vite';
import { resolve } from 'path';
import { fileURLToPath, URL } from 'node:url';

export default defineConfig({
  // Base configuration
  base: './',
  root: './',

  // Build configuration
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: true,
    minify: 'esbuild',
    target: 'es2020',
    rollupOptions: {
      input: {
        main: fileURLToPath(new URL('index.html', import.meta.url)),
        demo: fileURLToPath(new URL('examples/basic-app.html', import.meta.url))
      },
      output: {
        manualChunks: {
          vendor: ['axios'],
          framework: ['src/core/PyservClient.js', 'src/core/Component.js', 'src/core/Reactive.js'],
          services: ['src/services/ApiClient.js', 'src/services/WebSocketClient.js'],
          components: ['src/components/App.js', 'src/components/Button.js']
        }
      }
    }
  },

  // Development server
  server: {
    port: 3000,
    open: '/examples/basic-app.html',
    host: true,
    cors: true
  },

  // Plugins
  plugins: [],

  // Dependencies
  optimizeDeps: {
    include: [
      'axios',
      'socket.io-client'
    ]
  },

  // Define global constants
  define: {
    __DEV__: JSON.stringify(process.env.NODE_ENV === 'development'),
    __PROD__: JSON.stringify(process.env.NODE_ENV === 'production'),
    __VERSION__: JSON.stringify(process.env.npm_package_version || '1.0.0')
  },

  // CSS configuration
  css: {
    devSourcemap: true,
    modules: {
      localsConvention: 'camelCase'
    }
  },

  // TypeScript configuration
  esbuild: {
    target: 'es2020',
    minify: true,
    treeShaking: true
  },

  // Preview configuration
  preview: {
    port: 4000,
    open: '/examples/basic-app.html'
  },

  // Environment variables
  envPrefix: 'PYSERV_',

  // Path resolution
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('src', import.meta.url)),
      '@/core': fileURLToPath(new URL('src/core', import.meta.url)),
      '@/services': fileURLToPath(new URL('src/services', import.meta.url)),
      '@/components': fileURLToPath(new URL('src/components', import.meta.url)),
      '@/types': fileURLToPath(new URL('src/types', import.meta.url)),
      '@/utils': fileURLToPath(new URL('src/utils', import.meta.url)),
      '@/hooks': fileURLToPath(new URL('src/hooks', import.meta.url)),
      '@/stores': fileURLToPath(new URL('src/stores', import.meta.url))
    }
  }
});
