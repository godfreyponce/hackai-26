"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { AIAvatar } from "@/components/ai-avatar";
import { Download, Loader2 } from "lucide-react";
import { DndBoard, Course } from "@/components/dnd-board";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Fallback helper to detect UTD courses in text like "CS 1337" or "MATH 2418"
const COURSE_REGEX = /(?:CS|SE|CE|EE|MATH|STAT|PHYS|CGS|COGS)\s\d{4}/gi;

export default function SessionPage() {
  const [messages, setMessages] = useState<any[]>([]);
  const [isRecording, setIsRecording] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [advisorStatus, setAdvisorStatus] = useState<"listening" | "speaking" | "idle">("idle");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionEnded, setSessionEnded] = useState(false);
  
  // DND Board State
  const [columns, setColumns] = useState<Record<string, any>>({
    completed: {
      title: "Completed",
      credits: 0,
      courses: [],
      isCompleted: true,
    },
    recommended: {
      title: "Recommended for Fall",
      credits: 0,
      courses: [],
    },
    spring: {
      title: "Later (Spring)",
      credits: 0,
      courses: [],
    }
  });

  const chatHistory = useRef<any[]>([]);
  const messageCount = useRef(0);
  const transcriptCtx = useRef<string | null>(null);
  
  // Voice feature refs
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const recognitionRef = useRef<any>(null);
  const silenceTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Load transcript data into the first column on mount
  useEffect(() => {
    if (typeof window === "undefined") return;
    const raw = sessionStorage.getItem("transcriptData");
    if (raw) {
      try {
        const t = JSON.parse(raw);
        const validCourses = (t.completed_courses || []).filter((c: any) => c.grade !== "W");
        
        // Populate specific context for the LLM
        const courseListText = validCourses
          .map((c: any) => `${c.course_code} (${c.course_name}, grade: ${c.grade}, ${c.semester})`)
          .join("; ");
        transcriptCtx.current = [
          `Student Name: ${t.student_name}`,
          `Student ID: ${t.student_id}`,
          `Major: ${t.major}`,
          `GPA: ${t.gpa}`,
          `Total Credit Hours: ${t.total_credit_hours}`,
          `Completed Courses: ${courseListText}`,
        ].join("\n");

        // Populate board UI
        const mappedCourses: Course[] = validCourses.slice(-5).map((c: any) => ({
          id: c.course_code + "-" + Math.random().toString(36).substr(2, 9),
          code: c.course_code,
          title: c.course_name,
          professor: `Grade: ${c.grade}`,
          badge: "Core Requirement",
          whyText: `Completed in ${c.semester}.`,
        }));
        
        setColumns(prev => ({
          ...prev,
          completed: {
            ...prev.completed,
            credits: Math.round(t.total_credit_hours),
            courses: mappedCourses,
          }
        }));
      } catch {}
    }
  }, []);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
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

          if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);

          silenceTimerRef.current = setTimeout(() => {
            if (recognitionRef.current) recognitionRef.current.stop();
            handleSend(latestTranscript);
          }, 1500);
        };

        recognition.onspeechend = () => {
           if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
           recognition.stop();
        };

        recognition.onend = () => {
          setIsRecording(false);
          setAdvisorStatus((prev) => prev === "speaking" ? "speaking" : "idle");
        };

        recognition.onerror = (event: any) => {
          console.error("Speech recognition error", event.error);
          setIsRecording(false);
          setAdvisorStatus("idle");
        };

        recognitionRef.current = recognition;
      }
    }
    return () => {
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
    }
  }, []);

  const playAudio = async (text: string, onEnded?: () => void) => {
    try {
      const res = await fetch("/api/speak", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });

      if (!res.ok) throw new Error("TTS failed");

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);

      if (audioRef.current) audioRef.current.pause();

      const audio = new Audio(url);
      audioRef.current = audio;

      setAdvisorStatus("speaking");
      setIsSpeaking(true);

      audio.onended = () => {
        setIsSpeaking(false);
        setAdvisorStatus("listening");
        if (onEnded) onEnded();
      };

      await audio.play().catch(e => {
        console.warn("Autoplay was blocked by browser:", e);
        setIsSpeaking(false);
        setAdvisorStatus("listening");
        if (onEnded) onEnded();
      });

    } catch (error) {
      console.error("Audio playback error:", error);
      setIsSpeaking(false);
      setAdvisorStatus("listening");
      if (onEnded) onEnded();
    }
  };

  const startListening = () => {
    if (sessionEnded) return;
    if (recognitionRef.current && !isRecording) {
      setIsRecording(true);
      setAdvisorStatus("listening");
      try {
        recognitionRef.current.start();
      } catch (e) {
        console.log("Recognition already started");
      }
    }
  };

  // Start chat on mount
  useEffect(() => {
    const startChat = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/voice/start`, { method: "POST" });
        if (res.ok) {
          const data = await res.json();
          chatHistory.current = data.history;
          playAudio(data.reply, startListening);
        }
      } catch (err) {
        playAudio("Hey! I'm Comet Advisor. What courses are you thinking about?", startListening);
      }
    };
    startChat();
  }, []);

  // Helper to parse course codes from AI text and fetch details 
  const extractAndAddCourses = async (text: string) => {
    const matches = Array.from(text.matchAll(COURSE_REGEX)).map(m => m[0].toUpperCase());
    const uniqueCodes = Array.from(new Set(matches));

    if (uniqueCodes.length === 0) return;

    // Check what we already have
    setColumns((prevCols) => {
      const allExisting = Object.values(prevCols).flatMap(col => col.courses.map((c: any) => c.code));
      const newCodes = uniqueCodes.filter(code => !allExisting.includes(code));
      
      if (newCodes.length === 0) return prevCols;

      // In a real app, we would fetch details from /api/courses/{code}
      // For this hackathon demo, we will create mock cards for the detected codes
      const newCourses = newCodes.map(code => ({
        id: code + "-" + Math.random().toString(36).substr(2, 9),
        code: code,
        title: "Recommended Course", // Placeholder, would fetch real
        professor: "TBD",
        badge: "Core Requirement" as const,
        whyText: "Matches your career interests and degree plan.",
      }));

      return {
        ...prevCols,
        recommended: {
          ...prevCols.recommended,
          credits: prevCols.recommended.credits + (newCourses.length * 3),
          courses: [...prevCols.recommended.courses, ...newCourses],
        }
      };
    });
  };

  const handleSend = async (userText: string) => {
    if (!userText.trim() || isLoading || sessionEnded) return;

    messageCount.current += 1;
    setIsLoading(true);
    setAdvisorStatus("speaking");
    setIsSpeaking(true);

    // End session after ~4 interactions
    if (messageCount.current >= 4) {
      setSessionEnded(true);
    }

    try {
      const res = await fetch(`${API_BASE}/api/voice/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userText,
          history: chatHistory.current,
          transcript_context: transcriptCtx.current,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        chatHistory.current = data.history;
        
        // Parse the advisor's text and update board
        await extractAndAddCourses(data.reply);

        playAudio(data.reply, () => {
          if (!sessionEnded && messageCount.current < 4) {
            startListening();
          } else {
            setAdvisorStatus("idle");
          }
        });
      } else {
        playAudio("I had trouble understanding that. Could you try again?", startListening);
      }
    } catch (err) {
      playAudio("I'm having trouble connecting. Please try again.", startListening);
    }

    setIsLoading(false);
  };

  const handleMicToggle = useCallback(() => {
    if (isRecording && recognitionRef.current) {
      recognitionRef.current.stop();
      setIsRecording(false);
      setAdvisorStatus("idle");
    } else {
      startListening();
    }
  }, [isRecording]);

  const handleExportPlan = useCallback(() => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(columns, null, 2));
    const a = document.createElement("a");
    a.href = dataStr;
    a.download = "comet-academic-plan.json";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }, [columns]);

  return (
    <div className="min-h-screen bg-background flex flex-col pt-24 pb-12 px-8">
      <div className="max-w-7xl mx-auto w-full flex flex-col items-center">
        
        {/* Top Center: Voice Avatar */}
        <div className="flex flex-col items-center mb-16 relative">
           <AIAvatar isSpeaking={isSpeaking} status={advisorStatus} />
           
           {isLoading && (
             <div className="mt-4 flex items-center gap-2 text-muted-foreground animate-pulse">
               <Loader2 className="w-4 h-4 animate-spin" />
               <span className="text-sm">Thinking...</span>
             </div>
           )}

           {/* Manual Mic Override if disabled */}
           {advisorStatus === "idle" && !sessionEnded && !isLoading && (
             <button 
               onClick={handleMicToggle}
               className="mt-6 px-5 py-2.5 rounded-full border border-violet/20 flex items-center gap-2.5 hover:bg-violet/10 hover:border-violet text-muted-foreground transition-all shadow-sm"
               >
               <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse" />
               Tap to speak
             </button>
           )}
        </div>

        {/* Below Avatar: Drag and Drop Interactive Board */}
        <div className="w-full">
           <DndBoard columns={columns} setColumns={setColumns} />
        </div>

      </div>

      {/* Floating Export Button, fades in at the end of the conversation */}
      <div className={`fixed bottom-12 right-12 transition-all duration-1000 z-50 ${sessionEnded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10 pointer-events-none'}`}>
         <button onClick={handleExportPlan} className="px-6 py-4 rounded-xl bg-orange text-foreground font-[var(--font-heading)] font-semibold text-lg flex items-center gap-3 shadow-[0_0_30px_rgba(232,119,34,0.3)] hover:scale-105 transition-all">
           <Download className="w-5 h-5" />
           Export Final Plan
         </button>
      </div>

    </div>
  );
}
