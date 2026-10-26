/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  serverExternalPackages: ["mqtt"],
  poweredByHeader: false,
};

export default nextConfig;
