"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { AIAvatar } from "@/components/ai-avatar";
import { Download, Loader2, ChevronRight, ChevronDown, Mic, MicOff, Square } from "lucide-react";
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
  const [targetSemester, setTargetSemester] = useState("Fall 2026");
  const [conciseMode, setConciseMode] = useState(true); // Default ON for voice
  const [isGeneratingPlan, setIsGeneratingPlan] = useState(false);
  const [planGenerated, setPlanGenerated] = useState(false);

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
      title: "Recommended for Fall 2026",
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
  const transcriptGpa = useRef<number | null>(null);
  const transcriptCredits = useRef<number>(0);
  
  // Voice feature refs
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const recognitionRef = useRef<any>(null);
  const silenceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const isPlayingRef = useRef(false); // Guard against audio self-interrupt

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

        // Store GPA and credits for plan generation
        transcriptGpa.current = t.gpa || null;
        transcriptCredits.current = t.total_credit_hours || 0;

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
      } catch {}
    }
  }, []);

  // Update recommended column title when target semester changes
  useEffect(() => {
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

          // If the AI is currently speaking and user starts talking, interrupt the AI
          if (isPlayingRef.current) {
            // Only interrupt if the user actually said a recognizable word, not just noise
            if (latestTranscript.trim().length > 2) {
               stopAudio();
               // We don't want to immediately send just the interrupt word, 
               // we want to let them finish their thought
            }
          }

          if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);

          silenceTimerRef.current = setTimeout(() => {
            // Only auto-send if AI is NOT speaking, OR if user interrupted
            if (!isPlayingRef.current) {
              if (recognitionRef.current) recognitionRef.current.stop();
              handleSend(latestTranscript);
            }
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

  // Stop active audio playback (both ElevenLabs and Browser TTS)
  const stopAudio = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = "";
    }
    if (typeof window !== "undefined" && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    isPlayingRef.current = false;
    setIsSpeaking(false);
    setAdvisorStatus("listening");
  }, []);

  const playAudio = async (text: string, onEnded?: () => void) => {
    // Guard: don't interrupt ongoing playback automatically, but stop it if manually requested
    if (isPlayingRef.current) stopAudio();
    isPlayingRef.current = true;

    // Stop speech recognition timer so we don't auto-send the AI's own audio
    if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
    
    // We intentionally DO NOT stop recognitionRef here so user can interrupt.

    try {
      const res = await fetch("/api/speak", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });

      if (!res.ok) throw new Error("TTS failed");

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);

      // Clean up previous audio
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.src = "";
      }

      const audio = new Audio(url);
      audioRef.current = audio;

      // Set state AFTER audio is ready (playAudio owns state transitions)
      setAdvisorStatus("speaking");
      setIsSpeaking(true);

      audio.onended = () => {
        URL.revokeObjectURL(url);
        isPlayingRef.current = false;
        setIsSpeaking(false);
        setAdvisorStatus("listening");
        if (onEnded) onEnded();
      };

      audio.onerror = () => {
        URL.revokeObjectURL(url);
        isPlayingRef.current = false;
        setIsSpeaking(false);
        setAdvisorStatus("listening");
        if (onEnded) onEnded();
      };

      await audio.play().catch(e => {
        console.warn("Autoplay was blocked by browser:", e);
        URL.revokeObjectURL(url);
        isPlayingRef.current = false;
        setIsSpeaking(false);
        setAdvisorStatus("listening");
        if (onEnded) onEnded();
      });

    } catch (error) {
      console.warn("ElevenLabs failed, using browser TTS");
      isPlayingRef.current = false;
      // Fall back to browser speech
      if (typeof window !== "undefined" && window.speechSynthesis) {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.05;
        utterance.onend = () => {
          setIsSpeaking(false);
          setAdvisorStatus("listening");
          if (onEnded) onEnded();
        };
        utterance.onerror = () => {
          setIsSpeaking(false);
          setAdvisorStatus("listening");
          if (onEnded) onEnded();
        };
        window.speechSynthesis.speak(utterance);
      } else {
        setIsSpeaking(false);
        setAdvisorStatus("listening");
        if (onEnded) onEnded();
      }
    }
  };

  const startListening = () => {
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
  const detectTargetSemester = (text: string) => {
    const matches = text.match(SEMESTER_REGEX);
    if (matches && matches.length > 0) {
      // Capitalize properly: "fall 2026" -> "Fall 2026"
      const raw = matches[matches.length - 1];
      const parts = raw.trim().split(/\s+/);
      const season = parts[0].charAt(0).toUpperCase() + parts[0].slice(1).toLowerCase();
      let year = parts[1] || "";
      if (year.length === 2) year = "20" + year;
      const formatted = `${season} ${year}`;
      setTargetSemester(formatted);
    }
  };

  // Fetch real course title + best professor from backend and update the card
  const fetchAndEnrichCourse = async (code: string) => {
    try {
      const encoded = encodeURIComponent(code);
      const [courseRes, profRes] = await Promise.allSettled([
        fetch(`${API_BASE}/api/courses/${encoded}`),
        fetch(`${API_BASE}/api/courses/${encoded}/professor`),
      ]);

      let title: string | undefined;
      let professor: string | undefined;
      let aRate: number | undefined;

      if (courseRes.status === "fulfilled" && courseRes.value.ok) {
        const d = await courseRes.value.json();
        if (d.name) title = d.name;
      }
      if (profRes.status === "fulfilled" && profRes.value.ok) {
        const d = await profRes.value.json();
        if (d.professor) {
          professor = d.display || d.professor;
          aRate = d.a_rate;
        } else {
          professor = "TBD";
        }
      } else {
        professor = "TBD";
      }

      if (!title && !professor) return;

      setColumns(prev => {
        const updated: Record<string, any> = {};
        for (const key of Object.keys(prev)) {
          updated[key] = {
            ...prev[key],
            courses: prev[key].courses.map((c: any) =>
              c.code === code
                ? { ...c, ...(title && { title }), ...(professor && { professor }), ...(aRate !== undefined && { aRate }) }
                : c
            ),
          };
        }
        return updated;
      });
    } catch {}
  };

  // Helper to parse course codes from AI text and add to recommended
  const extractAndAddCourses = async (text: string) => {
    const matches = Array.from(text.matchAll(COURSE_REGEX)).map(m => m[0].toUpperCase());
    const uniqueCodes = Array.from(new Set(matches));

    if (uniqueCodes.length === 0) return;

    let addedCodes: string[] = [];

    setColumns((prevCols) => {
      const allExisting = Object.values(prevCols).flatMap(col => col.courses.map((c: any) => c.code));
      const newCodes = uniqueCodes.filter(code => !allExisting.includes(code));

      if (newCodes.length === 0) return prevCols;
      addedCodes = newCodes;

      const newCourses = newCodes.map(code => ({
        id: code + "-" + Math.random().toString(36).substr(2, 9),
        code: code,
        title: code, // placeholder until enriched
        professor: "Loading...",
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

    // Enrich asynchronously (won't block the voice response)
    for (const code of uniqueCodes) {
      fetchAndEnrichCourse(code);
    }
  };

  const handleSend = async (userText: string) => {
    if (!userText.trim() || isLoading) return;

    messageCount.current += 1;
    setIsLoading(true);

    // Detect target semester from user message
    detectTargetSemester(userText);

    try {
      const res = await fetch(`${API_BASE}/api/voice/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userText,
          history: chatHistory.current,
          transcript_context: transcriptCtx.current,
          concise: conciseMode,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        chatHistory.current = data.history;
        
        // Parse the advisor's text and update board
        await extractAndAddCourses(data.reply);

        playAudio(data.reply, startListening);
      } else {
        playAudio("I had trouble understanding that. Could you try again?", startListening);
      }
    } catch (err) {
      playAudio("I'm having trouble connecting. Please try again.", startListening);
    }

    setIsLoading(false);
  };

  const handleMicToggle = useCallback(() => {
    if (isRecording) {
      if (recognitionRef.current) {
        try { recognitionRef.current.stop(); } catch {}
      }
      setIsRecording(false);
      setAdvisorStatus("idle");
    } else {
      if (isPlayingRef.current) stopAudio();
      startListening();
    }
  }, [isRecording, stopAudio]);

  const handleExportPlan = useCallback(() => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(columns, null, 2));
    const a = document.createElement("a");
    a.href = dataStr;
    a.download = "comet-academic-plan.json";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }, [columns]);

  const buildColumnsFromPlan = (plan: {semesters: any[], graduation_semester: string}) => {
    const newColumns: Record<string, any> = {
      inProgress: columns.inProgress, // preserve in-progress
    };

    plan.semesters.forEach((sem: any) => {
      const key = sem.semester.replace(/\s+/g, "_");
      newColumns[key] = {
        title: sem.semester,
        credits: sem.total_credits || 0,
        courses: (sem.courses || []).map((c: any) => ({
          id: `${c.code}-${Math.random().toString(36).substr(2, 9)}`,
          code: c.code,
          title: c.title || c.code,
          professor: "Loading...",
          badge: "Degree Plan" as const,
          whyText: c.reason || "Part of your degree plan.",
        })),
      };
    });

    setColumns(newColumns);
    setPlanGenerated(true);

    // Fetch professor data for every planned course in background
    plan.semesters.flatMap((s: any) => s.courses || []).forEach((c: any) => {
      fetchAndEnrichCourse(c.code);
    });
  };

  const handleGeneratePlan = async () => {
    if (isGeneratingPlan || !transcriptCtx.current) return;
    setIsGeneratingPlan(true);

    try {
      const t = JSON.parse(sessionStorage.getItem("transcriptData") || "{}");
      const res = await fetch(`${API_BASE}/api/recommend/full-plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          transcript_context: transcriptCtx.current,
          current_semester: targetSemester,
          total_credit_hours: t.total_credit_hours || 0,
          gpa: t.gpa || null,
        }),
      });

      if (res.ok) {
        const plan = await res.json();
        if (plan.semesters && plan.semesters.length > 0) {
          buildColumnsFromPlan(plan);
          playAudio(
            `Your full ${plan.total_semesters}-semester plan is ready! Graduating ${plan.graduation_semester}. You can drag courses around to customize it.`,
            startListening
          );
        } else {
          playAudio("I had trouble building the plan. Try asking me about specific semesters instead.", startListening);
        }
      }
    } catch {
      playAudio("Couldn't generate the plan right now. Please try again.", startListening);
    }

    setIsGeneratingPlan(false);
  };

  const semesterKeys = Object.keys(previousSemesters).sort();
  const totalCompletedCredits = semesterKeys.reduce(
    (sum, key) => sum + previousSemesters[key].length * 3, 0
  );

  return (
    <div className="min-h-screen bg-background flex flex-col pt-24 pb-12 px-8">
      {/* Concise Mode Toggle - Top Right */}
      <button
        onClick={() => setConciseMode(p => !p)}
        className="fixed top-6 right-6 px-3 py-1.5 rounded-full border border-white/10 text-xs text-muted-foreground hover:border-violet-400/40 transition-all z-50"
      >
        {conciseMode ? "⚡ Concise" : "💬 Detailed"}
      </button>

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

           {/* AI Controls */}
           <div className="flex gap-4 mt-6">
             {/* Mic Toggle Button */}
             <button 
               onClick={handleMicToggle}
               className={`px-5 py-2.5 rounded-full border flex items-center gap-2.5 transition-all shadow-sm ${
                 isRecording 
                   ? "bg-red-500/10 border-red-500/50 hover:bg-red-500/20 text-red-500" 
                   : "border-violet-500/20 hover:bg-violet-500/10 hover:border-violet-500 text-muted-foreground"
               }`}
             >
               {isRecording ? (
                 <>
                   <Mic className="w-4 h-4" />
                   Listening...
                 </>
               ) : (
                 <>
                   <MicOff className="w-4 h-4" />
                   Tap to speak
                 </>
               )}
             </button>

             {/* Stop Speaking Button (Only visible when AI is speaking) */}
             {isPlayingRef.current && (
               <button 
                 onClick={stopAudio}
                 className="px-5 py-2.5 rounded-full border border-violet-500/20 bg-[#141428] hover:bg-violet-500/10 hover:border-violet-500 text-muted-foreground flex items-center gap-2.5 transition-all shadow-sm"
               >
                 <Square fill="currentColor" className="w-3.5 h-3.5" />
                 Stop AI
               </button>
             )}
           </div>

           {/* Generate My Plan Button */}
           <button
             onClick={handleGeneratePlan}
             disabled={isGeneratingPlan || isLoading}
             className="mt-6 px-6 py-3 rounded-xl bg-violet-600/80 hover:bg-violet-600 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-sm flex items-center gap-2.5 shadow-[0_0_20px_rgba(139,92,246,0.3)] hover:shadow-[0_0_30px_rgba(139,92,246,0.5)] transition-all"
           >
             {isGeneratingPlan ? (
               <><Loader2 className="w-4 h-4 animate-spin" /> Generating Plan...</>
             ) : (
               <><ChevronRight className="w-4 h-4" /> Generate My Full Plan</>
             )}
           </button>
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

        {/* Generate My Plan Button - visible after 3+ exchanges */}
        {messageCount.current >= 3 && !planGenerated && (
          <div className="w-full flex justify-center mb-8">
            <button
              onClick={handleGeneratePlan}
              disabled={isGeneratingPlan}
              className="px-8 py-4 rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 text-white font-[var(--font-heading)] font-semibold text-lg flex items-center gap-3 shadow-[0_0_30px_rgba(123,47,190,0.3)] hover:scale-105 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isGeneratingPlan ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Generating Plan...
                </>
              ) : (
                <>
                  <span className="text-xl">🎓</span>
                  Generate My Plan
                </>
              )}
            </button>
          </div>
        )}

        {/* Below Avatar: Drag and Drop Interactive Board */}
        <div className="w-full">
           <DndBoard columns={columns} setColumns={setColumns} />
        </div>

      </div>

      {/* Floating Export Button */}
      <div className="fixed bottom-12 right-12 transition-all duration-500 z-50">
         <button onClick={handleExportPlan} className="px-6 py-4 rounded-xl bg-orange text-foreground font-[var(--font-heading)] font-semibold text-lg flex items-center gap-3 shadow-[0_0_30px_rgba(232,119,34,0.3)] hover:scale-105 transition-all">
           <Download className="w-5 h-5" />
           Export Final Plan
         </button>
      </div>

    </div>
  );
}
