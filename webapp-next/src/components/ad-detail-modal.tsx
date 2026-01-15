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
      <DialogContent className="max-w-5xl w-[90vw] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-xl">{ad.page_name}</DialogTitle>
          <p className="text-sm text-muted-foreground">{ad._collected_at?.slice(0, 10)}</p>
        </DialogHeader>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mt-6">
          {/* 이미지 */}
          <div className="aspect-square rounded-xl overflow-hidden bg-gray-100 max-h-[500px]">
            {imageUrl && (
              <img
                src={imageUrl}
                alt={ad.page_name || "Ad"}
                className="w-full h-full object-cover"
              />
            )}
          </div>

          {/* 텍스트 정보 */}
          <div className="space-y-6">
            <div>
              <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-3">
                Ad Copy
              </h4>
              <div className="glass-card rounded-xl p-5 text-sm text-foreground leading-relaxed whitespace-pre-wrap min-h-[200px]">
                {adText || "No ad copy available"}
              </div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
