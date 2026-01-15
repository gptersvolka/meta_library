"use client";

import { useEffect, useState, useMemo } from "react";
import { AdCard } from "@/components/ui/ad-card";
import { AdDetailModal } from "@/components/ad-detail-modal";
import { GlassButton } from "@/components/ui/glass-button";
import { KeywordInput } from "@/components/ui/keyword-input";
import { RefreshCw, Calendar, ChevronDown, X, Sparkles } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Calendar as CalendarComponent } from "@/components/ui/calendar";
import { format } from "date-fns";
import { DateRange } from "react-day-picker";

interface Ad {
  page_name?: string;
  ad_text?: string[];
  image_urls?: string[];
  video_urls?: string[];
  _collected_at?: string;
  _source_file?: string;
}

interface AdsData {
  keywords: string[];
  ads: Record<string, Ad[]>;
}

export default function Home() {
  const [data, setData] = useState<AdsData>({ keywords: [], ads: {} });
  const [selectedKeyword, setSelectedKeyword] = useState<string>("");
  const [selectedAd, setSelectedAd] = useState<Ad | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  // 날짜 필터
  const [dateRange, setDateRange] = useState<DateRange | undefined>({
    from: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
    to: new Date(),
  });

  // 광고주 필터
  const [selectedAdvertisers, setSelectedAdvertisers] = useState<string[]>([]);
  const [advertiserDropdownOpen, setAdvertiserDropdownOpen] = useState(false);

  const fetchAds = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/ads");
      const json = await res.json();
      setData(json);
      if (json.keywords.length > 0 && !selectedKeyword) {
        setSelectedKeyword(json.keywords[0]);
      }
    } catch (e) {
      console.error("Failed to fetch ads:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAds();
  }, []);

  const currentAds = data.ads[selectedKeyword] || [];

  // 유효한 이미지가 있는 광고만 필터링
  const validAds = useMemo(() => {
    return currentAds.filter((ad) => {
      const imageUrl = ad.image_urls?.[0];
      if (!imageUrl) return false;
      const sizeMatch = imageUrl.match(/(\d+)x(\d+)/);
      if (sizeMatch) {
        const width = parseInt(sizeMatch[1]);
        const height = parseInt(sizeMatch[2]);
        if (width < 200 || height < 200) return false;
      }
      return true;
    });
  }, [currentAds]);

  // 날짜 필터 적용
  const dateFilteredAds = useMemo(() => {
    if (!dateRange?.from || !dateRange?.to) return validAds;

    return validAds.filter((ad) => {
      if (!ad._collected_at) return true;
      const adDate = new Date(ad._collected_at);
      return adDate >= dateRange.from! && adDate <= dateRange.to!;
    });
  }, [validAds, dateRange]);

  // 광고주 목록 (날짜 필터 적용 후)
  const availableAdvertisers = useMemo(() => {
    const advertisers = new Set(dateFilteredAds.map((ad) => ad.page_name).filter(Boolean));
    return Array.from(advertisers).sort() as string[];
  }, [dateFilteredAds]);

  // 최종 필터링된 광고
  const filteredAds = useMemo(() => {
    if (selectedAdvertisers.length === 0) return dateFilteredAds;
    return dateFilteredAds.filter((ad) => selectedAdvertisers.includes(ad.page_name || ""));
  }, [dateFilteredAds, selectedAdvertisers]);

  const uniqueAdvertisers = new Set(filteredAds.map((ad) => ad.page_name)).size;

  const toggleAdvertiser = (advertiser: string) => {
    setSelectedAdvertisers((prev) =>
      prev.includes(advertiser)
        ? prev.filter((a) => a !== advertiser)
        : [...prev, advertiser]
    );
  };

  return (
    <div className="flex min-h-screen bg-gradient-to-br from-gray-50 via-gray-100 to-gray-50">
      {/* 배경 도트 패턴 */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <svg xmlns="http://www.w3.org/2000/svg" height="100%" width="100%">
          <defs>
            <pattern patternUnits="userSpaceOnUse" height="30" width="30" id="dottedGrid">
              <circle fill="oklch(from var(--foreground) l c h / 8%)" r="1" cy="2" cx="2"></circle>
            </pattern>
          </defs>
          <rect fill="url(#dottedGrid)" height="100%" width="100%"></rect>
        </svg>
      </div>

      {/* 사이드바 */}
      <aside className="w-64 glass-sidebar p-6 flex flex-col relative z-10">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-foreground/70" />
          <h1 className="text-xl font-semibold text-foreground">Ad Reference</h1>
        </div>
        <p className="text-xs text-muted-foreground mt-1">Meta Ad Library Collection</p>

        <div className="h-px bg-border/50 my-6" />

        <h2 className="text-sm font-medium text-foreground/70 mb-3">Keywords</h2>
        <div className="space-y-2 flex-1 overflow-y-auto">
          {data.keywords.map((keyword) => (
            <button
              key={keyword}
              onClick={() => setSelectedKeyword(keyword)}
              className={`glass-keyword w-full text-left px-3 py-2 rounded-lg text-sm ${
                selectedKeyword === keyword ? "active" : ""
              }`}
            >
              {keyword}
            </button>
          ))}
        </div>

        {/* 키워드 추가 입력란 */}
        <div className="mt-4">
          <KeywordInput
            placeholder="키워드 추가"
            onSubmit={async (keyword) => {
              try {
                // 1. 키워드 저장
                const saveRes = await fetch("/api/keywords", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ keyword }),
                });
                const saveResult = await saveRes.json();

                if (!saveRes.ok) {
                  alert(saveResult.error || "키워드 추가 실패");
                  return;
                }

                // 2. 즉시 수집 실행
                alert(`"${keyword}" 키워드 추가됨!\n광고 수집을 시작합니다. (1~2분 소요)`);

                const collectRes = await fetch("/api/collect", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ keyword, limit: 50 }),
                });
                const collectResult = await collectRes.json();

                if (collectRes.ok) {
                  alert(`"${keyword}" 광고 수집 완료!`);
                  // 데이터 새로고침
                  await fetchAds();
                  setSelectedKeyword(keyword);
                } else {
                  alert(`수집 실패: ${collectResult.error || "알 수 없는 오류"}`);
                  // 키워드는 추가되었으므로 새로고침
                  await fetchAds();
                }
              } catch (e) {
                console.error("Failed to add keyword:", e);
                alert("키워드 추가 중 오류 발생");
              }
            }}
          />
        </div>

        <div className="h-px bg-border/50 my-4" />

        <GlassButton
          size="sm"
          onClick={fetchAds}
          className="w-full"
          contentClassName="flex items-center justify-center gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          <span>Refresh</span>
        </GlassButton>

        <p className="text-xs text-muted-foreground mt-4 text-center">
          © 2026 Ad Reference Gallery
        </p>
      </aside>

      {/* 메인 콘텐츠 */}
      <main className="flex-1 p-8 relative z-10">
        {/* 헤더 */}
        <div className="glass-header text-primary-foreground rounded-xl p-6 mb-6">
          <h1 className="text-2xl font-light">{selectedKeyword || "Select a keyword"}</h1>
          <p className="text-primary-foreground/60 text-sm mt-1">Ad creatives from Meta Ad Library</p>
        </div>

        {/* 필터 영역 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {/* 날짜 필터 */}
          <div>
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2 block">
              Date Range
            </label>
            <Popover>
              <PopoverTrigger asChild>
                <button className="glass-card w-full flex items-center justify-between px-4 py-2.5 rounded-lg text-sm text-foreground">
                  <div className="flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-muted-foreground" />
                    <span>
                      {dateRange?.from ? (
                        dateRange.to ? (
                          <>
                            {format(dateRange.from, "yyyy-MM-dd")} ~ {format(dateRange.to, "yyyy-MM-dd")}
                          </>
                        ) : (
                          format(dateRange.from, "yyyy-MM-dd")
                        )
                      ) : (
                        "Select date range"
                      )}
                    </span>
                  </div>
                  <ChevronDown className="w-4 h-4 text-muted-foreground" />
                </button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="start">
                <CalendarComponent
                  mode="range"
                  selected={dateRange}
                  onSelect={setDateRange}
                  numberOfMonths={2}
                />
              </PopoverContent>
            </Popover>
          </div>

          {/* 광고주 필터 */}
          <div>
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2 block">
              Advertiser
            </label>
            <Popover open={advertiserDropdownOpen} onOpenChange={setAdvertiserDropdownOpen}>
              <PopoverTrigger asChild>
                <button className="glass-card w-full flex items-center justify-between px-4 py-2.5 rounded-lg text-sm text-foreground">
                  <span className="truncate">
                    {selectedAdvertisers.length === 0
                      ? "Click to select (all if none)"
                      : `${selectedAdvertisers.length} selected`}
                  </span>
                  <ChevronDown className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                </button>
              </PopoverTrigger>
              <PopoverContent className="w-72 p-2" align="start">
                <div className="max-h-60 overflow-y-auto space-y-1">
                  {availableAdvertisers.map((advertiser) => (
                    <label
                      key={advertiser}
                      className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-accent cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={selectedAdvertisers.includes(advertiser)}
                        onChange={() => toggleAdvertiser(advertiser)}
                        className="rounded border-border"
                      />
                      <span className="text-sm text-foreground truncate">{advertiser}</span>
                    </label>
                  ))}
                </div>
                {selectedAdvertisers.length > 0 && (
                  <button
                    onClick={() => setSelectedAdvertisers([])}
                    className="w-full mt-2 py-1.5 text-xs text-muted-foreground hover:text-foreground border-t border-border"
                  >
                    Clear all
                  </button>
                )}
              </PopoverContent>
            </Popover>
          </div>
        </div>

        {/* 선택된 광고주 태그 */}
        {selectedAdvertisers.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4">
            {selectedAdvertisers.map((advertiser) => (
              <span
                key={advertiser}
                className="glass-card inline-flex items-center gap-1 px-3 py-1.5 text-foreground text-xs rounded-full"
              >
                {advertiser}
                <button
                  onClick={() => toggleAdvertiser(advertiser)}
                  className="hover:text-foreground/70 transition-colors"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
          </div>
        )}

        {/* 통계 */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="glass-card rounded-xl p-4 text-center">
            <div className="text-3xl font-light text-foreground">{filteredAds.length}</div>
            <div className="text-xs text-muted-foreground uppercase tracking-wide mt-1">Total Ads</div>
          </div>
          <div className="glass-card rounded-xl p-4 text-center">
            <div className="text-3xl font-light text-foreground">{uniqueAdvertisers}</div>
            <div className="text-xs text-muted-foreground uppercase tracking-wide mt-1">Advertisers</div>
          </div>
        </div>

        <div className="h-px bg-border/30 mb-6" />

        {/* 갤러리 */}
        {loading ? (
          <div className="text-center text-muted-foreground py-12">Loading...</div>
        ) : filteredAds.length === 0 ? (
          <div className="text-center text-muted-foreground py-12">
            No ads found. Run the pipeline first.
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
            {filteredAds.map((ad, idx) => (
              <AdCard
                key={`${ad._source_file}-${idx}`}
                imageUrl={ad.image_urls?.[0] || ""}
                pageName={ad.page_name || "Unknown"}
                collectedAt={ad._collected_at || ""}
                adText={Array.isArray(ad.ad_text) ? ad.ad_text.join("\n") : ad.ad_text}
                onDescriptionClick={() => {
                  setSelectedAd(ad);
                  setModalOpen(true);
                }}
              />
            ))}
          </div>
        )}
      </main>

      {/* 상세 모달 */}
      <AdDetailModal
        ad={selectedAd}
        open={modalOpen}
        onOpenChange={setModalOpen}
      />
    </div>
  );
}
