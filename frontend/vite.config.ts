import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Слушаем все интерфейсы: работает и через 127.0.0.1, и через ::1
    host: true,
    port: 5173,
    // Всегда строго 5173: если порт занят — Vite покажет ошибку в окне,
    // а не молча переедет на 5174 (backend по CORS доверяет только 5173)
    strictPort: true,
  },
});
