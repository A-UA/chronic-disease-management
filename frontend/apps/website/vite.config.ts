import { defineConfig } from "vite-plus";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { resolve } from "path";

const backendPortMap: Record<string, number> = {
  java: 8000,
  nestjs: 8001,
};

const backend = process.env.VITE_BACKEND || "nestjs";
const backendPort = backendPortMap[backend] || 8000;

export default defineConfig({
  staged: {
    "*": "vp check --fix",
  },
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": resolve(__dirname, "src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: `http://localhost:${backendPort}`,
        changeOrigin: true,
      },
    },
  },
});
