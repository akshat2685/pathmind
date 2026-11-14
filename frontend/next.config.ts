import type { NextConfig } from "next";

// GitHub Pages (static export under /pathmind) is the legacy deploy target.
// Vercel is the production target: a plain Next.js server build served at
// the project root. The static-export settings are therefore gated behind
// NEXT_STATIC_EXPORT=true, which only the GitHub Pages workflow sets.
// Vercel builds (env unset) get a standard Next.js server build with no
// basePath and no forced trailing slash.
const isStaticExport = process.env.NEXT_STATIC_EXPORT === "true";

const nextConfig: NextConfig = {
  ...(isStaticExport
    ? {
        output: "export", // Enforce static export for GitHub Pages
        basePath: "/pathmind", // The subpath for the GH pages deployment
        assetPrefix: "/pathmind", // Ensure all assets resolve under the repository subpath
        trailingSlash: true, // Required for GitHub Pages to resolve index.html and RSC payloads (.txt) consistently
      }
    : {}),
  async redirects() {
    return [
      { source: "/signup", destination: "/login", permanent: false },
      { source: "/signup/", destination: "/login/", permanent: false },
    ];
  },
  images: {
    unoptimized: true, // Required for static export; harmless on Vercel
  },
  eslint: {
    ignoreDuringBuilds: false,
  },
  typescript: {
    ignoreBuildErrors: false,
  },
};

export default nextConfig;
