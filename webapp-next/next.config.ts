import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        // Meta CDN 이미지
        protocol: "https",
        hostname: "**.fbcdn.net",
      },
      {
        // Meta CDN 이미지 (scontent)
        protocol: "https",
        hostname: "scontent*.fbcdn.net",
      },
      {
        // Cloudflare R2 공개 URL (r2.dev 서브도메인)
        protocol: "https",
        hostname: "**.r2.dev",
      },
    ],
  },
  // API 라우트에서 파일 시스템 접근을 위한 설정
  experimental: {
    serverActions: {
      bodySizeLimit: "2mb",
    },
  },
};

export default nextConfig;
