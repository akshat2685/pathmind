import type { NextConfig } from "next";

const isGithubPages = process.env.GITHUB_PAGES === "true";

const nextConfig: NextConfig = {
  ...(isGithubPages
    ? {
        output: "export",
        basePath: "/pathmind",
        assetPrefix: "/pathmind",
      }
    : {}),
  trailingSlash: true,
  async redirects() {
    return [
      { source: "/signup", destination: "/login", permanent: false },
      { source: "/signup/", destination: "/login/", permanent: false },
    ];
  },
  images: {
    unoptimized: true,
  },
  eslint: {
    ignoreDuringBuilds: false,
  },
  typescript: {
    ignoreBuildErrors: false,
  },
};

export default nextConfig;
