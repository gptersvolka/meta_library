"use client";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface Ad {
  page_name?: string;
  ad_text?: string[];
  image_urls?: string[];
  _collected_at?: string;
}

interface AdDetailModalProps {
  ad: Ad | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AdDetailModal({ ad, open, onOpenChange }: AdDetailModalProps) {
  if (!ad) return null;

  const imageUrl = ad.image_urls?.[0] || "";
  const adText = Array.isArray(ad.ad_text) ? ad.ad_text.join("\n") : ad.ad_text || "";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>{ad.page_name}</DialogTitle>
          <p className="text-sm text-gray-500">{ad._collected_at?.slice(0, 10)}</p>
        </DialogHeader>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
          {/* 이미지 */}
          <div className="aspect-square rounded-lg overflow-hidden bg-gray-100">
            {imageUrl && (
              <img
                src={imageUrl}
                alt={ad.page_name || "Ad"}
                className="w-full h-full object-cover"
              />
            )}
          </div>

          {/* 텍스트 정보 */}
          <div className="space-y-4">
            <div>
              <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                Ad Copy
              </h4>
              <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-700">
                {adText || "No ad copy available"}
              </div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
