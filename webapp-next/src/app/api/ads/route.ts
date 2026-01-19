import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

// 데이터 경로 (Vercel vs 로컬 자동 감지)
function getDataDir(): string {
  // Vercel 환경에서는 프로젝트 루트/data
  // 로컬에서는 webapp-next/../data
  const vercelDataDir = path.join(process.cwd(), "data");
  const localDataDir = path.join(process.cwd(), "..", "data");

  // Vercel 배포 시 data 폴더가 프로젝트 루트에 있음
  if (fs.existsSync(vercelDataDir) && fs.existsSync(path.join(vercelDataDir, "raw"))) {
    return vercelDataDir;
  }
  return localDataDir;
}

interface Ad {
  page_name?: string;
  ad_text?: string[];
  image_urls?: string[];
  video_urls?: string[];
  landing_url?: string;
  r2_image_url?: string; // Cloudflare R2에 업로드된 이미지 URL
  _collected_at?: string;
  _source_file?: string;
}

interface JsonData {
  query: string;
  collected_at: string;
  ads: Ad[];
}

interface KeywordItem {
  query: string;
  country: string;
  limit: number;
  enabled: boolean;
}

interface KeywordsData {
  keywords: KeywordItem[];
  schedule: { time: string };
}

// keywords.json에서 등록된 키워드 목록 읽기
function getRegisteredKeywords(): string[] {
  const keywordsFile = path.join(getDataDir(), "keywords.json");
  try {
    if (fs.existsSync(keywordsFile)) {
      const content = fs.readFileSync(keywordsFile, "utf-8");
      const data: KeywordsData = JSON.parse(content);
      return data.keywords.map(kw => kw.query);
    }
  } catch (e) {
    console.error("Error reading keywords.json:", e);
  }
  return [];
}

export async function GET() {
  try {
    // data/raw 폴더 경로
    const dataDir = path.join(getDataDir(), "raw");

    // keywords.json에서 등록된 키워드 가져오기
    const registeredKeywords = getRegisteredKeywords();

    if (!fs.existsSync(dataDir)) {
      // 폴더가 없어도 등록된 키워드는 표시 (빈 광고 목록과 함께)
      const emptyAds: Record<string, Ad[]> = {};
      for (const kw of registeredKeywords) {
        emptyAds[kw] = [];
      }
      return NextResponse.json({ keywords: registeredKeywords, ads: emptyAds }, { status: 200 });
    }

    const files = fs.readdirSync(dataDir).filter((f) => f.endsWith(".json"));
    const allAds: Record<string, Ad[]> = {};

    for (const file of files) {
      try {
        const filePath = path.join(dataDir, file);
        const content = fs.readFileSync(filePath, "utf-8");
        const data: JsonData = JSON.parse(content);

        const query = data.query || "unknown";
        const collectedAt = data.collected_at || "";
        const ads = data.ads || [];

        if (!allAds[query]) {
          allAds[query] = [];
        }

        for (const ad of ads) {
          allAds[query].push({
            ...ad,
            _collected_at: collectedAt,
            _source_file: file,
          });
        }
      } catch (e) {
        console.error(`Error reading ${file}:`, e);
      }
    }

    // 중복 제거 (이미지 URL 기준 - 쿼리스트링 제외하고 파일 경로만 비교)
    for (const keyword in allAds) {
      const seenImagePaths = new Set<string>();
      allAds[keyword] = allAds[keyword].filter((ad) => {
        const imageUrl = ad.image_urls?.[0];
        if (!imageUrl) return false;

        // URL에서 쿼리스트링 제외하고 경로만 추출
        // 예: https://scontent.../615432525_871913725548992_n.jpg?stp=... → 615432525_871913725548992_n.jpg
        let imagePath = imageUrl;
        try {
          const url = new URL(imageUrl);
          imagePath = url.pathname; // /v/t39.35426-6/615432525_...n.jpg
        } catch {
          // URL 파싱 실패 시 원본 사용
        }

        if (!seenImagePaths.has(imagePath)) {
          seenImagePaths.add(imagePath);
          return true;
        }
        return false;
      });
    }

    // keywords.json에 등록되었지만 아직 수집되지 않은 키워드도 포함
    for (const kw of registeredKeywords) {
      if (!allAds[kw]) {
        allAds[kw] = [];
      }
    }

    // 키워드 목록: keywords.json 순서 우선, 그 다음 수집된 키워드
    const collectedKeywords = Object.keys(allAds);
    const orderedKeywords = [
      ...registeredKeywords,
      ...collectedKeywords.filter(kw => !registeredKeywords.includes(kw))
    ];

    return NextResponse.json({
      keywords: orderedKeywords,
      ads: allAds,
    });
  } catch (error) {
    console.error("API Error:", error);
    return NextResponse.json(
      { error: "Failed to load ads" },
      { status: 500 }
    );
  }
}
