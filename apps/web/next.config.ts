import type { NextConfig } from "next";

const internalApi =
  process.env.OPORTUNA_INTERNAL_API_URL ?? process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  poweredByHeader: false,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${internalApi}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
