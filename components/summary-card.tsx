"use client";

import React from "react";
import { Play, Download } from "lucide-react";

interface SummaryCardProps {
  advisorMessage?: string;
  studentName?: string;
  completedCredits?: number;
  major?: string;
  gpa?: number;
}

export function SummaryCard({
  advisorMessage,
  studentName,
  completedCredits,
  major,
  gpa,
}: SummaryCardProps) {
  const displayMessage = advisorMessage
    ? advisorMessage.slice(0, 300) + (advisorMessage.length > 300 ? "..." : "")
    : `Based on your transcript, you've completed ${completedCredits || 45} credits toward your CS degree. I recommend focusing on core upper-division requirements this year to stay on track for a Spring 2027 graduation.`;

  const audioRef = React.useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = React.useState(false);
  const hasPlayedRef = React.useRef(false);

  const playAudio = async () => {
    if (isPlaying && audioRef.current) {
      audioRef.current.pause();
      setIsPlaying(false);
      return;
    }

    try {
      setIsPlaying(true);
      const res = await fetch("/api/speak", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: displayMessage }),
      });

      if (!res.ok) throw new Error("TTS failed");

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);

      if (audioRef.current) {
        audioRef.current.pause();
      }

      const audio = new Audio(url);
      audioRef.current = audio;

      audio.onended = () => {
        setIsPlaying(false);
      };

      await audio.play().catch(e => {
        console.warn("Autoplay was blocked by browser:", e);
        setIsPlaying(false);
      });
    } catch (err) {
      console.error("Audio playback error:", err);
      setIsPlaying(false);
    }
  };

  React.useEffect(() => {
    if (!hasPlayedRef.current && displayMessage) {
      hasPlayedRef.current = true;
      playAudio();
    }
  }, [displayMessage]);

  return (
    <div className="relative bg-[#141428]/70 backdrop-blur-xl border-l-4 border-purple rounded-md p-8 shadow-[0_0_40px_rgba(123,47,190,0.1)]">
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
          {displayMessage}
        </p>

        {/* Play button */}
        <button 
          onClick={playAudio}
          className={`flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center transition-all duration-300 hover:shadow-[0_0_20px_rgba(0,194,203,0.5)] ${isPlaying ? 'bg-orange animate-pulse' : 'bg-teal hover:opacity-90'}`}
        >
          <Play className="w-5 h-5 text-background ml-0.5" fill="currentColor" />
        </button>
      </div>

      {/* Student info bar */}
      {(studentName || gpa) && (
        <div className="mt-4 flex gap-4 text-sm text-muted-foreground">
          {studentName && <span>👤 {studentName}</span>}
          {major && <span>🎓 {major}</span>}
          {gpa && <span>📊 GPA: {gpa}</span>}
          {completedCredits && <span>📚 {completedCredits} credits completed</span>}
        </div>
      )}
    </div>
  );
}
