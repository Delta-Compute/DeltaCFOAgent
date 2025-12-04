import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

const nextConfig: NextConfig = {
  // Enable React strict mode for better development experience
  reactStrictMode: true,

  // Configure API rewrites to proxy requests to Flask backend
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.FLASK_API_URL || "http://localhost:5001"}/api/:path*`,
      },
    ];
  },

  // Allow images from external sources if needed
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**",
      },
    ],
  },
};

export default withNextIntl(nextConfig);
