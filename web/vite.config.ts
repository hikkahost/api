import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  base: "/",
  build: {
    outDir: path.resolve(__dirname, "../app/setup_web/static/dist"),
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      "/setup": {
        target: "http://127.0.0.1:8001",
        changeOrigin: true,
        cookiePathRewrite: { "/": "/" },
      },
    },
  },
});
