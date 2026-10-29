import type { NextConfig } from "next";

const API = process.env.EMPU_API_ORIGIN ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  experimental: {
    // Uploads are proxied through the dev server rewrites; lift the default
    // 10 MB proxy body cap so full-size videos (max 500 MB) upload cleanly.
    proxyClientMaxBodySize: "600mb",
  },
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${API}/api/:path*` },
      { source: "/media/:path*", destination: `${API}/media/:path*` },
    ];
  },
};
export default nextConfig;
