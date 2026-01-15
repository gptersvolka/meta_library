"use client";

import { CornerRightUp } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

interface KeywordInputProps {
  placeholder?: string;
  onSubmit?: (value: string) => void | Promise<void>;
  className?: string;
}

export function KeywordInput({
  placeholder = "키워드 추가",
  onSubmit,
  className,
}: KeywordInputProps) {
  const [inputValue, setInputValue] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async () => {
    if (!inputValue.trim() || submitted) return;

    setSubmitted(true);
    try {
      await onSubmit?.(inputValue.trim());
      setInputValue("");
    } finally {
      setTimeout(() => {
        setSubmitted(false);
      }, 1000);
    }
  };

  return (
    <div className={cn("w-full", className)}>
      <div className="relative w-full">
        <input
          type="text"
          placeholder={placeholder}
          className={cn(
            "w-full rounded-2xl pl-4 pr-10 py-3",
            "bg-black/5 dark:bg-white/5",
            "placeholder:text-black/50 dark:placeholder:text-white/50",
            "border border-black/10 dark:border-white/10",
            "text-black dark:text-white text-sm",
            "focus:outline-none focus:ring-2 focus:ring-purple-300/50",
            "transition-all duration-200"
          )}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              handleSubmit();
            }
          }}
          disabled={submitted}
        />
        <button
          onClick={handleSubmit}
          className={cn(
            "absolute right-2 top-1/2 -translate-y-1/2 rounded-xl p-1.5",
            submitted ? "bg-purple-100" : "bg-black/5 dark:bg-white/5",
            "hover:bg-purple-100 transition-colors"
          )}
          type="button"
          disabled={submitted}
        >
          {submitted ? (
            <div
              className="w-4 h-4 bg-purple-500 rounded-sm animate-spin"
              style={{ animationDuration: "1s" }}
            />
          ) : (
            <CornerRightUp
              className={cn(
                "w-4 h-4 transition-opacity text-purple-600",
                inputValue ? "opacity-100" : "opacity-40"
              )}
            />
          )}
        </button>
      </div>
      <p className="mt-2 h-4 text-[10px] text-center text-black/50 dark:text-white/50">
        {submitted ? "추가 중..." : "Enter로 키워드 추가"}
      </p>
    </div>
  );
}
