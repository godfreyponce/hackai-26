"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { UploadBox } from "./upload-box";
import { ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

export function HeroSection() {
  const [isFileUploaded, setIsFileUploaded] = useState(false);
  const router = useRouter();

  const handleStartSession = () => {
    router.push('/session');
  };

  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center px-8 pt-20">
      <div className="max-w-3xl mx-auto text-center space-y-10 z-10">
        {/* Small Label */}
        <p className="text-teal text-xs uppercase tracking-[0.25em] font-medium">
          Powered by Nebula Labs
        </p>

        {/* Headline */}
        <h1 
          className="font-[var(--font-heading)] text-5xl md:text-6xl lg:text-7xl font-semibold tracking-[-0.02em] bg-gradient-to-r from-[#7B6FE8] to-[#E8837B] bg-clip-text text-transparent text-balance leading-tight"
          style={{ fontFamily: "'Figtree', sans-serif" }}
        >
          Your AI Academic Advisor
        </h1>

        {/* Subtext */}
        <p className="text-muted-foreground text-lg md:text-xl max-w-xl mx-auto text-pretty">
          Available 24/7. No appointment needed. Built for UTD students.
        </p>

        {/* Upload Box */}
        <div className="pt-6">
          <UploadBox onFileUploaded={setIsFileUploaded} />
        </div>

        {/* CTA Button */}
        <div className="pt-4">
          <button
            onClick={handleStartSession}
            className={cn(
              "inline-flex items-center gap-2 px-8 py-4 rounded-full font-semibold text-lg transition-all duration-300",
              "bg-[#7B2FBE] hover:bg-[#9B5DE5] text-foreground hover:scale-105 hover:shadow-[0_0_40px_rgba(123,47,190,0.5)] active:scale-95",
            )}
          >
            Start Session
            <ArrowRight className="w-5 h-5" />
          </button>
        </div>
      </div>
    </section>
  );
}
