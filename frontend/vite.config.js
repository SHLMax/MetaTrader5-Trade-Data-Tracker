import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import electron from 'vite-plugin-electron'
import renderer from 'vite-plugin-electron-renderer'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    electron({
      entry: 'electron/main.js',
    }),
    renderer(),
  ],
  server: {
    host: '0.0.0.0',
    port: 3000,
    strictPort: false
  }
})
