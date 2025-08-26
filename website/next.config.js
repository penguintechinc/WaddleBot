/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  trailingSlash: true,
  skipTrailingSlashRedirect: true,
  images: {
    unoptimized: true,
  },
  // Optimize for Cloudflare Pages
  poweredByHeader: false,
  generateEtags: false,
}

module.exports = nextConfig