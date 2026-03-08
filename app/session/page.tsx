"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { AIAvatar } from "@/components/ai-avatar";
import { Download, Loader2, ChevronRight, ChevronDown } from "lucide-react";
import { DndBoard, Course } from "@/components/dnd-board";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Fallback helper to detect UTD courses in text like "CS 1337" or "MATH 2418"
const COURSE_REGEX = /(?:CS|SE|CE|EE|MATH|STAT|PHYS|CGS|COGS|RHET|GOVT|ECS|BMEN|MECH)[\s]\d{4}/gi;

// Detect semester mentions in user messages
const SEMESTER_REGEX = /(?:fall|spring|summer)\s*(?:20)?\d{2}/gi;

export default function SessionPage() {
  const [messages, setMessages] = useState<any[]>([]);
  const [isRecording, setIsRecording] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [advisorStatus, setAdvisorStatus] = useState<"listening" | "speaking" | "idle">("idle");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionEnded, setSessionEnded] = useState(false);
  const [showPrevious, setShowPrevious] = useState(false);
  const [targetSemester, setTargetSemester] = useState("");
  const transcriptData = useRef<any>(null);
  
  // Previous semesters (expandable)
  const [previousSemesters, setPreviousSemesters] = useState<Record<string, Course[]>>({});
  
  // DND Board State
  const [columns, setColumns] = useState<Record<string, any>>({
    inProgress: {
      title: "In Progress (Spring 2026)",
      credits: 0,
      courses: [],
      isCompleted: false,
      isInProgress: true,
    },
    recommended: {
      title: "Recommended Courses",
      credits: 0,
      courses: [],
    },
    later: {
      title: "Later",
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

  // Load transcript data into columns on mount
  useEffect(() => {
    if (typeof window === "undefined") return;
    const raw = sessionStorage.getItem("transcriptData");
    if (raw) {
      try {
        const t = JSON.parse(raw);
        const validCourses = (t.completed_courses || []).filter((c: any) => c.grade !== "W");
        
        // Build transcript context for LLM
        const courseListText = validCourses
          .map((c: any) => `${c.course_code} (${c.course_name}, grade: ${c.grade}, ${c.semester})`)
          .join("; ");
        transcriptCtx.current = [
          `Student Name: ${t.student_name}`,
          `Student ID: ${t.student_id}`,
          `Major: ${t.major}`,
          t.minor ? `Minor: ${t.minor}` : null,
          `GPA: ${t.gpa}`,
          `Total Credit Hours: ${t.total_credit_hours}`,
          `Completed Courses: ${courseListText}`,
        ].filter(Boolean).join("\n");

        // Separate in-progress (IP grade or current semester) from completed
        const inProgressCourses: Course[] = [];
        const completedBySemester: Record<string, Course[]> = {};

        validCourses.forEach((c: any) => {
          const course: Course = {
            id: c.course_code + "-" + Math.random().toString(36).substr(2, 9),
            code: c.course_code,
            title: c.course_name,
            professor: `Grade: ${c.grade}`,
            badge: "Core Requirement",
            whyText: `${c.semester}`,
          };

          if (c.grade === "IP" || c.grade === "CR") {
            inProgressCourses.push(course);
          } else {
            const sem = c.semester || "Unknown";
            if (!completedBySemester[sem]) completedBySemester[sem] = [];
            completedBySemester[sem].push(course);
          }
        });

        // Set in-progress column
        const ipCredits = inProgressCourses.length * 3;
        setColumns(prev => ({
          ...prev,
          inProgress: {
            ...prev.inProgress,
            credits: ipCredits,
            courses: inProgressCourses,
          },
        }));

        // Set previous semesters
        setPreviousSemesters(completedBySemester);

        // Save transcript for later when user picks a semester
        transcriptData.current = t;
      } catch {}
    }
  }, []);

  // Call backend recommend engine (uses verified CS flowchart semester sequence)
  const fetchRecommendations = async (transcript: any) => {
    try {
      const res = await fetch(`${API_BASE}/api/recommend/from-data`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(transcript),
      });
      if (!res.ok) return;
      const plan = await res.json();
      
      if (plan.recommendations && plan.recommendations.length > 0) {
        const recCourses: Course[] = plan.recommendations.map((r: any) => ({
          id: r.course_code + "-rec-" + Math.random().toString(36).substr(2, 9),
          code: r.course_code,
          title: r.course_name,
          professor: targetSemester || "Next Semester",
          badge: "Core Requirement" as const,
          whyText: r.reason,
        }));

        // Stagger courses onto the board one at a time (800ms apart)
        recCourses.forEach((course, index) => {
          setTimeout(() => {
            setColumns(prev => ({
              ...prev,
              recommended: {
                ...prev.recommended,
                credits: (index + 1) * 3,
                courses: [...prev.recommended.courses, course],
              }
            }));
          }, index * 800);
        });
      }
    } catch (err) {
      console.error("Failed to fetch recommendations:", err);
    }
  };

  // Update recommended column title when target semester changes
  useEffect(() => {
    if (!targetSemester) return;
    setColumns(prev => ({
      ...prev,
      recommended: {
        ...prev.recommended,
        title: `Recommended for ${targetSemester}`,
      }
    }));
  }, [targetSemester]);

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
    setAdvisorStatus("speaking");
    setIsSpeaking(true);

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

      audio.onended = () => {
        setIsSpeaking(false);
        setAdvisorStatus("idle");
        if (onEnded) onEnded();
      };

      audio.onerror = () => {
        setIsSpeaking(false);
        setAdvisorStatus("idle");
        if (onEnded) onEnded();
      };

      await audio.play().catch(() => {
        // Autoplay blocked — fall back to browser TTS
        fallbackSpeak(text, onEnded);
      });

    } catch (error) {
      // ElevenLabs failed — fall back to browser speech
      console.warn("ElevenLabs failed, using browser TTS");
      fallbackSpeak(text, onEnded);
    }
  };

  // Browser-native TTS fallback
  const fallbackSpeak = (text: string, onEnded?: () => void) => {
    if (typeof window !== "undefined" && window.speechSynthesis) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.05;
      utterance.pitch = 1.0;
      utterance.onend = () => {
        setIsSpeaking(false);
        setAdvisorStatus("idle");
        if (onEnded) onEnded();
      };
      utterance.onerror = () => {
        setIsSpeaking(false);
        setAdvisorStatus("idle");
        if (onEnded) onEnded();
      };
      window.speechSynthesis.speak(utterance);
    } else {
      // No TTS available at all — just move on
      setIsSpeaking(false);
      setAdvisorStatus("idle");
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

  // Detect semester from user text (e.g. "Fall 2026", "Spring 2027")
  // Also detect from AI response text
  const detectTargetSemester = (text: string) => {
    const matches = text.match(SEMESTER_REGEX);
    if (matches && matches.length > 0) {
      const raw = matches[matches.length - 1];
      const parts = raw.trim().split(/\s+/);
      const season = parts[0].charAt(0).toUpperCase() + parts[0].slice(1).toLowerCase();
      let year = parts[1] || "";
      if (year.length === 2) year = "20" + year;
      const formatted = `${season} ${year}`;
      
      // Only fetch if semester changed
      if (formatted !== targetSemester) {
        setTargetSemester(formatted);
        // Fetch recommendations when user picks a semester
        if (transcriptData.current) {
          fetchRecommendations(transcriptData.current);
        }
      }
    }
  };

  // Helper to parse course codes from AI text and add to recommended
  const extractAndAddCourses = async (text: string) => {
    const matches = Array.from(text.matchAll(COURSE_REGEX)).map(m => m[0].toUpperCase());
    const uniqueCodes = Array.from(new Set(matches));

    if (uniqueCodes.length === 0) return;

    setColumns((prevCols) => {
      const allExisting = Object.values(prevCols).flatMap(col => col.courses.map((c: any) => c.code));
      const newCodes = uniqueCodes.filter(code => !allExisting.includes(code));
      
      if (newCodes.length === 0) return prevCols;

      const newCourses = newCodes.map(code => ({
        id: code + "-" + Math.random().toString(36).substr(2, 9),
        code: code,
        title: "Recommended Course",
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

    // Detect target semester from user message
    detectTargetSemester(userText);

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

        // Also detect semester from AI response
        detectTargetSemester(data.reply);

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

  const semesterKeys = Object.keys(previousSemesters).sort();
  const totalCompletedCredits = semesterKeys.reduce(
    (sum, key) => sum + previousSemesters[key].length * 3, 0
  );

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

        {/* Expandable Previous Semesters */}
        {semesterKeys.length > 0 && (
          <div className="w-full mb-6">
            <button
              onClick={() => setShowPrevious(!showPrevious)}
              className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors mb-4"
            >
              {showPrevious ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronRight className="w-4 h-4" />
              )}
              <span className="font-[var(--font-heading)] font-semibold text-sm" style={{ fontFamily: "'Figtree', sans-serif" }}>
                Previous Semesters ({totalCompletedCredits} credits completed)
              </span>
            </button>

            {showPrevious && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-8 animate-in slide-in-from-top-2 duration-300">
                {semesterKeys.map((sem) => (
                  <div
                    key={sem}
                    className="bg-[#141428]/40 border border-green-500/20 rounded-xl p-4"
                  >
                    <h3
                      className="font-[var(--font-heading)] font-bold text-sm text-green-400 mb-3"
                      style={{ fontFamily: "'Figtree', sans-serif" }}
                    >
                      {sem}
                    </h3>
                    <div className="flex flex-col gap-2">
                      {previousSemesters[sem].map((course) => (
                        <div
                          key={course.id}
                          className="flex items-center justify-between px-3 py-2 bg-green-500/5 rounded-lg border border-green-500/10"
                        >
                          <div className="flex flex-col">
                            <span className="text-xs font-semibold text-green-400">{course.code}</span>
                            <span className="text-[11px] text-muted-foreground truncate max-w-[160px]">{course.title}</span>
                          </div>
                          <span className="text-[10px] text-green-500/70">{course.professor.replace("Grade: ", "")}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Below Avatar: Drag and Drop Interactive Board */}
        <div className="w-full">
           <DndBoard columns={columns} setColumns={setColumns} />
        </div>

      </div>

      {/* Floating Export Button */}
      <div className={`fixed bottom-12 right-12 transition-all duration-1000 z-50 ${sessionEnded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10 pointer-events-none'}`}>
         <button onClick={handleExportPlan} className="px-6 py-4 rounded-xl bg-orange text-foreground font-[var(--font-heading)] font-semibold text-lg flex items-center gap-3 shadow-[0_0_30px_rgba(232,119,34,0.3)] hover:scale-105 transition-all">
           <Download className="w-5 h-5" />
           Export Final Plan
         </button>
      </div>

    </div>
  );
}
