import { NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

interface Ad {
  id: string;
  keyword: string;
  page_name: string;
  ad_text: string[];
  image_url: string;
  permanent_image_url: string;
  landing_url: string;
  collected_at: string;
}

// Supabase에서 등록된 키워드 목록 읽기
async function getRegisteredKeywords(): Promise<string[]> {
  try {
    const { data, error } = await supabase
      .from("keywords")
      .select("query")
      .eq("enabled", true)
      .order("created_at", { ascending: true });

    if (error) {
      console.error("Supabase keywords error:", error);
      return [];
    }

    return (data || []).map((kw: { query: string }) => kw.query);
  } catch (e) {
    console.error("Error reading keywords from Supabase:", e);
    return [];
  }
}

// Supabase에서 광고 데이터 읽기
async function getAdsFromSupabase(): Promise<Record<string, Ad[]>> {
  try {
    const { data, error } = await supabase
      .from("ads")
      .select("*")
      .order("collected_at", { ascending: false });

    if (error) {
      console.error("Supabase ads error:", error);
      return {};
    }

    // 키워드별로 그룹화
    const adsByKeyword: Record<string, Ad[]> = {};
    for (const ad of data || []) {
      const keyword = ad.keyword || "unknown";
      if (!adsByKeyword[keyword]) {
        adsByKeyword[keyword] = [];
      }

      // 프론트엔드 호환 형태로 변환
      adsByKeyword[keyword].push({
        id: ad.id,
        keyword: ad.keyword,
        page_name: ad.page_name,
        ad_text: ad.ad_text || [],
        image_url: ad.image_url,
        permanent_image_url: ad.permanent_image_url,
        landing_url: ad.landing_url,
        collected_at: ad.collected_at,
      });
    }

    return adsByKeyword;
  } catch (e) {
    console.error("Error reading ads from Supabase:", e);
    return {};
  }
}

export async function GET() {
  try {
    // Supabase에서 키워드와 광고 데이터 가져오기
    const [registeredKeywords, adsByKeyword] = await Promise.all([
      getRegisteredKeywords(),
      getAdsFromSupabase(),
    ]);

    // 프론트엔드 호환 형태로 변환
    const allAds: Record<string, Array<{
      page_name?: string;
      ad_text?: string[];
      image_urls?: string[];
      permanent_image_url?: string;
      landing_url?: string;
      _collected_at?: string;
    }>> = {};

    // Supabase 데이터를 기존 형식으로 변환
    for (const [keyword, ads] of Object.entries(adsByKeyword)) {
      allAds[keyword] = ads.map((ad) => ({
        page_name: ad.page_name,
        ad_text: ad.ad_text,
        image_urls: [ad.permanent_image_url || ad.image_url],
        permanent_image_url: ad.permanent_image_url,
        landing_url: ad.landing_url,
        _collected_at: ad.collected_at,
      }));
    }

    // 등록된 키워드 중 아직 수집 안 된 것도 포함
    for (const kw of registeredKeywords) {
      if (!allAds[kw]) {
        allAds[kw] = [];
      }
    }

    // 키워드 순서: 등록된 키워드 우선
    const collectedKeywords = Object.keys(allAds);
    const orderedKeywords = [
      ...registeredKeywords,
      ...collectedKeywords.filter((kw) => !registeredKeywords.includes(kw)),
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
