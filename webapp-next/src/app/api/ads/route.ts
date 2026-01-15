import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

interface Ad {
  page_name?: string;
  ad_text?: string[];
  image_urls?: string[];
  video_urls?: string[];
  _collected_at?: string;
  _source_file?: string;
}

interface JsonData {
  query: string;
  collected_at: string;
  ads: Ad[];
}

export async function GET() {
  try {
    // data/raw 폴더 경로 (프로젝트 루트 기준)
    const dataDir = path.join(process.cwd(), "..", "data", "raw");

    if (!fs.existsSync(dataDir)) {
      return NextResponse.json({ keywords: [], ads: {} }, { status: 200 });
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

    // 중복 제거 (image_urls 기준)
    for (const keyword in allAds) {
      const seenUrls = new Set<string>();
      allAds[keyword] = allAds[keyword].filter((ad) => {
        const imageUrl = ad.image_urls?.[0];
        if (imageUrl && !seenUrls.has(imageUrl)) {
          seenUrls.add(imageUrl);
          return true;
        }
        return !imageUrl ? false : false;
      });
    }

    return NextResponse.json({
      keywords: Object.keys(allAds),
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
