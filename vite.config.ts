import path from "node:path";
import { fileURLToPath } from "node:url";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const root = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(root, "./src"),
      react: path.resolve(root, "./node_modules/react"),
      "react-dom": path.resolve(root, "./node_modules/react-dom"),
    },
  },
  optimizeDeps: {
    include: ["react", "react-dom", "lucide-react"],
  },
  server: {
    proxy: {
      "/api": {
        target: process.env.VITE_BACKEND_URL || "https://schol-tau.vercel.app",
        changeOrigin: true,
      },
    },
  },
});
