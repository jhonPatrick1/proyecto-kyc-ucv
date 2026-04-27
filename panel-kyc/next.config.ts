import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  experimental: {
    // Esto es lo que te pedía la terminal para aceptar tu IP
    serverActions: {
      allowedOrigins: ["192.168.18.21:3000", "localhost:3000"],
    },
  },
};

export default nextConfig;
