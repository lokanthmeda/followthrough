/** @type {import('next').NextConfig} */
const path = require('path');

module.exports = {
  reactStrictMode: true,
  trailingSlash: false,
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  webpack(config) {
    // Keep @/* pointed at src/, and @/styles at styles/ (do not map bare "@"
    // alone — that breaks imports like @/styles/globals.css).
    config.resolve.alias = {
      ...(config.resolve.alias || {}),
      '@/src': path.resolve(__dirname, 'src'),
      '@/lib': path.resolve(__dirname, 'src/lib'),
      '@/styles': path.resolve(__dirname, 'styles'),
    };
    return config;
  },
};