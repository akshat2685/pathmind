import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export", // Enforce static export for GitHub Pages
  basePath: "/pathmind", // The subpath for the GH pages deployment
  images: {
    unoptimized: true, // Required for static export
  },
  eslint: {
    ignoreDuringBuilds: false, 
  },
  typescript: {
    ignoreBuildErrors: false,
  }
};

export default nextConfig;
