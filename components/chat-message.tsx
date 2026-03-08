interface ChatMessageProps {
  content: string;
  isAdvisor: boolean;
}

export function ChatMessage({ content, isAdvisor }: ChatMessageProps) {
  return (
    <div
      className={`flex w-full ${isAdvisor ? "justify-start" : "justify-end"}`}
    >
      <div
        className={`max-w-[80%] px-5 py-4 rounded-md ${
          isAdvisor
            ? "bg-[#141428]/80 backdrop-blur-xl border-l-4 border-purple text-foreground"
            : "bg-[#141428]/60 border-r-2 border-teal text-foreground"
        }`}
      >
        {isAdvisor && (
          <p className="text-[10px] uppercase tracking-wider font-semibold text-violet-400 mb-1">Pam</p>
        )}
        <p className="text-sm font-sans leading-relaxed">{content}</p>
      </div>
    </div>
  );
}
