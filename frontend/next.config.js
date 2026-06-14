/** @type {import('next').NextConfig} */
const nextConfig = {
  // Backend routes are spec-first (openapi.yaml) and have NO trailing slash
  // (e.g. `/api/trips`). Frontend calls must match exactly — a trailing slash
  // makes FastAPI's redirect_slashes emit a 307 to the absolute backend origin,
  // which leaks the backend host to the browser (and surfaced as mixed content
  // before the backend proxy-headers fix). Keep this so Next never rewrites
  // slashes itself; the proxy then forwards the path through untouched.
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
