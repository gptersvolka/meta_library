"use client";

import React, { useState, useRef, useCallback, useMemo, useEffect } from "react";
import {
  format,
  startOfMonth,
  endOfMonth,
  eachDayOfInterval,
  isSameMonth,
  isSameDay,
  addMonths,
  subMonths,
  isWithinInterval,
  startOfWeek,
  endOfWeek,
  isAfter,
  isBefore,
} from "date-fns";
import { ko } from "date-fns/locale";
import clsx from "clsx";
import { Material } from "@/components/ui/material-1";
import { useClickOutside } from "@/components/ui/use-click-outside";

interface DateRange {
  from: Date | null;
  to: Date | null;
}

interface CalendarNewProps {
  value?: DateRange;
  onChange?: (range: DateRange) => void;
  className?: string;
}

const ChevronLeft = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
    <path
      fillRule="evenodd"
      clipRule="evenodd"
      d="M10.5303 3.46967L11.0607 4L6.06066 9L11.0607 14L10.5303 14.5303L10 15.0607L4.46967 9.53033C4.17678 9.23744 4.17678 8.76256 4.46967 8.46967L10 2.93934L10.5303 3.46967Z"
      transform="translate(0, -2)"
    />
  </svg>
);

const ChevronRight = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
    <path
      fillRule="evenodd"
      clipRule="evenodd"
      d="M5.46967 3.46967L4.93934 4L9.93934 9L4.93934 14L5.46967 14.5303L6 15.0607L11.5303 9.53033C11.8232 9.23744 11.8232 8.76256 11.5303 8.46967L6 2.93934L5.46967 3.46967Z"
      transform="translate(0, -2)"
    />
  </svg>
);

const CalendarIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
    <path
      fillRule="evenodd"
      clipRule="evenodd"
      d="M4 0.5V1.5V2H2.5C1.67157 2 1 2.67157 1 3.5V13.5C1 14.3284 1.67157 15 2.5 15H13.5C14.3284 15 15 14.3284 15 13.5V3.5C15 2.67157 14.3284 2 13.5 2H12V1.5V0.5H11V1.5V2H5V1.5V0.5H4ZM2.5 6V13.5H13.5V6H2.5ZM13.5 5V3.5H2.5V5H13.5Z"
    />
  </svg>
);

const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"];

