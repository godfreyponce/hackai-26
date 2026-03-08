"use client";

interface AIAvatarProps {
  isSpeaking: boolean;
  status: "listening" | "speaking" | "idle";
}

export function AIAvatar({ isSpeaking, status }: AIAvatarProps) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-6">
      {/* Avatar Container */}
      <div className="relative flex items-center justify-center">
        {/* Sound wave ripple rings — visible when speaking */}
        <div
          className={`absolute w-52 h-52 rounded-full border-2 border-orange/30 transition-opacity duration-300 ${
            isSpeaking ? "animate-ripple-1 opacity-100" : "opacity-0"
          }`}
        />
        <div
          className={`absolute w-60 h-60 rounded-full border border-orange/20 transition-opacity duration-300 ${
            isSpeaking ? "animate-ripple-2 opacity-100" : "opacity-0"
          }`}
        />
        <div
          className={`absolute w-68 h-68 rounded-full border border-orange/10 transition-opacity duration-300 ${
            isSpeaking ? "animate-ripple-3 opacity-100" : "opacity-0"
          }`}
        />

        {/* Outer slow pulse ring — breathing idle state */}
        <div
          className={`absolute w-48 h-48 rounded-full border-2 transition-all duration-500 ${
            status === "speaking"
              ? "border-orange/50 animate-pulse-fast"
              : status === "listening"
                ? "border-teal/50 animate-pulse-slow"
                : "border-purple/30 animate-pulse-slow"
          }`}
        />

        {/* Background glow — color changes with state */}
        <div
          className={`absolute w-44 h-44 rounded-full blur-2xl transition-all duration-500 ${
            status === "speaking"
              ? "bg-orange/30"
              : status === "listening"
                ? "bg-teal/20"
                : "bg-purple/20"
          }`}
        />

        {/* Temoc avatar image */}
        <div
          className={`relative w-40 h-40 rounded-full overflow-hidden shadow-2xl ring-2 transition-all duration-300 ${
            status === "speaking"
              ? "ring-orange/60 shadow-orange/20 animate-temoc-speak"
              : status === "listening"
                ? "ring-teal/60 shadow-teal/20"
                : "ring-purple/30 shadow-purple/10 animate-temoc-idle"
          }`}
        >
          {/* Use the centered portrait from public */}
          <div
            className="absolute inset-0 bg-cover bg-center"
            style={{
              backgroundImage: "url('/Gemini_Generated_Image_9w218k9w218k9w21.png')",
            }}
          />
        </div>
      </div>

      {/* Labels */}
      <div className="flex flex-col items-center gap-2">
        <span className="font-[var(--font-heading)] text-xl font-semibold text-foreground/90">
          Pam
        </span>
        <span
          className={`text-sm font-sans transition-colors duration-300 ${
            status === "speaking"
              ? "text-orange"
              : status === "listening"
                ? "text-teal"
                : "text-muted-foreground"
          }`}
        >
          {status === "speaking"
            ? "Speaking..."
            : status === "listening"
              ? "Listening..."
              : ""}
        </span>
      </div>
    </div>
  );
}
