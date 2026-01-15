"use client";

import { useState } from "react";

interface AdCardProps {
  imageUrl: string;
  pageName: string;
  collectedAt: string;
  adText?: string;
  onDescriptionClick?: () => void;
}

export function AdCard({
  imageUrl,
  pageName,
  collectedAt,
  adText,
  onDescriptionClick,
}: AdCardProps) {
  const [imageError, setImageError] = useState(false);

  return (
    <div className="glass-card rounded-xl overflow-hidden">
      {/* 이미지 */}
      <div className="relative aspect-square">
        {!imageError ? (
          <img
            src={imageUrl}
            alt={pageName}
            className="w-full h-full object-cover"
            onError={() => setImageError(true)}
          />
        ) : (
          <div className="w-full h-full bg-gray-100/50 flex items-center justify-center text-gray-400">
            No Image
          </div>
        )}
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
