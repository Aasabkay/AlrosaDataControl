import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Адрес API задаётся переменной VITE_API_URL (см. src/api.js).
export default defineConfig({
  plugins: [react()],
  server: {
    // Явно 127.0.0.1: на некоторых машинах bind на ::1 не открывается извне.
    host: '127.0.0.1',
    port: 5173,
  },
})
