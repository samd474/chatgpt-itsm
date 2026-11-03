import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

/** Matches modules inside the named node_modules packages. */
const vendor = (...packages: string[]) =>
  new RegExp(`node_modules[\\\\/](${packages.map((p) => p.replace("/", "[\\\\/]")).join("|")})[\\\\/]`);

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  // Same-origin /api in development: the browser calls http://localhost:5173/api/...
  // and Vite forwards it to Django inside the Compose network, so the session and
  // CSRF cookies stay on the browser-facing origin (like NGINX in production).
  const target = env.VITE_DEV_PROXY_TARGET || "http://backend:8000";
  return {
    plugins: [react()],
    build: {
      rolldownOptions: {
        output: {
          // Long-lived vendor chunks so app updates don't re-download libraries.
          codeSplitting: {
            groups: [
              { name: "react", test: vendor("react", "react-dom", "react-router", "react-router-dom", "scheduler") },
              { name: "data", test: vendor("@tanstack/react-query", "@tanstack/query-core", "axios", "zod", "react-hook-form", "@hookform/resolvers") },
              { name: "icons", test: vendor("lucide-react") },
            ],
          },
        },
      },
    },
    server: {
      host: "0.0.0.0",
      port: 5173,
      strictPort: true,
      // File-change events don't cross Windows/WSL bind mounts into Docker, so poll there.
      watch: env.VITE_USE_POLLING === "1" ? { usePolling: true, interval: 300 } : undefined,
      proxy: {
        "/api": { target, changeOrigin: false },
        "/admin": { target, changeOrigin: false },
        "/static": { target, changeOrigin: false },
      },
    },
  };
});
