import { Sparkles } from "lucide-react";

export function Navbar() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 backdrop-blur-md bg-[#0a0a1a]/60 border-b border-violet/10">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Logo Left */}
        <div className="flex items-center gap-2 group">
          <div className="relative">
            <Sparkles className="w-6 h-6 text-violet transition-colors group-hover:text-teal" />
            <div className="absolute inset-0 blur-md bg-violet/50 group-hover:bg-teal/50 transition-colors" />
          </div>
          <span className="font-[var(--font-heading)] font-black tracking-[-0.02em] text-foreground">
            Nebula Labs
          </span>
        </div>

        {/* App Name Center */}
        <div className="absolute left-1/2 -translate-x-1/2">
          <span className="font-[var(--font-heading)] font-black text-lg tracking-[-0.02em] bg-gradient-to-r from-[#7B6FE8] to-[#E8837B] bg-clip-text text-transparent">
            Nebula Advisor
          </span>
        </div>

        {/* Empty Right */}
        <div className="w-[120px]" />
      </div>
    </nav>
  );
}
