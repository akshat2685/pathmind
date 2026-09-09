import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export", // Enforce static export for GitHub Pages
  basePath: "/pathmind", // The subpath for the GH pages deployment
  assetPrefix: "/pathmind", // Ensure all assets resolve under the repository subpath
  trailingSlash: true, // Required for GitHub Pages to resolve index.html and RSC payloads (.txt) consistently
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
