import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

// 데이터 경로 (Vercel vs 로컬 자동 감지)
function getDataDir(): string {
  const vercelDataDir = path.join(process.cwd(), "data");
  const localDataDir = path.join(process.cwd(), "..", "data");

  if (fs.existsSync(vercelDataDir)) {
    return vercelDataDir;
  }
  return localDataDir;
}

// 하이라이트 저장 파일 경로
function getHighlightsFile(): string {
  return path.join(getDataDir(), "highlights.json");
}

// 하이라이트 광고 정보
interface HighlightAd {
  id: string; // 고유 ID (image_url 기반 해시)
  image_url: string;
  page_name: string;
  ad_text?: string[];
  keyword: string;
  collected_at: string;
  highlighted_at: string;
  landing_url?: string;
}

interface HighlightsData {
  highlights: HighlightAd[];
}

function ensureDataDir() {
  const dataDir = getDataDir();
  if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true });
  }
}

function readHighlights(): HighlightsData {
  ensureDataDir();
  const highlightsFile = getHighlightsFile();
  if (!fs.existsSync(highlightsFile)) {
    return { highlights: [] };
  }
  try {
    const content = fs.readFileSync(highlightsFile, "utf-8");
    return JSON.parse(content);
  } catch {
    return { highlights: [] };
  }
}

function writeHighlights(data: HighlightsData) {
  ensureDataDir();
  const highlightsFile = getHighlightsFile();
  fs.writeFileSync(highlightsFile, JSON.stringify(data, null, 2), "utf-8");
}

// 이미지 URL에서 고유 ID 생성 (pathname 기반)
function generateId(imageUrl: string): string {
  try {
    const url = new URL(imageUrl);
    // pathname에서 파일명 추출
    const filename = url.pathname.split("/").pop() || "";
    // 확장자 제거하고 반환
    return filename.replace(/\.[^.]+$/, "");
  } catch {
    // URL 파싱 실패 시 간단한 해시
    return Buffer.from(imageUrl).toString("base64").slice(0, 20);
  }
}

// GET: 하이라이트 목록 조회
export async function GET() {
  try {
    const data = readHighlights();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error reading highlights:", error);
    return NextResponse.json(
      { error: "Failed to read highlights" },
      { status: 500 }
    );
  }
}

// POST: 하이라이트 추가
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { image_url, page_name, ad_text, keyword, collected_at, landing_url } = body;

    if (!image_url) {
      return NextResponse.json(
        { error: "image_url is required" },
        { status: 400 }
      );
    }

    const id = generateId(image_url);
    const data = readHighlights();

    // 이미 존재하는지 확인
    const exists = data.highlights.some((h) => h.id === id);
    if (exists) {
      return NextResponse.json({
        success: true,
        alreadyExists: true,
        id,
      });
    }

    // 새 하이라이트 추가
    const newHighlight: HighlightAd = {
      id,
      image_url,
      page_name: page_name || "Unknown",
      ad_text,
      keyword: keyword || "",
      collected_at: collected_at || "",
      highlighted_at: new Date().toISOString(),
      landing_url,
    };

    data.highlights.unshift(newHighlight); // 최신순으로 앞에 추가
    writeHighlights(data);

    return NextResponse.json({
      success: true,
      highlight: newHighlight,
    });
  } catch (error) {
    console.error("Error adding highlight:", error);
    return NextResponse.json(
      { error: "Failed to add highlight" },
      { status: 500 }
    );
  }
}

// DELETE: 하이라이트 제거
export async function DELETE(request: Request) {
  try {
    const body = await request.json();
    const { id, image_url } = body;

    // id 또는 image_url로 삭제 가능
    const targetId = id || (image_url ? generateId(image_url) : null);

    if (!targetId) {
      return NextResponse.json(
        { error: "id or image_url is required" },
        { status: 400 }
      );
    }

    const data = readHighlights();
    const index = data.highlights.findIndex((h) => h.id === targetId);

    if (index === -1) {
      return NextResponse.json(
        { error: "Highlight not found" },
        { status: 404 }
      );
    }

    data.highlights.splice(index, 1);
    writeHighlights(data);

    return NextResponse.json({
      success: true,
      removedId: targetId,
    });
  } catch (error) {
    console.error("Error deleting highlight:", error);
    return NextResponse.json(
      { error: "Failed to delete highlight" },
      { status: 500 }
    );
  }
}
