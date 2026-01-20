import { NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

// 이미지 URL에서 고유 ID 생성 (pathname 기반)
function generateId(imageUrl: string): string {
  try {
    const url = new URL(imageUrl);
    const filename = url.pathname.split("/").pop() || "";
    return filename.replace(/\.[^.]+$/, "");
  } catch {
    return Buffer.from(imageUrl).toString("base64").slice(0, 20);
  }
}

// GET: 하이라이트 목록 조회
export async function GET() {
  try {
    const { data, error } = await supabase
      .from("highlights")
      .select("*")
      .order("highlighted_at", { ascending: false });

    if (error) {
      console.error("Supabase error:", error);
      return NextResponse.json(
        { error: "Failed to read highlights" },
        { status: 500 }
      );
    }

    // 프론트엔드 호환 형식으로 변환
    const highlights = (data || []).map((h) => ({
      id: generateId(h.image_url),
      image_url: h.image_url,
      page_name: h.page_name,
      ad_text: h.ad_text,
      keyword: h.keyword,
      collected_at: h.collected_at,
      highlighted_at: h.highlighted_at,
      landing_url: h.landing_url,
    }));

    return NextResponse.json({ highlights });
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

    // 중복 체크
    const { data: existing } = await supabase
      .from("highlights")
      .select("id")
      .eq("image_url", image_url)
      .single();

    if (existing) {
      return NextResponse.json({
        success: true,
        alreadyExists: true,
        id: generateId(image_url),
      });
    }

    // 새 하이라이트 추가
    const { error: insertError } = await supabase.from("highlights").insert({
      image_url,
      page_name: page_name || "Unknown",
      ad_text: ad_text || [],
      keyword: keyword || "",
      collected_at: collected_at || "",
      landing_url,
    });

    if (insertError) {
      // 중복 에러인 경우
      if (insertError.code === "23505") {
        return NextResponse.json({
          success: true,
          alreadyExists: true,
          id: generateId(image_url),
        });
      }
      console.error("Insert error:", insertError);
      return NextResponse.json(
        { error: "Failed to add highlight" },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      highlight: {
        id: generateId(image_url),
        image_url,
        page_name: page_name || "Unknown",
        ad_text,
        keyword,
        collected_at,
        highlighted_at: new Date().toISOString(),
        landing_url,
      },
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

    if (!image_url) {
      return NextResponse.json(
        { error: "image_url is required" },
        { status: 400 }
      );
    }

    const { error: deleteError } = await supabase
      .from("highlights")
      .delete()
      .eq("image_url", image_url);

    if (deleteError) {
      console.error("Delete error:", deleteError);
      return NextResponse.json(
        { error: "Failed to delete highlight" },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      removedId: id || generateId(image_url),
    });
  } catch (error) {
    console.error("Error deleting highlight:", error);
    return NextResponse.json(
      { error: "Failed to delete highlight" },
      { status: 500 }
    );
  }
}
