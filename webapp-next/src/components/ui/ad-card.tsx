"use client";

import { useState } from "react";
import Image from "next/image";

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
    <div className="bg-white rounded-lg shadow-sm border border-gray-100 overflow-hidden">
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
          <div className="w-full h-full bg-gray-100 flex items-center justify-center text-gray-400">
            No Image
          </div>
        )}
      </div>

      {/* 정보 영역 */}
      <div className="p-3">
        <h3 className="text-sm font-medium text-gray-900 truncate">
          {pageName}
        </h3>
        <p className="text-xs text-gray-500 mt-1">
          {collectedAt?.slice(0, 10)}
        </p>
      </div>

      {/* 구분선 */}
      <div className="h-px bg-gray-100" />

      {/* Description 버튼 */}
      <button
        onClick={onDescriptionClick}
        className="w-full py-3 text-sm text-blue-500 hover:text-blue-600 hover:bg-gray-50 transition-colors"
      >
        description
      </button>
    </div>
  );
}
