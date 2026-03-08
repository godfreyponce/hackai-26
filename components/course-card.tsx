"use client";

import { useState } from "react";
import { User, CheckCircle } from "lucide-react";

interface CourseCardProps {
  code: string;
  title: string;
  professor: string;
  badge: "Core Requirement" | "Track Elective";
  whyText: string;
  isCompleted?: boolean;
  delay?: number;
}

export function CourseCard({
  code,
  title,
  professor,
  badge,
  whyText,
  isCompleted = false,
  delay = 0,
}: CourseCardProps) {
  const [showTooltip, setShowTooltip] = useState(false);

  return (
    <div
      className={`relative group animate-fade-in-up ${
        isCompleted ? "opacity-70" : ""
      }`}
      style={{ animationDelay: `${delay}ms` }}
      onMouseEnter={() => setShowTooltip(true)}
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

        {/* Course code */}
        <p className="font-[var(--font-heading)] font-semibold text-teal text-sm">
          {code}
        </p>

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

        {/* Badge */}
        <div className="mt-3">
          <span className="inline-block px-2.5 py-1 text-xs font-medium rounded-full bg-purple/20 text-violet border border-purple/30">
            {badge}
          </span>
        </div>
      </div>

      {/* Tooltip */}
      {showTooltip && !isCompleted && (
        <div className="absolute left-0 right-0 -bottom-2 translate-y-full z-20 px-1">
          <div className="bg-[#1a1a3a]/95 backdrop-blur-xl border border-violet/20 rounded-md p-4 shadow-[0_0_30px_rgba(123,47,190,0.1)]">
            <p className="text-xs text-muted-foreground leading-relaxed">
              <span className="text-teal font-medium">Why this course:</span>{" "}
              {whyText}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
