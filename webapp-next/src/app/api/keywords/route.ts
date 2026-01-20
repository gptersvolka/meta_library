import { NextResponse } from "next/server";
import { supabase, KeywordRow } from "@/lib/supabase";

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

    return NextResponse.json({
      success: true,
      keyword: trimmedKeyword,
      keywords: (allKeywords || []).map((kw: { query: string }) => kw.query),
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
