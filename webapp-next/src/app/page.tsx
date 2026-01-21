"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { AdCard } from "@/components/ui/ad-card";
import { AdDetailModal } from "@/components/ad-detail-modal";
import { GlassButton } from "@/components/ui/glass-button";
import { KeywordInput } from "@/components/ui/keyword-input";
import { PaginationAnt } from "@/components/ui/pagination-ant";
import { ChevronDown, X, Sparkles, Trash2, Star, User, Hash, Play, Loader2, Clock } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { CalendarNew } from "@/components/ui/calendar-new";
import { startOfDay, endOfDay } from "date-fns";

interface Ad {
  page_name?: string;
  ad_text?: string[];
  image_urls?: string[];
  video_urls?: string[];
  permanent_image_url?: string; // imgbb 영구 URL (우선 사용)
  r2_image_url?: string; // (구) R2 URL (하위 호환)
  _collected_at?: string;
  _source_file?: string;
  landing_url?: string;
  _keyword?: string; // 하이라이트용 키워드 추가
}

interface AdsData {
  keywords: string[];
  ads: Record<string, Ad[]>;
}

interface HighlightAd {
  id: string;
  image_url: string;
  page_name: string;
  ad_text?: string[];
  keyword: string;
  collected_at: string;
  highlighted_at: string;
  landing_url?: string;
}

// 영구 URL 우선, 없으면 원본 이미지 URL 사용
const getImageUrl = (ad: Ad): string => {
  return ad.permanent_image_url || ad.r2_image_url || ad.image_urls?.[0] || "";
};

