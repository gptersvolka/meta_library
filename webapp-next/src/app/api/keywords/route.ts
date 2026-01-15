import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

// 키워드 저장 파일 경로 (스케줄러와 동일한 파일 사용)
const KEYWORDS_FILE = path.join(process.cwd(), "..", "data", "keywords.json");

// 스케줄러와 동일한 형식
interface KeywordItem {
  query: string;
  country: string;
  limit: number;
  enabled: boolean;
}

interface KeywordsData {
  keywords: KeywordItem[];
  schedule: {
    time: string;
  };
}

function ensureDataDir() {
  const dataDir = path.dirname(KEYWORDS_FILE);
  if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true });
  }
}

function readKeywords(): KeywordsData {
  ensureDataDir();
  if (!fs.existsSync(KEYWORDS_FILE)) {
    return {
      keywords: [],
      schedule: { time: "09:00" }
    };
  }
  try {
    const content = fs.readFileSync(KEYWORDS_FILE, "utf-8");
    return JSON.parse(content);
  } catch {
    return {
      keywords: [],
      schedule: { time: "09:00" }
    };
  }
}

function writeKeywords(data: KeywordsData) {
  ensureDataDir();
  fs.writeFileSync(KEYWORDS_FILE, JSON.stringify(data, null, 2), "utf-8");
}

// GET: 키워드 목록 조회
export async function GET() {
  try {
    const data = readKeywords();
    // 키워드 query만 추출해서 반환
    const keywordQueries = data.keywords.map(kw => kw.query);
    return NextResponse.json({
      keywords: keywordQueries,
      schedule: data.schedule,
    });
  } catch (error) {
    console.error("Error reading keywords:", error);
    return NextResponse.json(
      { error: "Failed to read keywords" },
      { status: 500 }
    );
  }
}

// POST: 새 키워드 추가
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { keyword, country = "KR", limit = 50 } = body;

    if (!keyword || typeof keyword !== "string") {
      return NextResponse.json(
        { error: "Invalid keyword" },
        { status: 400 }
      );
    }

    const trimmedKeyword = keyword.trim();
    if (!trimmedKeyword) {
      return NextResponse.json(
        { error: "Keyword cannot be empty" },
        { status: 400 }
      );
    }

    const data = readKeywords();

    // 중복 체크
    const exists = data.keywords.some(kw => kw.query === trimmedKeyword);
    if (exists) {
      return NextResponse.json(
        { error: "Keyword already exists", keywords: data.keywords.map(kw => kw.query) },
        { status: 409 }
      );
    }

    // 키워드 추가 (스케줄러 형식)
    data.keywords.push({
      query: trimmedKeyword,
      country,
      limit,
      enabled: true,
    });
    writeKeywords(data);

    return NextResponse.json({
      success: true,
      keyword: trimmedKeyword,
      keywords: data.keywords.map(kw => kw.query),
    });
  } catch (error) {
    console.error("Error adding keyword:", error);
    return NextResponse.json(
      { error: "Failed to add keyword" },
      { status: 500 }
    );
  }
}

// DELETE: 키워드 삭제
export async function DELETE(request: Request) {
  try {
    const body = await request.json();
    const { keyword } = body;

    if (!keyword || typeof keyword !== "string") {
      return NextResponse.json(
        { error: "Invalid keyword" },
        { status: 400 }
      );
    }

    const data = readKeywords();
    const index = data.keywords.findIndex(kw => kw.query === keyword);

    if (index === -1) {
      return NextResponse.json(
        { error: "Keyword not found" },
        { status: 404 }
      );
    }

    data.keywords.splice(index, 1);
    writeKeywords(data);

    return NextResponse.json({
      success: true,
      keywords: data.keywords.map(kw => kw.query),
    });
  } catch (error) {
    console.error("Error deleting keyword:", error);
    return NextResponse.json(
      { error: "Failed to delete keyword" },
      { status: 500 }
    );
  }
}
