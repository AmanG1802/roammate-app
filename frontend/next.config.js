/** @type {import('next').NextConfig} */
const nextConfig = {
  // Don't 308-redirect `/api/trips/` -> `/api/trips`. Preserving the trailing
  // slash lets the proxy forward it intact so it matches FastAPI's `/api/trips/`
  // route directly, avoiding a backend redirect_slashes 307 leaking to the browser.
  skipTrailingSlashRedirect: true,
  async headers() {
    return [
      {
        source: '/.well-known/apple-app-site-association',
        headers: [{ key: 'Content-Type', value: 'application/json' }],
      },
    ];
  },
  async rewrites() {
    const backend =
      process.env.BACKEND_INTERNAL_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      'http://localhost:8000/api';
    return [
      {
        source: '/api/:path((?!auth/).*)',
        destination: `${backend}/:path`,
      },
    ];
  },
};

module.exports = nextConfig;
