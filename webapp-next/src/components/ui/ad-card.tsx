"use client";

import { useState } from "react";
import { Star, Trash2 } from "lucide-react";
import Image from "next/image";

interface AdCardProps {
  imageUrl: string;
  pageName: string;
  collectedAt: string;
  onDescriptionClick?: () => void;
  isHighlighted?: boolean;
  onHighlightToggle?: () => void;
  onDelete?: () => void;
}

export function AdCard({
  imageUrl,
  pageName,
  collectedAt,
  onDescriptionClick,
  isHighlighted = false,
  onHighlightToggle,
  onDelete,
}: AdCardProps) {
  const [imageError, setImageError] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);

  return (
    <div className="glass-card rounded-xl overflow-hidden">
      {/* 이미지 */}
      <div className="relative aspect-square group">
        {!imageError ? (
          <>
            {/* 로딩 플레이스홀더 */}
            {!isLoaded && (
              <div className="absolute inset-0 bg-gray-100/50 animate-pulse" />
            )}
            <Image
              src={imageUrl}
              alt={pageName}
              fill
              sizes="(max-width: 768px) 50vw, (max-width: 1024px) 25vw, 14vw"
              className={`object-cover transition-opacity duration-300 ${
                isLoaded ? "opacity-100" : "opacity-0"
              }`}
              onLoad={() => setIsLoaded(true)}
              onError={() => setImageError(true)}
              loading="lazy"
              quality={75}
            />
          </>
        ) : (
          <div className="w-full h-full bg-gray-100/50 flex items-center justify-center text-gray-400">
            No Image
          </div>
        )}
        {/* 버튼 그룹 - 우상단 (세로 배치) */}
        <div className="absolute top-2 right-2 flex flex-col gap-1.5 z-10">
          {/* 별표 버튼 */}
          {onHighlightToggle && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onHighlightToggle();
              }}
              className={`p-1.5 rounded-full transition-all duration-200 shadow-md ${
                isHighlighted
                  ? "bg-yellow-400 shadow-lg shadow-yellow-400/30"
                  : "bg-black/40 backdrop-blur-sm opacity-0 group-hover:opacity-100 hover:bg-black/60"
              }`}
            >
              <Star
                className={`w-4 h-4 transition-all duration-200 ${
                  isHighlighted
                    ? "fill-white text-white"
                    : "text-white hover:text-yellow-300"
                }`}
              />
            </button>
          )}
          {/* 삭제 버튼 */}
          {onDelete && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
              className="p-1.5 rounded-full transition-all duration-200 bg-black/40 backdrop-blur-sm shadow-md opacity-0 group-hover:opacity-100 hover:bg-red-500"
            >
              <Trash2 className="w-4 h-4 text-white transition-colors" />
            </button>
          )}
        </div>
      </div>

      {/* 정보 영역 */}
      <div className="px-3 py-2.5">
        <div className="flex items-center justify-between gap-2 min-h-[28px]">
          <div className="flex-1 min-w-0">
            <h3 className="text-xs font-medium text-foreground truncate">
              {pageName}
            </h3>
            <p className="text-[10px] text-muted-foreground mt-0.5">
              {collectedAt?.slice(0, 10)}
            </p>
          </div>
          {/* Glass pill 버튼 - 세로 가운데 정렬 */}
          <button
            onClick={onDescriptionClick}
            className="glass-pill-button"
          >
            description
          </button>
        </div>
      </div>
    </div>
  );
}
