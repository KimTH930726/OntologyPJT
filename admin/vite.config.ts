import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

const API_TARGET = process.env.VITE_API_TARGET || "http://localhost:8000";

const proxyPrefixes = [
  "/documents",
  "/chunks",
  "/candidates",
  "/ontology",
  "/graph",
  "/qa",
  "/audit-logs",
  "/health",
];

export default defineConfig({
  plugins: [react()],
  base: "/admin/",
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  build: {
    outDir: "../app/static/admin",
    emptyOutDir: true,
    sourcemap: false,
  },
  server: {
    port: 5173,
    proxy: Object.fromEntries(
      proxyPrefixes.map((p) => [p, { target: API_TARGET, changeOrigin: true }]),
    ),
  },
});
