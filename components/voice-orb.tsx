"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";

type OrbState = "IDLE" | "LISTENING" | "THINKING" | "SPEAKING";

interface MessagePart {
  text: string;
}
interface HistoryMessage {
  role: "user" | "model";
  parts: MessagePart[];
}

interface VoiceOrbProps {
  transcriptContext: any;
  conciseMode: boolean;
  onUserSpeech: (text: string) => void;
  onAIResponse: (text: string) => void;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function VoiceOrb({
  transcriptContext,
  conciseMode,
  onUserSpeech,
  onAIResponse,
}: VoiceOrbProps) {
  const [orbState, setOrbState] = useState<OrbState>("IDLE");
  const [interimTranscript, setInterimTranscript] = useState("");
  const [aiText, setAiText] = useState("");
  
  const aiTextRef = useRef("");
  const recognitionRef = useRef<any>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const silenceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const chatHistory = useRef<HistoryMessage[]>([]);
  const isComponentMounted = useRef(true);
  const transcriptCtxRef = useRef(transcriptContext);

  // Sync transcript context so the closure always has the latest
  useEffect(() => {
    transcriptCtxRef.current = transcriptContext;
  }, [transcriptContext]);

  // Initialize Speech Recognition
  useEffect(() => {
    isComponentMounted.current = true;
    if (typeof window !== "undefined") {
      const SpeechRecognition =
        (window as any).SpeechRecognition ||
        (window as any).webkitSpeechRecognition;
      
      if (SpeechRecognition) {
        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = "en-US";

        recognition.onresult = (event: any) => {
          let latestTranscript = "";
          for (let i = 0; i < event.results.length; i++) {
            latestTranscript += event.results[i][0].transcript;
          }
          
          setInterimTranscript(latestTranscript);

          // Reset silence timer
          if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
          
          silenceTimerRef.current = setTimeout(() => {
             // 1.5s of silence detected
             const finalUserText = latestTranscript.trim();
             if (finalUserText) {
               handleSendMessage(finalUserText, false); // Turn-taking means no mid-speech interrupts
               setInterimTranscript("");
             }
          }, 1500);
        };

        recognition.onerror = (e: any) => {
          console.error("Speech Recognition Error:", e.error);
          if (e.error !== "no-speech") {
            setOrbState("IDLE");
          }
        };

        recognition.onend = () => {
          // If we are marked as LISTENING but the engine stopped itself, restart it
          // UNLESS component unmounted
          if (isComponentMounted.current) {
            // We handle explicit stops via state machine. 
            // The continuous=true usually keeps it alive, but occasionally it drops.
          }
        };

        recognitionRef.current = recognition;
      }
    }

    // INITIAL GREETING ON MOUNT
    const startInitialGreeting = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/voice/start`, { method: "POST" });
        if (res.ok) {
          const data = await res.json();
          chatHistory.current = data.history;
          
          if (isComponentMounted.current) {
            setAiText(data.reply);
            aiTextRef.current = data.reply;
            onAIResponse(data.reply);
            playAudioResponse(data.reply);
          }
        }
      } catch (err) {
        if (isComponentMounted.current) {
          const fallbackMsg = "Hey! I'm Comet Advisor. How can I help you plan your courses?";
          setAiText(fallbackMsg);
          aiTextRef.current = fallbackMsg;
          playAudioResponse(fallbackMsg);
        }
      }
    };
    
    // Tiny delay to ensure UI mounts first
    setTimeout(startInitialGreeting, 500);

    return () => {
      isComponentMounted.current = false;
      stopAll();
    };
  }, []);

  const playAudioResponse = async (text: string) => {
    try {
      setOrbState("SPEAKING");
      // The speak endpoint is a Next.js route, not the Python backend
      const audioRes = await fetch(`/api/speak`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });

      if (!audioRes.ok) throw new Error("Audio POST failed");
      const audioBlob = await audioRes.blob();
      const url = URL.createObjectURL(audioBlob);

      stopAudioPlayback();
      const audio = new Audio(url);
      audioRef.current = audio;

      audio.onended = () => {
        URL.revokeObjectURL(url);
        if (isComponentMounted.current) {
          setOrbState("LISTENING");
          // Turn mic back on for user's turn
          if (recognitionRef.current) { 
             try { recognitionRef.current.start(); } catch {} 
          }
        }
      };

      audio.onerror = () => {
        URL.revokeObjectURL(url);
        if (isComponentMounted.current) {
          setOrbState("LISTENING");
          if (recognitionRef.current) { 
             try { recognitionRef.current.start(); } catch {} 
          }
        }
      };

      // Turn OFF the mic while the audio plays to prevent echo loops
      if (recognitionRef.current) {
         try { recognitionRef.current.abort(); } catch {}
      }

      await audio.play().catch((e) => {
        console.warn("Autoplay blocked", e);
        if (isComponentMounted.current) {
          setOrbState("LISTENING");
          if (recognitionRef.current) { try { recognitionRef.current.start(); } catch {} }
        }
      });
    } catch (e) {
      console.warn("ElevenLabs TTS failed, using browser fallback:", e);
      // Fallback to browser TTS
      if (typeof window !== "undefined" && window.speechSynthesis) {
        setOrbState("SPEAKING");
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.05;
        
        utterance.onend = () => {
          if (isComponentMounted.current) {
            setOrbState("LISTENING");
            if (recognitionRef.current) { try { recognitionRef.current.start(); } catch {} }
          }
        };
        
        utterance.onerror = () => {
          if (isComponentMounted.current) {
            setOrbState("LISTENING");
            if (recognitionRef.current) { try { recognitionRef.current.start(); } catch {} }
          }
        };

        stopAudioPlayback();
        window.speechSynthesis.speak(utterance);

        // Turn OFF the mic while the audio plays to prevent echo loops
        if (recognitionRef.current) {
           try { recognitionRef.current.abort(); } catch {}
        }
      } else {
        setOrbState("LISTENING");
        if (recognitionRef.current) { try { recognitionRef.current.start(); } catch {} }
      }
    }
  };

  const stopAudioPlayback = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = "";
    }
    if (typeof window !== "undefined" && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
  }, []);

  const stopAll = useCallback(() => {
    stopAudioPlayback();
    if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
    if (recognitionRef.current) {
      try { recognitionRef.current.abort(); } catch {}
    }
    setOrbState("IDLE");
    setInterimTranscript("");
    setAiText("");
  }, [stopAudioPlayback]);

  const toggleMic = () => {
    if (orbState === "IDLE") {
      setOrbState("LISTENING");
      setAiText("");
      if (recognitionRef.current) {
        try { recognitionRef.current.start(); } catch (e) {
          console.warn("Recognition start error", e);
        }
      }
    } else if (orbState === "SPEAKING") {
      // TAP TO INTERRUPT
      stopAudioPlayback();
      setOrbState("LISTENING");
      setAiText("");
      if (recognitionRef.current) {
        try { recognitionRef.current.start(); } catch {}
      }
    } else {
      stopAll();
    }
  };

  const handleSendMessage = async (text: string, wasInterrupted: boolean) => {
    if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
    if (!text.trim() || orbState !== "LISTENING") return;

    // Transition to thinking, pause mic
    if (recognitionRef.current) {
      try { recognitionRef.current.abort(); } catch {}
    }

    setOrbState("THINKING");
    onUserSpeech(text); // Notify parent for target semester detection

    try {
      const chatRes = await fetch(`${API_BASE}/api/voice/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          history: chatHistory.current,
          transcript_context: transcriptCtxRef.current,
          concise: conciseMode,
          was_interrupted: wasInterrupted
        }),
      });

      if (!chatRes.ok) throw new Error("Chat POST failed");
      const chatData = await chatRes.json();
      chatHistory.current = chatData.history;
      
      const replyText = chatData.reply;
      setAiText(replyText);
      aiTextRef.current = replyText;
      onAIResponse(replyText); // Notify parent to parse courses

      // Now fetch audio using our helper
      await playAudioResponse(replyText);

    } catch (err) {
      console.error("Voice cycle failed:", err);
      // Fallback
      setOrbState("LISTENING");
      if (recognitionRef.current) {
        try { recognitionRef.current.start(); } catch {}
      }
    }
  };

  // --- STYLES FOR ORB STATES ---
  const getOrbStateStyles = () => {
    switch (orbState) {
      case "IDLE":
        return "bg-neutral-800 scale-100 shadow-none";
      case "LISTENING":
        return "bg-violet-600 scale-110 shadow-[0_0_40px_rgba(139,92,246,0.6)] animate-pulse";
      case "THINKING":
        return "bg-blue-600 scale-100 shadow-[0_0_30px_rgba(37,99,235,0.6)] border-4 border-t-blue-300 animate-spin";
      case "SPEAKING":
        // Gradient wave
        return "bg-gradient-to-tr from-violet-600 via-blue-500 to-indigo-600 scale-110 shadow-[0_0_60px_rgba(139,92,246,0.8)] animate-[wave_2s_ease-in-out_infinite]";
      default:
        return "bg-neutral-800 scale-100";
    }
  };

  return (
    <div className="flex flex-col items-center w-full max-w-2xl mx-auto px-4 relative min-h-[300px] justify-center">
      
      {/* Dynamic Voice Orb */}
      <div 
        onClick={toggleMic}
        className={`w-28 h-28 rounded-full cursor-pointer transition-all duration-500 flex items-center justify-center ${getOrbStateStyles()}`}
      >
        {orbState === "IDLE" && (
          <span className="text-white/50 text-xs font-semibold uppercase tracking-wider">Tap</span>
        )}
        {orbState === "SPEAKING" && (
          <span className="text-white/60 text-[10px] font-semibold uppercase tracking-wider absolute opacity-0 hover:opacity-100 transition-opacity">Interrupt</span>
        )}
      </div>

      {/* State Text Indicator */}
      <h3 className="mt-8 text-sm font-semibold text-muted-foreground uppercase tracking-widest transition-opacity duration-300">
        {orbState === "IDLE" ? "Ready" : orbState}
      </h3>

      {/* Real-time Transcript Layer */}
      <div className="h-24 mt-6 w-full text-center flex flex-col items-center justify-start overflow-hidden relative">
        {/* User live transcript */}
        {orbState === "LISTENING" && interimTranscript && (
          <p className="text-xl font-medium text-white/90 italic drop-shadow-md animate-in fade-in duration-300 max-w-lg">
            "{interimTranscript}"
          </p>
        )}
        
        {/* AI Response Text */}
        {(orbState === "SPEAKING" || orbState === "THINKING") && aiText && (
          <p className="text-lg font-medium text-violet-200/90 animate-in fade-in slide-in-from-bottom-2 duration-500 max-w-xl">
            {aiText}
          </p>
        )}
      </div>

      <style jsx>{`
        @keyframes wave {
          0%, 100% {
            border-radius: 50% 50% 50% 50% / 50% 50% 50% 50%;
            transform: scale(1.1);
          }
          33% {
            border-radius: 40% 60% 40% 60% / 60% 40% 60% 40%;
            transform: scale(1.15) rotate(5deg);
          }
          66% {
            border-radius: 60% 40% 60% 40% / 40% 60% 40% 60%;
            transform: scale(1.05) rotate(-5deg);
          }
        }
      `}</style>
    </div>
  );
}