export const CalendarNew = ({ value, onChange, className }: CalendarNewProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [currentMonth, setCurrentMonth] = useState(value?.from || new Date());
  const [selecting, setSelecting] = useState<"from" | "to" | null>(null);
  const [tempRange, setTempRange] = useState<DateRange>({
    from: value?.from || null,
    to: value?.to || null,
  });
  const containerRef = useRef<HTMLDivElement>(null);

  useClickOutside(containerRef as React.RefObject<HTMLElement>, () => {
    if (isOpen) {
      setIsOpen(false);
      setSelecting(null);
    }
  });

  useEffect(() => {
    if (value) {
      setTempRange({
        from: value.from,
        to: value.to,
      });
    }
  }, [value]);

  const days = useMemo(() => {
    const monthStart = startOfMonth(currentMonth);
    const monthEnd = endOfMonth(currentMonth);
    const calendarStart = startOfWeek(monthStart);
    const calendarEnd = endOfWeek(monthEnd);
    return eachDayOfInterval({ start: calendarStart, end: calendarEnd });
  }, [currentMonth]);

  const handleDayClick = useCallback(
    (day: Date) => {
      if (selecting === "from" || (!selecting && !tempRange.from)) {
        const newRange = {
          from: day,
          to: tempRange.to && isAfter(day, tempRange.to) ? null : tempRange.to,
        };
        setTempRange(newRange);
        setSelecting("to");
        onChange?.(newRange);
      } else if (selecting === "to" || !tempRange.to) {
        let newRange: DateRange;
        if (tempRange.from && isBefore(day, tempRange.from)) {
          newRange = { from: day, to: tempRange.from };
        } else {
          newRange = { from: tempRange.from, to: day };
        }
        setTempRange(newRange);
        setSelecting(null);
        onChange?.(newRange);
        setIsOpen(false);
      }
    },
    [selecting, tempRange, onChange]
  );

  const isInRange = useCallback(
    (day: Date) => {
      if (!tempRange.from || !tempRange.to) return false;
      return isWithinInterval(day, { start: tempRange.from, end: tempRange.to });
    },
    [tempRange]
  );

  const isRangeStart = useCallback(
    (day: Date) => tempRange.from && isSameDay(day, tempRange.from),
    [tempRange.from]
  );

  const isRangeEnd = useCallback(
    (day: Date) => tempRange.to && isSameDay(day, tempRange.to),
    [tempRange.to]
  );

  const formatDisplayDate = () => {
    if (!tempRange.from && !tempRange.to) {
      return "기간 선택";
    }
    const fromStr = tempRange.from ? format(tempRange.from, "yyyy.MM.dd") : "시작일";
    const toStr = tempRange.to ? format(tempRange.to, "yyyy.MM.dd") : "종료일";
    return `${fromStr} - ${toStr}`;
  };

  const handleQuickSelect = (days: number) => {
    const today = new Date();
    let from: Date;
    let to: Date;

    if (days === 0) {
      // 오늘
      from = today;
      to = today;
    } else if (days === 1) {
      // 어제
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);
      from = yesterday;
      to = yesterday;
    } else {
      // 최근 N일
      from = new Date();
      from.setDate(from.getDate() - days);
      to = today;
    }

    const newRange = { from, to };
    setTempRange(newRange);
    onChange?.(newRange);
    setIsOpen(false);
  };

  const handleAllTime = () => {
    const newRange = { from: null, to: null };
    setTempRange(newRange);
    onChange?.(newRange);
    setIsOpen(false);
  };

  return (
    <div className={clsx("relative inline-block", className)} ref={containerRef}>
      <button
        type="button"
        onClick={() => {
          setIsOpen(!isOpen);
          if (!isOpen) {
            setSelecting("from");
          }
        }}
        className={clsx(
          "flex items-center gap-2 px-3 py-2 text-sm rounded-lg border transition-all duration-200",
          "bg-white/60 backdrop-blur-sm border-gray-200 hover:border-gray-300",
          "focus:outline-none focus:ring-2 focus:ring-blue-500/20",
          isOpen && "border-blue-400 ring-2 ring-blue-500/20"
        )}
      >
        <CalendarIcon />
        <span className="text-gray-700">{formatDisplayDate()}</span>
      </button>

      {isOpen && (
        <Material
          type="menu"
          className="absolute top-full left-0 mt-2 z-50 p-4 min-w-[320px] !bg-white"
          style={{ backgroundColor: 'white' }}
        >
          <div className="flex gap-2 mb-4 flex-wrap">
            <button
              onClick={handleAllTime}
              className="px-3 py-1.5 text-xs rounded-full bg-gray-100 hover:bg-gray-200 transition-colors"
            >
              전체
            </button>
            <button
              onClick={() => handleQuickSelect(0)}
              className="px-3 py-1.5 text-xs rounded-full bg-gray-100 hover:bg-gray-200 transition-colors"
            >
              오늘
            </button>
            <button
              onClick={() => handleQuickSelect(1)}
              className="px-3 py-1.5 text-xs rounded-full bg-gray-100 hover:bg-gray-200 transition-colors"
            >
              어제
            </button>
            <button
              onClick={() => handleQuickSelect(7)}
              className="px-3 py-1.5 text-xs rounded-full bg-gray-100 hover:bg-gray-200 transition-colors"
            >
              최근 7일
            </button>
            <button
              onClick={() => handleQuickSelect(30)}
              className="px-3 py-1.5 text-xs rounded-full bg-gray-100 hover:bg-gray-200 transition-colors"
            >
              최근 30일
            </button>
            <button
              onClick={() => handleQuickSelect(90)}
              className="px-3 py-1.5 text-xs rounded-full bg-gray-100 hover:bg-gray-200 transition-colors"
            >
              최근 90일
            </button>
          </div>

          <div className="flex items-center justify-between mb-4">
            <button
              onClick={() => setCurrentMonth(subMonths(currentMonth, 1))}
              className="p-1.5 rounded-md hover:bg-gray-100 transition-colors"
            >
              <ChevronLeft />
            </button>
            <span className="text-sm font-medium">
              {format(currentMonth, "yyyy년 M월", { locale: ko })}
            </span>
            <button
              onClick={() => setCurrentMonth(addMonths(currentMonth, 1))}
              className="p-1.5 rounded-md hover:bg-gray-100 transition-colors"
            >
              <ChevronRight />
            </button>
          </div>

          <div className="grid grid-cols-7 gap-1 mb-2">
            {WEEKDAYS.map((day) => (
              <div
                key={day}
                className="text-center text-xs font-medium text-gray-500 py-1"
              >
                {day}
              </div>
            ))}
          </div>

          <div className="grid grid-cols-7 gap-1">
            {days.map((day) => {
              const isCurrentMonth = isSameMonth(day, currentMonth);
              const isStart = isRangeStart(day);
              const isEnd = isRangeEnd(day);
              const inRange = isInRange(day);
              const isToday = isSameDay(day, new Date());

              return (
                <button
                  key={day.toISOString()}
                  onClick={() => handleDayClick(day)}
                  disabled={!isCurrentMonth}
                  className={clsx(
                    "relative h-8 w-8 text-sm rounded-md transition-all duration-150",
                    !isCurrentMonth && "text-gray-300 cursor-default",
                    isCurrentMonth && !isStart && !isEnd && !inRange && "hover:bg-gray-100",
                    inRange && !isStart && !isEnd && "bg-blue-50",
                    (isStart || isEnd) && "bg-blue-500 text-white hover:bg-blue-600",
                    isToday && !isStart && !isEnd && "ring-1 ring-blue-400"
                  )}
                >
                  {format(day, "d")}
                </button>
              );
            })}
          </div>

          <div className="mt-4 pt-3 border-t border-gray-100 text-xs text-gray-500">
            {selecting === "from" ? "시작일을 선택하세요" : selecting === "to" ? "종료일을 선택하세요" : "기간이 선택되었습니다"}
          </div>
        </Material>
      )}
    </div>
  );
};

export default CalendarNew;