export default function Home() {
  const [data, setData] = useState<AdsData>({ keywords: [], ads: {} });
  const [selectedKeyword, setSelectedKeyword] = useState<string>("");
  const [selectedAd, setSelectedAd] = useState<Ad | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  // 하이라이트 관련 상태
  const [highlights, setHighlights] = useState<HighlightAd[]>([]);
  const [highlightedIds, setHighlightedIds] = useState<Set<string>>(new Set());
  const [viewMode, setViewMode] = useState<"keywords" | "highlights">("keywords");
  const [selectedHighlightKeywords, setSelectedHighlightKeywords] = useState<string[]>([]);

  // 날짜 필터 (기본값: 이번 달 1일 ~ 오늘)
  const [dateRange, setDateRange] = useState<{ from: Date | null; to: Date | null }>(() => {
    const now = new Date();
    const firstDayOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);
    return {
      from: firstDayOfMonth,
      to: now,
    };
  });

  // 광고주 필터 (null = 전체 선택, [] = 아무것도 선택 안됨)
  const [selectedAdvertisers, setSelectedAdvertisers] = useState<string[] | null>(null);
  const [advertiserDropdownOpen, setAdvertiserDropdownOpen] = useState(false);

  // 페이지네이션 (7열 x 10줄 = 70개)
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 70;

  // 수집 상태
  const [isCollecting, setIsCollecting] = useState(false);

  const fetchAds = useCallback(async () => {
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
  }, [selectedKeyword]);

  // 모든 키워드 수집 실행
  const collectAllKeywords = async () => {
    if (isCollecting) return;

    if (!confirm("등록된 모든 키워드에 대해 광고 수집을 시작합니다.\n키워드 수에 따라 시간이 소요될 수 있습니다.\n\n계속하시겠습니까?")) {
      return;
    }

    setIsCollecting(true);
    try {
      const res = await fetch("/api/collect/all", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      const result = await res.json();

      if (res.ok) {
        alert(`수집 완료!\n${result.message}`);
        await fetchAds();
      } else {
        alert(`수집 실패: ${result.error || result.message}`);
      }
    } catch (e) {
      console.error("Failed to collect all keywords:", e);
      alert("수집 중 오류 발생");
    } finally {
      setIsCollecting(false);
    }
  };

  // 하이라이트 목록 가져오기
  const fetchHighlights = useCallback(async () => {
    try {
      const res = await fetch("/api/highlights");
      const json = await res.json();
      setHighlights(json.highlights || []);
      // ID Set 업데이트
      const ids = new Set<string>((json.highlights || []).map((h: HighlightAd) => h.id));
      setHighlightedIds(ids);
    } catch (e) {
      console.error("Failed to fetch highlights:", e);
    }
  }, []);

  // 하이라이트 토글
  const toggleHighlight = async (ad: Ad, keyword: string) => {
    const imageUrl = getImageUrl(ad);
    if (!imageUrl) return;

    // 이미지 URL에서 ID 생성 (API와 동일한 로직)
    let id: string;
    try {
      const url = new URL(imageUrl);
      const filename = url.pathname.split("/").pop() || "";
      id = filename.replace(/\.[^.]+$/, "");
    } catch {
      id = btoa(imageUrl).slice(0, 20);
    }

    const isCurrentlyHighlighted = highlightedIds.has(id);

    try {
      if (isCurrentlyHighlighted) {
        // 제거
        await fetch("/api/highlights", {
          method: "DELETE",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id }),
        });
        setHighlightedIds((prev) => {
          const next = new Set(prev);
          next.delete(id);
          return next;
        });
        setHighlights((prev) => prev.filter((h) => h.id !== id));
      } else {
        // 추가
        const res = await fetch("/api/highlights", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            image_url: imageUrl,
            page_name: ad.page_name,
            ad_text: ad.ad_text,
            keyword,
            collected_at: ad._collected_at,
            landing_url: ad.landing_url,
          }),
        });
        const result = await res.json();
        if (result.success && result.highlight) {
          setHighlightedIds((prev) => new Set(prev).add(id));
          setHighlights((prev) => [result.highlight, ...prev]);
        }
      }
    } catch (e) {
      console.error("Failed to toggle highlight:", e);
    }
  };

  // 광고의 하이라이트 ID 계산
  const getAdHighlightId = (ad: Ad): string => {
    const imageUrl = getImageUrl(ad);
    if (!imageUrl) return "";
    try {
      const url = new URL(imageUrl);
      const filename = url.pathname.split("/").pop() || "";
      return filename.replace(/\.[^.]+$/, "");
    } catch {
      return btoa(imageUrl).slice(0, 20);
    }
  };

  useEffect(() => {
    fetchAds();
    fetchHighlights();
  }, [fetchAds, fetchHighlights]);

  const currentAds = useMemo(() => data.ads[selectedKeyword] || [], [data.ads, selectedKeyword]);

  // 유효한 이미지가 있는 광고만 필터링
  // Meta CDN URL은 시간이 지나면 만료되므로, permanent_image_url이 있는 광고만 표시
  const validAds = useMemo(() => {
    return currentAds.filter((ad) => {
      // 영구 URL이 있는 광고만 표시 (imgbb 또는 R2)
      if (ad.permanent_image_url || ad.r2_image_url) return true;
      // 영구 URL이 없으면 표시하지 않음 (Meta CDN URL은 만료됨)
      return false;
    });
  }, [currentAds]);

  // 날짜 필터 적용
  const dateFilteredAds = useMemo(() => {
    if (!dateRange?.from && !dateRange?.to) return validAds;

    return validAds.filter((ad) => {
      if (!ad._collected_at) return true;
      const adDate = new Date(ad._collected_at);

      // 시작일과 종료일을 하루의 시작/끝으로 설정하여 같은 날짜도 포함되도록
      const fromDate = dateRange.from ? startOfDay(dateRange.from) : null;
      const toDate = dateRange.to ? endOfDay(dateRange.to) : null;

      if (fromDate && toDate) {
        return adDate >= fromDate && adDate <= toDate;
      } else if (fromDate) {
        return adDate >= fromDate;
      } else if (toDate) {
        return adDate <= toDate;
      }
      return true;
    });
  }, [validAds, dateRange]);

  // 광고주 목록 (날짜 필터 적용 후)
  const availableAdvertisers = useMemo(() => {
    const advertisers = new Set(dateFilteredAds.map((ad) => ad.page_name).filter(Boolean));
    return Array.from(advertisers).sort() as string[];
  }, [dateFilteredAds]);

  // 최종 필터링된 광고 (최신순 정렬)
  // selectedAdvertisers: null = 전체 선택, [] = 아무것도 선택 안됨, [...] = 선택된 항목만
  const filteredAds = useMemo(() => {
    let ads = dateFilteredAds;
    if (selectedAdvertisers === null) {
      // null = 전체 선택 (필터 없음)
    } else if (selectedAdvertisers.length === 0) {
      // 빈 배열 = 아무것도 선택 안됨 → 결과 없음
      ads = [];
    } else {
      // 선택된 항목만 필터링
      ads = ads.filter((ad) => selectedAdvertisers.includes(ad.page_name || ""));
    }
    // 날짜 역순 정렬 (최신순)
    return [...ads].sort((a, b) => {
      const dateA = a._collected_at ? new Date(a._collected_at).getTime() : 0;
      const dateB = b._collected_at ? new Date(b._collected_at).getTime() : 0;
      return dateB - dateA;
    });
  }, [dateFilteredAds, selectedAdvertisers]);

  const uniqueAdvertisers = new Set(filteredAds.map((ad) => ad.page_name)).size;

  // 하이라이트 뷰를 위한 필터링
  const highlightKeywords = useMemo(() => {
    const keywords = new Set(highlights.map((h) => h.keyword).filter(Boolean));
    return Array.from(keywords).sort();
  }, [highlights]);

  const filteredHighlights = useMemo(() => {
    let filtered = highlights;

    // 날짜 필터
    if (dateRange?.from || dateRange?.to) {
      filtered = filtered.filter((h) => {
        if (!h.collected_at) return true;
        const adDate = new Date(h.collected_at);
        const fromDate = dateRange.from ? startOfDay(dateRange.from) : null;
        const toDate = dateRange.to ? endOfDay(dateRange.to) : null;

        if (fromDate && toDate) {
          return adDate >= fromDate && adDate <= toDate;
        } else if (fromDate) {
          return adDate >= fromDate;
        } else if (toDate) {
          return adDate <= toDate;
        }
        return true;
      });
    }

    // 광고주 필터 (null = 전체, [] = 없음, [...] = 선택된 것만)
    if (selectedAdvertisers === null) {
      // 전체 선택 - 필터 없음
    } else if (selectedAdvertisers.length === 0) {
      // 아무것도 선택 안됨 - 결과 없음
      filtered = [];
    } else {
      filtered = filtered.filter((h) => selectedAdvertisers.includes(h.page_name));
    }

    // 키워드 필터
    if (selectedHighlightKeywords.length > 0) {
      filtered = filtered.filter((h) => selectedHighlightKeywords.includes(h.keyword));
    }

    // 최신순 정렬 (하이라이트된 시간 기준)
    return [...filtered].sort((a, b) => {
      const dateA = new Date(a.highlighted_at).getTime();
      const dateB = new Date(b.highlighted_at).getTime();
      return dateB - dateA;
    });
  }, [highlights, dateRange, selectedAdvertisers, selectedHighlightKeywords]);

  // 하이라이트 뷰의 광고주 목록
  const highlightAdvertisers = useMemo(() => {
    const advertisers = new Set(highlights.map((h) => h.page_name).filter(Boolean));
    return Array.from(advertisers).sort();
  }, [highlights]);

  // 현재 페이지에 해당하는 광고만 추출
  const paginatedAds = useMemo(() => {
    const startIndex = (currentPage - 1) * pageSize;
    const endIndex = startIndex + pageSize;
    return filteredAds.slice(startIndex, endIndex);
  }, [filteredAds, currentPage, pageSize]);

  // 하이라이트 페이지네이션
  const paginatedHighlights = useMemo(() => {
    const startIndex = (currentPage - 1) * pageSize;
    const endIndex = startIndex + pageSize;
    return filteredHighlights.slice(startIndex, endIndex);
  }, [filteredHighlights, currentPage, pageSize]);

  // 키워드 변경 시 광고주 필터 초기화 (null = 전체 선택)
  useEffect(() => {
    setSelectedAdvertisers(null);
  }, [selectedKeyword]);

  // 필터 변경 시 페이지 리셋
  useEffect(() => {
    setCurrentPage(1);
  }, [selectedKeyword, dateRange, selectedAdvertisers, viewMode, selectedHighlightKeywords]);

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    // 페이지 변경 시 상단으로 스크롤
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  // toggleAdvertiser는 더 이상 사용되지 않음 - 직접 로직 사용

  const deleteKeyword = async (keyword: string) => {
    if (!confirm(`"${keyword}" 키워드를 삭제하시겠습니까?\n\n(수집된 광고 데이터는 유지됩니다)`)) {
      return;
    }

    try {
      const res = await fetch("/api/keywords", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ keyword }),
      });

      if (res.ok) {
        // 삭제된 키워드가 현재 선택된 것이면 다른 키워드로 전환
        if (selectedKeyword === keyword) {
          const remainingKeywords = data.keywords.filter((k) => k !== keyword);
          setSelectedKeyword(remainingKeywords[0] || "");
        }
        // 데이터 새로고침
        await fetchAds();
      } else {
        const result = await res.json();
        alert(result.error || "키워드 삭제 실패");
      }
    } catch (e) {
      console.error("Failed to delete keyword:", e);
      alert("키워드 삭제 중 오류 발생");
    }
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

      {/* 사이드바 - 화면에 고정 */}
      <aside className="w-64 glass-sidebar p-6 flex flex-col fixed top-0 left-0 h-screen z-20">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-foreground/70" />
          <h1 className="text-xl font-semibold text-foreground">Ad Reference</h1>
        </div>
        <p className="text-xs text-muted-foreground mt-1">Meta Ad Library Collection</p>

        <div className="h-px bg-border/50 my-6" />

        {/* Highlights 섹션 */}
        <h2 className="text-sm font-medium text-foreground/70 mb-2">Highlights</h2>
        <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground/70 mb-3">
          <Clock className="w-3 h-3" />
          <span>매주 월/금 오전 9시 자동 수집</span>
        </div>
        <button
          onClick={() => {
            setViewMode("highlights");
            setSelectedHighlightKeywords([]);
          }}
          className={`glass-keyword w-full text-left px-3 py-2 rounded-lg text-sm flex items-center gap-2 ${
            viewMode === "highlights" ? "active" : ""
          }`}
        >
          <Star className={`w-4 h-4 ${viewMode === "highlights" ? "fill-yellow-400 text-yellow-400" : ""}`} />
          <span>Highlights</span>
          <span className="ml-auto text-xs text-muted-foreground">{highlights.length}</span>
        </button>

        <div className="h-px bg-border/50 my-6" />

        <h2 className="text-sm font-medium text-foreground/70 mb-3">Keywords</h2>
        <div className="space-y-2 flex-1 overflow-y-auto">
          {data.keywords.map((keyword) => (
            <div
              key={keyword}
              className="group relative"
            >
              <button
                onClick={() => {
                  setViewMode("keywords");
                  setSelectedKeyword(keyword);
                }}
                className={`glass-keyword w-full text-left px-3 py-2 pr-8 rounded-lg text-sm ${
                  viewMode === "keywords" && selectedKeyword === keyword ? "active" : ""
                }`}
              >
                {keyword}
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  deleteKeyword(keyword);
                }}
                className="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity duration-200 p-1 rounded hover:bg-red-100 text-muted-foreground hover:text-red-500"
                title="키워드 삭제"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>

        {/* 키워드 추가 입력란 */}
        <div className="mt-4">
          <KeywordInput
            placeholder="키워드 추가"
            onSubmit={async (keyword) => {
              try {
                // 1. 키워드 저장 (이미 존재해도 OK)
                const saveRes = await fetch("/api/keywords", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ keyword }),
                });
                const saveResult = await saveRes.json();

                if (!saveRes.ok && !saveResult.success) {
                  alert(saveResult.error || "키워드 추가 실패");
                  return;
                }

                // 2. 즉시 수집 실행
                const message = saveResult.alreadyExists
                  ? `"${keyword}" 키워드가 이미 존재합니다.\n광고 수집을 시작합니다. (1~2분 소요)`
                  : `"${keyword}" 키워드 추가됨!\n광고 수집을 시작합니다. (1~2분 소요)`;
                alert(message);

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
          onClick={collectAllKeywords}
          disabled={isCollecting}
          className="w-full"
          contentClassName="flex items-center justify-center gap-2"
        >
          {isCollecting ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>수집 중...</span>
            </>
          ) : (
            <>
              <Play className="w-4 h-4" />
              <span>지금 수집</span>
            </>
          )}
        </GlassButton>

        <p className="text-xs text-muted-foreground mt-4 text-center">
          © 2026 Ad Reference Gallery
        </p>
      </aside>

      {/* 메인 콘텐츠 - 사이드바 너비만큼 왼쪽 여백 */}
      <main className="flex-1 p-8 relative z-10 ml-64">
        {/* 헤더 */}
        <div className="glass-header text-primary-foreground rounded-xl p-6 mb-6">
          <h1 className="text-2xl font-light flex items-center gap-3">
            {viewMode === "highlights" && <Star className="w-6 h-6 fill-yellow-400 text-yellow-400" />}
            {viewMode === "highlights" ? "Highlights" : (selectedKeyword || "Select a keyword")}
          </h1>
          <p className="text-primary-foreground/60 text-sm mt-1">
            {viewMode === "highlights"
              ? "Your saved ad creatives"
              : "Ad creatives from Meta Ad Library"}
          </p>
        </div>

        {/* 필터 영역 - 왼쪽 정렬, 너비 축소 */}
        <div className="flex flex-wrap items-end gap-4 mb-6">
          {/* 날짜 필터 */}
          <div className="w-auto">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2 block">
              Date Range
            </label>
            <CalendarNew
              value={dateRange}
              onChange={setDateRange}
            />
          </div>

          {/* 광고주 필터 */}
          <div className="w-auto">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2 block">
              Advertiser
            </label>
            <Popover open={advertiserDropdownOpen} onOpenChange={setAdvertiserDropdownOpen}>
              <PopoverTrigger asChild>
                <button className="glass-card flex items-center justify-between gap-2 px-3 py-2 rounded-lg text-sm text-foreground min-w-[220px]">
                  <User className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                  <span className="truncate flex-1 text-left">
                    {selectedAdvertisers === null
                      ? "All advertisers"
                      : selectedAdvertisers.length === 0
                        ? "None selected"
                        : `${selectedAdvertisers.length} selected`}
                  </span>
                  <ChevronDown className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                </button>
              </PopoverTrigger>
              <PopoverContent className="w-72 p-2" align="start">
                {(() => {
                  const currentAdvertisers = viewMode === "highlights" ? highlightAdvertisers : availableAdvertisers;
                  // null = 전체 선택, [] = 아무것도 선택 안됨
                  const isAllSelected = selectedAdvertisers === null;

                  return (
                    <>
                      <div className="max-h-60 overflow-y-auto space-y-1">
                        {currentAdvertisers.map((advertiser) => {
                          // null = 전체 선택 (모두 체크), 아니면 포함된 것만 체크
                          const isChecked = selectedAdvertisers === null || selectedAdvertisers.includes(advertiser);
                          return (
                            <label
                              key={advertiser}
                              className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-accent cursor-pointer"
                            >
                              <input
                                type="checkbox"
                                checked={isChecked}
                                onChange={() => {
                                  if (selectedAdvertisers === null) {
                                    // 전체 선택 상태에서 하나 해제 → 해당 항목 제외한 나머지 선택
                                    setSelectedAdvertisers(currentAdvertisers.filter(a => a !== advertiser));
                                  } else if (selectedAdvertisers.includes(advertiser)) {
                                    // 선택된 항목 해제
                                    const newSelection = selectedAdvertisers.filter(a => a !== advertiser);
                                    setSelectedAdvertisers(newSelection);
                                  } else {
                                    // 선택 안된 항목 추가
                                    const newSelection = [...selectedAdvertisers, advertiser];
                                    // 모든 항목이 선택되면 null로 (전체 선택 상태)
                                    if (newSelection.length === currentAdvertisers.length) {
                                      setSelectedAdvertisers(null);
                                    } else {
                                      setSelectedAdvertisers(newSelection);
                                    }
                                  }
                                }}
                                className="rounded border-border"
                              />
                              <span className="text-sm text-foreground truncate">{advertiser}</span>
                            </label>
                          );
                        })}
                      </div>
                      {isAllSelected ? (
                        <button
                          onClick={() => setSelectedAdvertisers([])}
                          className="w-full mt-2 py-1.5 text-xs text-muted-foreground hover:text-foreground border-t border-border"
                        >
                          Clear all
                        </button>
                      ) : (
                        <button
                          onClick={() => setSelectedAdvertisers(null)}
                          className="w-full mt-2 py-1.5 text-xs text-muted-foreground hover:text-foreground border-t border-border"
                        >
                          Select all
                        </button>
                      )}
                    </>
                  );
                })()}
              </PopoverContent>
            </Popover>
          </div>

          {/* 키워드 필터 - 하이라이트 뷰에서만 표시 */}
          {viewMode === "highlights" && highlightKeywords.length > 0 && (
            <div className="w-auto">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2 block">
                Keyword
              </label>
              <Popover>
                <PopoverTrigger asChild>
                  <button className="glass-card flex items-center justify-between gap-2 px-3 py-2 rounded-lg text-sm text-foreground min-w-[220px]">
                    <Hash className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                    <span className="truncate flex-1 text-left">
                      {selectedHighlightKeywords.length === 0
                        ? "All keywords"
                        : `${selectedHighlightKeywords.length} selected`}
                    </span>
                    <ChevronDown className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                  </button>
                </PopoverTrigger>
                <PopoverContent className="w-72 p-2" align="start">
                  <div className="max-h-60 overflow-y-auto space-y-1">
                    {highlightKeywords.map((kw) => (
                      <label
                        key={kw}
                        className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-accent cursor-pointer"
                      >
                        <input
                          type="checkbox"
                          checked={selectedHighlightKeywords.includes(kw)}
                          onChange={() => {
                            setSelectedHighlightKeywords((prev) =>
                              prev.includes(kw)
                                ? prev.filter((k) => k !== kw)
                                : [...prev, kw]
                            );
                          }}
                          className="rounded border-border"
                        />
                        <span className="text-sm text-foreground truncate">{kw}</span>
                      </label>
                    ))}
                  </div>
                  {selectedHighlightKeywords.length > 0 && (
                    <button
                      onClick={() => setSelectedHighlightKeywords([])}
                      className="w-full mt-2 py-1.5 text-xs text-muted-foreground hover:text-foreground border-t border-border"
                    >
                      Clear all
                    </button>
                  )}
                </PopoverContent>
              </Popover>
            </div>
          )}
        </div>

        {/* 선택된 필터 태그 */}
        {((selectedAdvertisers !== null && selectedAdvertisers.length > 0) || selectedHighlightKeywords.length > 0) && (
          <div className="flex flex-wrap gap-2 mb-4">
            {/* Advertiser 태그 - 파란색 계열 */}
            {selectedAdvertisers !== null && selectedAdvertisers.map((advertiser) => (
              <span
                key={`adv-${advertiser}`}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-full bg-blue-50 text-blue-700 border border-blue-200"
              >
                <User className="w-3 h-3" />
                {advertiser}
                <button
                  onClick={() => {
                    const newSelection = selectedAdvertisers.filter(a => a !== advertiser);
                    setSelectedAdvertisers(newSelection);
                  }}
                  className="hover:text-blue-900 transition-colors ml-0.5"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
            {/* Keyword 태그 - 노란색/주황색 계열 */}
            {selectedHighlightKeywords.map((kw) => (
              <span
                key={`kw-${kw}`}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-full bg-amber-50 text-amber-700 border border-amber-200"
              >
                <Hash className="w-3 h-3" />
                {kw}
                <button
                  onClick={() => setSelectedHighlightKeywords((prev) => prev.filter((k) => k !== kw))}
                  className="hover:text-amber-900 transition-colors ml-0.5"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
          </div>
        )}

        {/* 통계 - 왼쪽 정렬, 너비 축소 */}
        <div className="flex gap-4 mb-6">
          <div className="glass-card rounded-xl px-6 py-3 text-center">
            <div className="text-2xl font-light text-foreground">
              {viewMode === "highlights" ? filteredHighlights.length : filteredAds.length}
            </div>
            <div className="text-xs text-muted-foreground uppercase tracking-wide">
              {viewMode === "highlights" ? "Highlighted" : "Total Ads"}
            </div>
          </div>
          <div className="glass-card rounded-xl px-6 py-3 text-center">
            <div className="text-2xl font-light text-foreground">
              {viewMode === "highlights"
                ? new Set(filteredHighlights.map((h) => h.page_name)).size
                : uniqueAdvertisers}
            </div>
            <div className="text-xs text-muted-foreground uppercase tracking-wide">Advertisers</div>
          </div>
        </div>

        <div className="h-px bg-border/30 mb-6" />

        {/* 갤러리 */}
        {loading ? (
          <div className="text-center text-muted-foreground py-12">Loading...</div>
        ) : viewMode === "highlights" ? (
          // 하이라이트 뷰
          filteredHighlights.length === 0 ? (
            <div className="text-center text-muted-foreground py-12">
              <Star className="w-12 h-12 mx-auto mb-4 text-muted-foreground/30" />
              <p>No highlights yet.</p>
              <p className="text-sm mt-1">Click the star icon on ads to save them here.</p>
            </div>
          ) : (
            <>
              <PaginationAnt
                current={currentPage}
                total={filteredHighlights.length}
                pageSize={pageSize}
                onChange={handlePageChange}
                className="mb-6 flex justify-end"
              />

              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
                {paginatedHighlights.map((highlight) => (
                  <AdCard
                    key={highlight.id}
                    imageUrl={highlight.image_url}
                    pageName={highlight.page_name}
                    collectedAt={highlight.collected_at}
                    isHighlighted={true}
                    onHighlightToggle={() => {
                      // 하이라이트에서 제거
                      fetch("/api/highlights", {
                        method: "DELETE",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ id: highlight.id }),
                      }).then(() => {
                        setHighlightedIds((prev) => {
                          const next = new Set(prev);
                          next.delete(highlight.id);
                          return next;
                        });
                        setHighlights((prev) => prev.filter((h) => h.id !== highlight.id));
                      });
                    }}
                    onDescriptionClick={() => {
                      setSelectedAd({
                        page_name: highlight.page_name,
                        ad_text: highlight.ad_text,
                        image_urls: [highlight.image_url],
                        _collected_at: highlight.collected_at,
                        landing_url: highlight.landing_url,
                      });
                      setModalOpen(true);
                    }}
                  />
                ))}
              </div>

              <PaginationAnt
                current={currentPage}
                total={filteredHighlights.length}
                pageSize={pageSize}
                onChange={handlePageChange}
                className="mt-6 flex justify-end"
              />
            </>
          )
        ) : filteredAds.length === 0 ? (
          <div className="text-center text-muted-foreground py-12">
            No ads found. Run the pipeline first.
          </div>
        ) : (
          <>
            {/* 상단 페이지네이션 */}
            <PaginationAnt
              current={currentPage}
              total={filteredAds.length}
              pageSize={pageSize}
              onChange={handlePageChange}
              className="mb-6 flex justify-end"
            />

            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
              {paginatedAds.map((ad, idx) => (
                <AdCard
                  key={`${ad._source_file}-${idx}`}
                  imageUrl={getImageUrl(ad)}
                  pageName={ad.page_name || "Unknown"}
                  collectedAt={ad._collected_at || ""}
                  isHighlighted={highlightedIds.has(getAdHighlightId(ad))}
                  onHighlightToggle={() => toggleHighlight(ad, selectedKeyword)}
                  onDescriptionClick={() => {
                    setSelectedAd(ad);
                    setModalOpen(true);
                  }}
                />
              ))}
            </div>

            {/* 하단 페이지네이션 */}
            <PaginationAnt
              current={currentPage}
              total={filteredAds.length}
              pageSize={pageSize}
              onChange={handlePageChange}
              className="mt-6 flex justify-end"
            />
          </>
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
