"use client";

import { useRef, useEffect } from "react";
import { Mic, Send, ArrowRight } from "lucide-react";
import { ChatMessage } from "./chat-message";

interface Message {
  id: string;
  content: string;
  isAdvisor: boolean;
}

interface ConversationFeedProps {
  messages: Message[];
  inputValue: string;
  onInputChange: (value: string) => void;
  onSend: () => void;
  isRecording: boolean;
  onMicToggle: () => void;
}

export function ConversationFeed({
  messages,
  inputValue,
  onInputChange,
  onSend,
  isRecording,
  onMicToggle,
}: ConversationFeedProps) {
  const feedRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [messages]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Scrollable message feed */}
      <div
        ref={feedRef}
        className="flex-1 overflow-y-auto p-6 space-y-5 scrollbar-thin scrollbar-thumb-purple/30 scrollbar-track-transparent"
      >
        {messages.map((message) => (
          <ChatMessage
            key={message.id}
            content={message.content}
            isAdvisor={message.isAdvisor}
          />
        ))}
      </div>

      {/* Input row */}
      <div className="p-5 border-t border-violet/10">
        <div className="flex items-center gap-4">
          {/* Mic button */}
          <button
            onClick={onMicToggle}
            className={`flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center transition-all duration-300 ${
              isRecording
                ? "bg-teal text-background animate-pulse shadow-[0_0_15px_rgba(0,194,203,0.5)] ring-2 ring-teal"
                : "bg-[#141428]/80 border border-teal/30 text-teal hover:bg-teal/10 hover:border-teal"
            }`}
            aria-label={isRecording ? "Stop recording" : "Start recording"}
          >
            <Mic className="w-5 h-5" />
          </button>

          {/* Text input */}
          <input
            type="text"
            value={inputValue}
            onChange={(e) => onInputChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your response..."
            className="flex-1 h-12 px-5 rounded-full bg-[#141428]/80 border border-violet/20 text-foreground placeholder:text-muted-foreground font-sans text-sm focus:outline-none focus:border-violet/40 focus:ring-1 focus:ring-violet/20 transition-all"
          />

          {/* Send button */}
          <button
            id="send-btn"
            onClick={onSend}
            disabled={!inputValue.trim()}
            className="flex-shrink-0 w-12 h-12 rounded-full bg-gradient-to-r from-purple to-teal flex items-center justify-center text-foreground transition-all duration-300 hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed"
            aria-label="Send message"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}
