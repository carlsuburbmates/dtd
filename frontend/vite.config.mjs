import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import svgr from "vite-plugin-svgr";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react(), svgr()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  define: {
    "process.env.REACT_APP_BACKEND_URL": JSON.stringify(process.env.REACT_APP_BACKEND_URL || ""),
    "process.env.REACT_APP_FIRST_LEASH_URL": JSON.stringify(process.env.REACT_APP_FIRST_LEASH_URL || "https://learn.dogtrainersdirectory.com.au"),
    "process.env.REACT_APP_DIRECTORY_URL": JSON.stringify(process.env.REACT_APP_DIRECTORY_URL || "https://dogtrainersdirectory.com.au"),
    "process.env.NODE_ENV": JSON.stringify(process.env.NODE_ENV || "production"),
  },
  build: {
    outDir: "build",
    emptyOutDir: true,
  },
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/setupTests.js",
    css: true,
  },
});
