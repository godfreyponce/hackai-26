"use client";

import { Play, Download } from "lucide-react";

export function SummaryCard() {
  return (
    <div className="relative bg-[#141428]/70 backdrop-blur-xl border-l-4 border-purple rounded-2xl p-8 shadow-[0_0_40px_rgba(123,47,190,0.1)]">
      {/* Export button - top right */}
      <button className="absolute top-4 right-4 px-4 py-2 rounded-lg bg-orange text-foreground font-[var(--font-heading)] font-semibold text-sm flex items-center gap-2 transition-all duration-300 hover:opacity-90 hover:shadow-[0_0_15px_rgba(232,119,34,0.4)]">
        <Download className="w-4 h-4" />
        Export Plan
      </button>

      <div className="flex items-center gap-6 pr-32">
        {/* Glowing purple circle avatar */}
        <div className="relative flex-shrink-0">
          <div className="w-14 h-14 rounded-full bg-gradient-to-br from-purple to-violet flex items-center justify-center">
            <div className="w-10 h-10 rounded-full bg-card/50 backdrop-blur-sm" />
          </div>
          <div className="absolute inset-0 rounded-full bg-gradient-to-br from-purple to-violet blur-md opacity-60" />
        </div>

        {/* Summary text */}
        <p className="text-foreground text-base leading-relaxed flex-1">
          Based on your transcript, you&apos;ve completed{" "}
          <span className="text-teal font-semibold">45 credits</span> toward
          your CS degree. I recommend focusing on core upper-division
          requirements this year to stay on track for a{" "}
          <span className="text-teal font-semibold">Spring 2027</span>{" "}
          graduation.
        </p>

        {/* Play button */}
        <button className="flex-shrink-0 w-12 h-12 rounded-full bg-teal flex items-center justify-center transition-all duration-300 hover:opacity-90 hover:shadow-[0_0_20px_rgba(0,194,203,0.5)]">
          <Play className="w-5 h-5 text-background ml-0.5" fill="currentColor" />
        </button>
      </div>
    </div>
  );
}
