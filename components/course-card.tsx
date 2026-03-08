"use client";

import { useState, useRef, useEffect } from "react";
import { createPortal } from "react-dom";
import { User, CheckCircle } from "lucide-react";

interface CourseCardProps {
  code: string;
  title: string;
  professor: string;
  badge: "Core Requirement" | "Track Elective" | "Degree Plan";
  whyText: string;
  isCompleted?: boolean;
  delay?: number;
  aRate?: number; // A-rate percentage (0-100)
  grade?: string; // Letter grade for completed courses
}

export function CourseCard({
  code,
  title,
  professor,
  badge,
  whyText,
  isCompleted = false,
  delay = 0,
  aRate,
  grade,
}: CourseCardProps) {
  const [showTooltip, setShowTooltip] = useState(false);
  const [tooltipPos, setTooltipPos] = useState({ top: 0, left: 0, width: 0 });
  const cardRef = useRef<HTMLDivElement>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleMouseEnter = () => {
    if (cardRef.current) {
      const rect = cardRef.current.getBoundingClientRect();
      setTooltipPos({
        top: rect.bottom + window.scrollY + 8,
        left: rect.left + window.scrollX,
        width: rect.width,
      });
    }
    setShowTooltip(true);
  };

  return (
    <div
      ref={cardRef}
      className={`relative group animate-fade-in-up ${
        isCompleted ? "opacity-70" : ""
      }`}
      style={{ animationDelay: `${delay}ms` }}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <div
        className={`bg-[#141428]/70 rounded-md p-5 transition-all duration-300 border border-transparent group-hover:bg-[#1a1a3a]/80 group-hover:shadow-[0_0_30px_rgba(123,47,190,0.15)] ${
          isCompleted ? "border-green-500/20" : ""
        }`}
      >
        {/* Completed checkmark overlay */}
        {isCompleted && (
          <div className="absolute top-3 right-3">
            <CheckCircle className="w-5 h-5 text-green-500" />
          </div>
        )}

        {/* Course code + grade badge */}
        <div className="flex items-center justify-between">
          <p className="font-[var(--font-heading)] font-semibold text-teal text-sm">
            {code}
          </p>
          {grade && (
            <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
              ['A+','A','A-'].includes(grade) ? 'bg-green-500/20 text-green-400' :
              ['B+','B','B-'].includes(grade) ? 'bg-blue-500/20 text-blue-400' :
              ['C+','C','C-'].includes(grade) ? 'bg-yellow-500/20 text-yellow-400' :
              'bg-red-500/20 text-red-400'
            }`}>{grade}</span>
          )}
        </div>

        {/* Course title */}
        <h3
          className="font-[var(--font-heading)] font-semibold text-foreground mt-1 text-base leading-tight"
          style={{ fontFamily: "'Figtree', sans-serif" }}
        >
          {title}
        </h3>

        {/* Professor */}
        <div className="flex items-center gap-1.5 mt-2 text-muted-foreground text-sm">
          <User className="w-3.5 h-3.5" />
          <span>{professor}</span>
        </div>

        {/* A-Rate Progress Bar */}
        {aRate !== undefined && aRate > 0 && (
          <div className="mt-2">
            <div className="w-full h-1.5 rounded-full bg-white/5 overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-green-500 to-emerald-400"
                style={{ width: `${Math.min(aRate, 100)}%` }}
              />
            </div>
            <p className="text-[10px] text-emerald-400/70 mt-0.5">{aRate}% A-rate</p>
          </div>
        )}

        {/* Badge */}
        <div className="mt-3">
          <span className="inline-block px-2.5 py-1 text-xs font-medium rounded-full bg-purple/20 text-violet border border-purple/30">
            {badge}
          </span>
        </div>
      </div>

      {/* Tooltip - rendered via portal to avoid clipping */}
      {mounted && showTooltip && !isCompleted && whyText && createPortal(
        <div
          className="fixed z-[100] pointer-events-none animate-in fade-in duration-150"
          style={{
            top: tooltipPos.top,
            left: tooltipPos.left,
            width: Math.max(tooltipPos.width, 280),
          }}
        >
          <div className="bg-[#1a1a3a] backdrop-blur-xl border border-violet-500/30 rounded-lg p-4 shadow-[0_4px_30px_rgba(0,0,0,0.4),0_0_20px_rgba(123,47,190,0.2)]">
            <p className="text-xs text-muted-foreground leading-relaxed">
              <span className="text-teal font-medium">Why this course:</span>{" "}
              {whyText}
            </p>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
}
