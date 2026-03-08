"use client";

interface AIAvatarProps {
  isSpeaking: boolean;
  status: "listening" | "speaking";
}

export function AIAvatar({ isSpeaking, status }: AIAvatarProps) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-6">
      {/* Avatar Container */}
      <div className="relative flex items-center justify-center">
        {/* Outer slow pulse ring */}
        <div
          className={`absolute w-56 h-56 rounded-full border-2 border-purple/40 animate-pulse-slow`}
        />

        {/* Inner fast pulse ring - active when speaking */}
        <div
          className={`absolute w-48 h-48 rounded-full border-2 border-violet/60 transition-opacity duration-300 ${
            isSpeaking ? "animate-pulse-fast opacity-100" : "opacity-0"
          }`}
        />

        {/* Main glowing circle */}
        <div className="relative w-40 h-40 rounded-full bg-gradient-to-br from-purple to-violet shadow-lg">
          {/* Inner glow effect */}
          <div className="absolute inset-0 rounded-full bg-gradient-to-br from-purple/80 to-violet/80 blur-xl" />
          
          {/* Core gradient */}
          <div className="absolute inset-2 rounded-full bg-gradient-to-br from-purple via-violet to-purple opacity-90" />
          
          {/* Highlight */}
          <div className="absolute inset-4 rounded-full bg-gradient-to-br from-violet/30 to-transparent" />
        </div>

        {/* Outer glow */}
        <div className="absolute w-40 h-40 rounded-full bg-gradient-to-br from-purple to-violet blur-2xl opacity-40" />
      </div>

      {/* Labels */}
      <div className="flex flex-col items-center gap-2">
        <span className="font-[var(--font-heading)] text-xl font-semibold text-muted-foreground">
          Nebula Advisor
        </span>
        <span
          className={`text-sm font-sans transition-colors duration-300 ${
            status === "speaking" ? "text-violet" : "text-teal"
          }`}
        >
          {status === "speaking" ? "Speaking..." : "Listening..."}
        </span>
      </div>
    </div>
  );
}
