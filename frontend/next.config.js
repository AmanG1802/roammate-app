/** @type {import('next').NextConfig} */
const nextConfig = {
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
        destination: `${backend}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
