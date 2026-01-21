"use client";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ExternalLink } from "lucide-react";

interface Ad {
  page_name?: string;
  ad_text?: string[];
  image_urls?: string[];
  permanent_image_url?: string;
  r2_image_url?: string;
  _collected_at?: string;
  landing_url?: string;
}

interface AdDetailModalProps {
  ad: Ad | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AdDetailModal({ ad, open, onOpenChange }: AdDetailModalProps) {
  if (!ad) return null;

  // 영구 URL 우선, 없으면 원본 이미지 URL 사용
  const imageUrl = ad.permanent_image_url || ad.r2_image_url || ad.image_urls?.[0] || "";
  const adText = Array.isArray(ad.ad_text) ? ad.ad_text.join("\n") : ad.ad_text || "";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[1000px] max-w-[95vw] max-h-[92vh] overflow-y-auto p-10">
        <DialogHeader className="pb-4">
          <DialogTitle className="text-xl">{ad.page_name}</DialogTitle>
          <p className="text-sm text-muted-foreground">{ad._collected_at?.slice(0, 10)}</p>
          {ad.landing_url && (
            <a
              href={ad.landing_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-800 hover:underline mt-1 transition-colors"
            >
              <ExternalLink className="w-4 h-4" />
              <span className="truncate max-w-[400px]">{ad.landing_url}</span>
            </a>
          )}
        </DialogHeader>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-10 mt-6">
          {/* 이미지 - 원본 비율 유지 */}
          <div className="flex items-center justify-center rounded-xl overflow-hidden bg-gray-100 max-h-[600px]">
            {imageUrl && (
              <img
                src={imageUrl}
                alt={ad.page_name || "Ad"}
                className="max-w-full max-h-[600px] object-contain"
              />
            )}
          </div>

          {/* 텍스트 정보 */}
          <div className="space-y-6">
            <div>
              <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-3">
                Ad Copy
              </h4>
              <div className="glass-card rounded-xl p-6 text-sm text-foreground leading-relaxed whitespace-pre-wrap min-h-[250px]">
                {adText || "No ad copy available"}
              </div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
