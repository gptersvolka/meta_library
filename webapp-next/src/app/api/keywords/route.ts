import { NextResponse } from "next/server";
import { supabase, KeywordRow } from "@/lib/supabase";

// GitHub Actions 워크플로우 트리거 (특정 키워드만 수집)
async function triggerCollectionForKeyword(keyword: string): Promise<{ success: boolean; message: string }> {
  const token = process.env.GITHUB_TOKEN;
  const owner = process.env.GITHUB_OWNER || "gptersvolka";
  const repo = process.env.GITHUB_REPO || "meta_library";

  if (!token) {
    return {
      success: false,
      message: "GITHUB_TOKEN이 설정되지 않았습니다.",
    };
  }

  try {
    const response = await fetch(
      `https://api.github.com/repos/${owner}/${repo}/actions/workflows/collect-ads.yml/dispatches`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "application/vnd.github.v3+json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ref: "main",
          inputs: {
            query: keyword,
          },
        }),
      }
    );

    if (response.status === 204) {
      return {
        success: true,
        message: `'${keyword}' 키워드 수집이 시작되었습니다.`,
      };
    } else {
      const errorText = await response.text();
      console.error("GitHub API error:", response.status, errorText);
      return {
        success: false,
        message: `GitHub Actions 트리거 실패: ${response.status}`,
      };
    }
  } catch (error) {
    console.error("GitHub API request failed:", error);
    return {
      success: false,
      message: "GitHub API 요청 실패",
    };
  }
}

// GET: 키워드 목록 조회
export async function GET() {
  try {
    const { data, error } = await supabase
      .from("keywords")
      .select("*")
      .order("created_at", { ascending: true });

    if (error) {
      console.error("Supabase error:", error);
      return NextResponse.json(
        { error: "Failed to read keywords" },
        { status: 500 }
      );
    }

    const keywords = (data as KeywordRow[]) || [];
    const keywordQueries = keywords.map((kw) => kw.query);

    return NextResponse.json({
      keywords: keywordQueries,
      keywordsData: keywords,
      schedule: { time: "09:00" },
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

    // 중복 체크
    const { data: existing } = await supabase
      .from("keywords")
      .select("query")
      .eq("query", trimmedKeyword)
      .single();

    if (existing) {
      // 이미 존재하면 성공으로 반환
      const { data: allKeywords } = await supabase
        .from("keywords")
        .select("query");

      return NextResponse.json({
        success: true,
        keyword: trimmedKeyword,
        keywords: (allKeywords || []).map((kw: { query: string }) => kw.query),
        alreadyExists: true,
        message: "Keyword already exists, you can run collection",
      });
    }

    // 키워드 추가
    const { error: insertError } = await supabase.from("keywords").insert({
      query: trimmedKeyword,
      country,
      ad_limit: limit,
      enabled: true,
    });

    if (insertError) {
      console.error("Insert error:", insertError);
      return NextResponse.json(
        { error: "Failed to add keyword" },
        { status: 500 }
      );
    }

    // 전체 키워드 목록 반환
    const { data: allKeywords } = await supabase
      .from("keywords")
      .select("query");

    // 키워드 추가 성공 시 즉시 수집 트리거 (Vercel 환경에서만)
    let collectionTriggered = false;
    let collectionMessage = "";
    if (process.env.VERCEL) {
      const triggerResult = await triggerCollectionForKeyword(trimmedKeyword);
      collectionTriggered = triggerResult.success;
      collectionMessage = triggerResult.message;
    }

    return NextResponse.json({
      success: true,
      keyword: trimmedKeyword,
      keywords: (allKeywords || []).map((kw: { query: string }) => kw.query),
      collectionTriggered,
      collectionMessage: collectionTriggered
        ? `키워드 추가 완료! ${collectionMessage}`
        : "키워드 추가 완료",
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

    const { error: deleteError } = await supabase
      .from("keywords")
      .delete()
      .eq("query", keyword);

    if (deleteError) {
      console.error("Delete error:", deleteError);
      return NextResponse.json(
        { error: "Failed to delete keyword" },
        { status: 500 }
      );
    }

    // 전체 키워드 목록 반환
    const { data: allKeywords } = await supabase
      .from("keywords")
      .select("query");

    return NextResponse.json({
      success: true,
      keywords: (allKeywords || []).map((kw: { query: string }) => kw.query),
    });
  } catch (error) {
    console.error("Error deleting keyword:", error);
    return NextResponse.json(
      { error: "Failed to delete keyword" },
      { status: 500 }
    );
  }
}
