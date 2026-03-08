"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { AIAvatar } from "@/components/ai-avatar";
import { Download, Loader2 } from "lucide-react";
import { DndBoard, Course } from "@/components/dnd-board";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Fallback helper to detect UTD courses in text like "CS 1337" or "MATH 2418"
// Includes all common UTD subject prefixes for multi-disciplinary degree plans
const COURSE_REGEX = /(?:CS|SE|CE|EE|MATH|STAT|PHYS|CGS|COGS|RHET|GOVT|ECS|BMEN|MECH|ENGR|HIST|HUMA|ARTS|ECON|PSY|SOC|COMM|ATCM|BA|FIN|MKT|ACCT|CHEM|BIOL|GEOS|NATS|IMS|MIS|OBHR|OPRE)[\s]\d{4}/gi;

// Detect semester mentions in user messages
const SEMESTER_REGEX = /(?:fall|spring|summer)\s*(?:20)?\d{2}/gi;

// Detect graduation year in user messages like "graduate by 2027" or "graduate Spring 2028"
const GRAD_YEAR_REGEX = /(?:graduat\w*|finish|done|complete)\s+(?:by\s+)?(?:(fall|spring|summer)\s+)?(\d{4})/i;
const GRAD_SEMESTER_REGEX = /(?:graduat\w*|finish)\s+(?:by\s+)?((?:fall|spring|summer)\s+\d{4})/i;

// Helper: generate semester labels from a start semester to a graduation semester
function generateSemesterLabels(start: string, gradSemester: string, includeSummer: boolean = false): string[] {
  const seasonOrder = ["Spring", "Summer", "Fall"];
  const labels: string[] = [];

  // Parse "Fall 2026" -> { season: "Fall", year: 2026 }
  const parse = (s: string) => {
    const parts = s.trim().split(/\s+/);
    return { season: parts[0], year: parseInt(parts[1]) };
  };

  const startParsed = parse(start);
  const gradParsed = parse(gradSemester);

  let { season, year } = startParsed;
  let idx = seasonOrder.indexOf(season);
  if (idx === -1) idx = 2; // default to Fall

  // Generate semesters
  for (let i = 0; i < 20; i++) { // safety cap at 20
    const label = `${seasonOrder[idx]} ${year}`;
    // Include Summer only if includeSummer is true
    if (seasonOrder[idx] !== "Summer" || includeSummer) {
      labels.push(label);
    }

    // Check if we've reached or passed graduation
    if (year > gradParsed.year || (year === gradParsed.year && idx >= seasonOrder.indexOf(gradParsed.season))) {
      break;
    }

    // Advance to next semester
    idx++;
    if (idx >= seasonOrder.length) {
      idx = 0;
      year++;
    }
  }

  return labels;
}

export default function SessionPage() {
  const [messages, setMessages] = useState<any[]>([]);
  const [isRecording, setIsRecording] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [advisorStatus, setAdvisorStatus] = useState<"listening" | "speaking" | "idle">("idle");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionEnded, setSessionEnded] = useState(false);
  const [sessionStarted, setSessionStarted] = useState(false); // Gate for autoplay policy
  const [targetSemester, setTargetSemester] = useState("Fall 2026");

  const [isGeneratingPlan, setIsGeneratingPlan] = useState(false);
  const [planGenerated, setPlanGenerated] = useState(false);
  const [earlyGradMode, setEarlyGradMode] = useState(false);
  const [expectedGradDate, setExpectedGradDate] = useState<string | null>(null);
  const [displayGpa, setDisplayGpa] = useState<number | null>(null);
  const [displayCredits, setDisplayCredits] = useState(0);
  const [displayTotalRequired, setDisplayTotalRequired] = useState(124);
  const [displayMajor, setDisplayMajor] = useState("Computer Science");
  const [displayMinor, setDisplayMinor] = useState<string | null>(null);
  const [showRegenConfirm, setShowRegenConfirm] = useState(false);
  const [regenReason, setRegenReason] = useState("");

  // Prerequisite map for DnD validation (course_code -> [prereq_codes])
  const [prereqMap, setPrereqMap] = useState<Record<string, string[]>>({});
  
  // DND Board State — initialized with just inProgress; semester columns built in useEffect from transcript
  const [columns, setColumns] = useState<Record<string, any>>({
    inProgress: {
      title: "In Progress (Spring 2026)",
      credits: 0,
      courses: [],
      isCompleted: false,
      isInProgress: true,
    },
  });

  const chatHistory = useRef<any[]>([]);
  const messageCount = useRef(0);
  const transcriptCtx = useRef<string | null>(null);
  const transcriptGpa = useRef<number | null>(null);
  const transcriptCredits = useRef<number>(0);
  const transcriptMajor = useRef<string>("Computer Science");
  const transcriptStartSem = useRef<string | null>(null);
  const transcriptExpectedGrad = useRef<string | null>(null);
  const transcriptCompletedCodes = useRef<string[]>([]);
  
  // Voice feature refs
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const recognitionRef = useRef<any>(null);
  const silenceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const isPlayingRef = useRef(false); // Guard against audio self-interrupt
  const boardScrollRef = useRef<HTMLDivElement | null>(null); // Scroll container for DnD board
  const handleSendRef = useRef<(text: string) => void>(() => {}); // Always-current handleSend

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
          `GPA: ${t.gpa}`,
          `Total Credit Hours: ${t.total_credit_hours}`,
          `Completed Courses: ${courseListText}`,
        ].join("\n");

        // Store GPA and credits for plan generation
        transcriptGpa.current = t.gpa || null;
        transcriptCredits.current = t.total_credit_hours || 0;
        transcriptMajor.current = t.major || "Computer Science";

        // Extract completed course codes (excluding W and IP)
        transcriptCompletedCodes.current = validCourses
          .filter((c: any) => c.grade !== "IP")
          .map((c: any) => c.course_code);

        // Determine start semester (earliest semester in transcript)
        const allSemesters = validCourses
          .map((c: any) => c.semester)
          .filter((s: string) => s && !s.includes("Transfer") && s !== "Unknown");
        if (allSemesters.length > 0) {
          // Sort semesters chronologically: "2024 Fall" -> sort by year then season
          const seasonOrder: Record<string, number> = { "Spring": 0, "Summer": 1, "Fall": 2 };
          allSemesters.sort((a: string, b: string) => {
            const [yearA, seasonA] = a.split(" ");
            const [yearB, seasonB] = b.split(" ");
            if (yearA !== yearB) return parseInt(yearA) - parseInt(yearB);
            return (seasonOrder[seasonA] || 0) - (seasonOrder[seasonB] || 0);
          });
          const earliest = allSemesters[0];
          // Convert "2024 Fall" to "Fall 2024" for the API
          const parts = earliest.split(" ");
          if (parts.length === 2) {
            transcriptStartSem.current = `${parts[1]} ${parts[0]}`;
          }
          // Calculate expected graduation: 4 years from start
          if (transcriptStartSem.current) {
            const startYear = parseInt(parts[0]);
            transcriptExpectedGrad.current = `Spring ${startYear + 4}`;
          }
        }

        // Set display state from transcript
        setDisplayGpa(t.gpa || null);
        setDisplayCredits(t.total_credit_hours || 0);
        setDisplayMajor(t.major || "Computer Science");
        if (transcriptExpectedGrad.current) {
          setExpectedGradDate(transcriptExpectedGrad.current);
        }

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
            grade: c.grade,
          };

          if (c.grade === "IP" || c.grade === "CR") {
            inProgressCourses.push(course);
          } else {
            const sem = c.semester || "Unknown";
            if (!completedBySemester[sem]) completedBySemester[sem] = [];
            completedBySemester[sem].push(course);
          }
        });

        // Set in-progress column and generate empty semester skeleton
        const ipCredits = inProgressCourses.length * 3;

        // Build initial columns: historical semesters first, then inProgress, then future
        const initColumns: Record<string, any> = {};

        // --- Historical semesters (chronological, read-only) ---
        const historicalSeasonOrder: Record<string, number> = { "Spring": 0, "Summer": 1, "Fall": 2 };
        const sortedHistoricalKeys = Object.keys(completedBySemester)
          .filter(s => s !== "Unknown" && !s.includes("Transfer"))
          .sort((a, b) => {
            const [yearA, seasonA] = a.split(" ");
            const [yearB, seasonB] = b.split(" ");
            if (yearA !== yearB) return parseInt(yearA) - parseInt(yearB);
            return (historicalSeasonOrder[seasonA] || 0) - (historicalSeasonOrder[seasonB] || 0);
          });

        // Add transfer credits as a special column if present
        if (completedBySemester["Transfer"]) {
          const transferKey = "hist_Transfer";
          initColumns[transferKey] = {
            title: "Transfer Credits",
            credits: completedBySemester["Transfer"].length * 3,
            courses: completedBySemester["Transfer"],
            isCompleted: true,
            isInProgress: false,
            isHistorical: true,
          };
        }

        for (const semKey of sortedHistoricalKeys) {
          // Convert "2024 Fall" to "Fall 2024" for display
          const parts = semKey.split(" ");
          const displayTitle = parts.length === 2 ? `${parts[1]} ${parts[0]}` : semKey;
          const columnKey = `hist_${semKey.replace(/\s+/g, "_")}`;
          initColumns[columnKey] = {
            title: displayTitle,
            credits: completedBySemester[semKey].length * 3,
            courses: completedBySemester[semKey],
            isCompleted: true,
            isInProgress: false,
            isHistorical: true,
          };
        }

        // --- In Progress column ---
        initColumns["inProgress"] = {
          title: "In Progress (Spring 2026)",
          credits: ipCredits,
          courses: inProgressCourses,
          isCompleted: false,
          isInProgress: true,
        };

        // Determine start semester for planning (next semester after current)
        const planStart = "Fall 2026";
        const gradTarget = transcriptExpectedGrad.current || "Spring 2028";
        const semLabels = generateSemesterLabels(planStart, gradTarget);

        for (const label of semLabels) {
          const key = label.replace(/\s+/g, "_");
          initColumns[key] = {
            title: label,
            credits: 0,
            courses: [],
          };
        }

        // Add graduation marker
        initColumns["graduation"] = {
          title: `🎓 ${gradTarget}`,
          credits: 0,
          courses: [],
        };

        setColumns(initColumns);
      } catch {}
    }
  }, []);

  // Auto-scroll the DnD board to the "In Progress" column on mount
  useEffect(() => {
    if (!boardScrollRef.current) return;
    // Wait a tick for columns to render
    const timer = setTimeout(() => {
      const container = boardScrollRef.current;
      if (!container) return;
      const inProgressCol = container.querySelector('[data-column-id="inProgress"]');
      if (inProgressCol) {
        const containerRect = container.getBoundingClientRect();
        const colRect = inProgressCol.getBoundingClientRect();
        // Scroll so inProgress is ~100px from the left edge
        const scrollTarget = container.scrollLeft + (colRect.left - containerRect.left) - 100;
        container.scrollTo({ left: Math.max(0, scrollTarget), behavior: "smooth" });
      }
    }, 400);
    return () => clearTimeout(timer);
  }, [Object.keys(columns).length]); // Re-run when columns change (e.g., transcript loaded)

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
            if (recognitionRef.current) {
              try { recognitionRef.current.stop(); } catch {}
            }
            // Use ref to always call the LATEST handleSend (avoids stale closure)
            handleSendRef.current(latestTranscript);
          }, 1500);
        };

        // Do NOT clear the silence timer in onspeechend — the timer calls handleSend
        // Just let the 1500ms timer fire naturally after speech ends
        recognition.onspeechend = () => {
          // no-op: let the silence timer handle it
        };

        recognition.onend = () => {
          setIsRecording(false);
          setAdvisorStatus((prev) => prev === "speaking" ? "speaking" : "idle");
        };

        recognition.onerror = (event: any) => {
          // Suppress expected/non-fatal errors
          if (["aborted", "network", "no-speech"].includes(event.error)) {
            setIsRecording(false);
            setAdvisorStatus("idle");
            return;
          }
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
    // Guard: don't interrupt ongoing playback
    if (isPlayingRef.current) return;
    isPlayingRef.current = true;

    // Stop speech recognition so we don't pick up our own audio output
    if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
    if (recognitionRef.current) {
      try { recognitionRef.current.abort(); } catch {}
    }
    setIsRecording(false);

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
        // Auto-start listening after advisor finishes speaking
        setTimeout(() => startListening(), 300);
      };

      audio.onerror = () => {
        URL.revokeObjectURL(url);
        isPlayingRef.current = false;
        setIsSpeaking(false);
        setAdvisorStatus("listening");
        if (onEnded) onEnded();
        setTimeout(() => startListening(), 300);
      };

      await audio.play().catch(e => {
        console.warn("Autoplay was blocked by browser:", e);
        URL.revokeObjectURL(url);
        isPlayingRef.current = false;
        setIsSpeaking(false);
        setAdvisorStatus("idle");
        if (onEnded) onEnded();
      });

    } catch (error) {
      console.error("Audio playback error:", error);
      isPlayingRef.current = false;
      setIsSpeaking(false);
      setAdvisorStatus("idle");
      if (onEnded) onEnded();
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

  // Start chat on mount — autoplay is allowed because user interacted on the home/upload page
  useEffect(() => {
    const startChat = async () => {
      setSessionStarted(true);
      try {
        const res = await fetch(`${API_BASE}/api/voice/start`, { method: "POST" });
        if (res.ok) {
          const data = await res.json();
          chatHistory.current = data.history;
          playAudio(data.reply);
        } else {
          playAudio("Hey! I'm Pam, your academic advisor. What courses are you thinking about?");
        }
      } catch (err) {
        playAudio("Hey! I'm Pam, your academic advisor. What courses are you thinking about?");
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

  // Bulk fetch professor data for multiple courses in a single request
  const fetchBulkProfessors = async (courseCodes: string[]) => {
    if (courseCodes.length === 0) return;

    // Helper to update columns with results (or fallback to TBD)
    const updateColumnsWithResults = (results: Record<string, any>) => {
      setColumns(prev => {
        const updated: Record<string, any> = {};
        for (const key of Object.keys(prev)) {
          updated[key] = {
            ...prev[key],
            courses: prev[key].courses.map((c: any) => {
              const profData = results[c.code];
              if (profData && profData.professor) {
                return {
                  ...c,
                  professor: profData.display || profData.professor,
                  aRate: profData.a_rate,
                };
              } else if (c.professor === "Loading...") {
                return { ...c, professor: "TBD" };
              }
              return c;
            }),
          };
        }
        return updated;
      });
    };

    try {
      const res = await fetch(`${API_BASE}/api/courses/bulk-professors`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ course_codes: courseCodes }),
      });
      if (!res.ok) {
        // On error, still update Loading... to TBD
        updateColumnsWithResults({});
        return;
      }
      const data = await res.json();
      const results = data.results || {};
      updateColumnsWithResults(results);
    } catch {
      // On network error, update Loading... to TBD
      updateColumnsWithResults({});
    }
  };

  // Execute structured board actions returned by the AI (ADD, REMOVE, MOVE)
  const executeBoardActions = (actions: Array<{action: string; course_code: string; semester: string; to_semester?: string}>) => {
    if (!actions || actions.length === 0) return;

    setColumns(prev => {
      const updated = { ...prev };

      // Deep-copy each column to avoid mutation
      for (const key of Object.keys(updated)) {
        updated[key] = { ...updated[key], courses: [...updated[key].courses] };
      }

      for (const act of actions) {
        const semKey = act.semester.replace(/\s+/g, "_");
        const toSemKey = act.to_semester?.replace(/\s+/g, "_");

        if (act.action === "ADD") {
          // Ensure the target column exists; create it if needed
          if (!updated[semKey]) {
            updated[semKey] = { title: act.semester, credits: 0, courses: [] };
          }
          // Don't add if course already exists in that column
          const alreadyThere = updated[semKey].courses.some((c: any) => c.code === act.course_code);
          if (!alreadyThere) {
            const newCourse: Course = {
              id: `${act.course_code}-${Math.random().toString(36).substr(2, 9)}`,
              code: act.course_code,
              title: act.course_code, // will be enriched
              professor: "Loading...",
              badge: "Degree Plan" as const,
              whyText: "Added by advisor.",
              credits: 3,
            };
            updated[semKey].courses.push(newCourse);
            updated[semKey].credits = (updated[semKey].credits || 0) + 3;
            // Enrich in background
            fetchAndEnrichCourse(act.course_code);
          }
        } else if (act.action === "REMOVE") {
          if (updated[semKey]) {
            const before = updated[semKey].courses.length;
            updated[semKey].courses = updated[semKey].courses.filter((c: any) => c.code !== act.course_code);
            const removed = before - updated[semKey].courses.length;
            updated[semKey].credits = Math.max(0, (updated[semKey].credits || 0) - removed * 3);
          }
        } else if (act.action === "MOVE" && toSemKey) {
          // Remove from source
          let movedCourse: any = null;
          if (updated[semKey]) {
            const idx = updated[semKey].courses.findIndex((c: any) => c.code === act.course_code);
            if (idx !== -1) {
              movedCourse = updated[semKey].courses.splice(idx, 1)[0];
              updated[semKey].credits = Math.max(0, (updated[semKey].credits || 0) - (movedCourse.credits || 3));
            }
          }
          // Add to target
          if (movedCourse) {
            if (!updated[toSemKey]) {
              updated[toSemKey] = { title: act.to_semester!, credits: 0, courses: [] };
            }
            updated[toSemKey].courses.push(movedCourse);
            updated[toSemKey].credits = (updated[toSemKey].credits || 0) + (movedCourse.credits || 3);
          }
        }
      }

      return updated;
    });
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

      // Find the first future semester column (not inProgress, not graduation)
      const targetKey = Object.keys(prevCols).find(
        k => k !== "inProgress" && k !== "graduation" && (prevCols[k].courses || []).length < 6
      );
      if (!targetKey) return prevCols;

      // Cap: don't exceed 15 credits (5 courses) in target column
      const currentCredits = prevCols[targetKey].credits || 0;
      const maxNewCredits = 15 - currentCredits;
      const maxNewCourses = Math.floor(maxNewCredits / 3);
      if (maxNewCourses <= 0) return prevCols;

      const cappedCodes = newCodes.slice(0, maxNewCourses);
      addedCodes = cappedCodes;

      const newCourses = cappedCodes.map(code => ({
        id: code + "-" + Math.random().toString(36).substr(2, 9),
        code: code,
        title: code, // placeholder until enriched
        professor: "Loading...",
        badge: "Core Requirement" as const,
        whyText: "Matches your career interests and degree plan.",
      }));

      return {
        ...prevCols,
        [targetKey]: {
          ...prevCols[targetKey],
          credits: prevCols[targetKey].credits + (newCourses.length * 3),
          courses: [...prevCols[targetKey].courses, ...newCourses],
        }
      };
    });

    // Enrich asynchronously (won't block the voice response)
    for (const code of addedCodes) {
      fetchAndEnrichCourse(code);
    }
  };

  const handleSend = async (userText: string) => {
    if (!userText.trim() || isLoading) return;

    messageCount.current += 1;
    setIsLoading(true);

    // Detect target semester from user message
    detectTargetSemester(userText);

    // Detect early graduation intent from voice
    if (/graduate\s*early|finish\s*early|graduate.*sooner|3\s*years?|accelerat/i.test(userText)) {
      setEarlyGradMode(true);
    }

    // Detect specific graduation year/semester from user (e.g. "graduate by 2027" or "graduate Spring 2028")
    let detectedGradTarget: string | null = null;
    const gradSemMatch = userText.match(GRAD_SEMESTER_REGEX);
    const gradYearMatch = userText.match(GRAD_YEAR_REGEX);
    if (gradSemMatch) {
      const raw = gradSemMatch[1].trim();
      const parts = raw.split(/\s+/);
      const season = parts[0].charAt(0).toUpperCase() + parts[0].slice(1).toLowerCase();
      detectedGradTarget = `${season} ${parts[1]}`;
    } else if (gradYearMatch) {
      const year = gradYearMatch[2];
      const season = gradYearMatch[1]
        ? gradYearMatch[1].charAt(0).toUpperCase() + gradYearMatch[1].slice(1).toLowerCase()
        : "Spring";
      detectedGradTarget = `${season} ${year}`;
    }

    if (detectedGradTarget) {
      transcriptExpectedGrad.current = detectedGradTarget;
      setExpectedGradDate(detectedGradTarget);
    }

    try {
      // Build a compact summary of the current board state for the AI
      const boardSummary = Object.entries(columns)
        .filter(([key]) => key !== "graduation")
        .map(([, col]) => {
          const courseCodes = (col.courses || []).map((c: any) => c.code).join(", ");
          return `${col.title}: ${courseCodes || "(empty)"} [${col.credits || 0} credits]`;
        }).join("\n");

      const fullContext = [
        transcriptCtx.current || "",
        `\nCURRENT BOARD STATE (these are the semester columns the student sees):\n${boardSummary}`,
        expectedGradDate ? `\nExpected Graduation: ${expectedGradDate}` : "",
      ].join("");

      const res = await fetch(`${API_BASE}/api/voice/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userText,
          history: chatHistory.current,
          transcript_context: fullContext,
          concise: true,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        chatHistory.current = data.history;

        // Execute structured board actions from AI (ADD, REMOVE, MOVE)
        if (data.board_actions && data.board_actions.length > 0) {
          executeBoardActions(data.board_actions);
        } else {
          // Fallback: parse course codes from text for backward compat
          await extractAndAddCourses(data.reply);
        }

        // Check for SUGGEST_REGENERATE action from backend
        if (data.suggest_regenerate) {
          setRegenReason(data.suggest_regenerate_reason || "Your goals have changed");
          setShowRegenConfirm(true);
        }

        // Detect and persist minor from conversation
        const detectedMinor = extractMinorFromChat();
        if (detectedMinor && detectedMinor !== displayMinor) {
          setDisplayMinor(detectedMinor);
        }

        playAudio(data.reply);

        // If a graduation year was detected and we already have a plan, auto-regenerate
        if (detectedGradTarget && planGenerated) {
          setTimeout(() => handleGeneratePlan(), 500);
        }
      } else {
        playAudio("I had trouble understanding that. Could you try again?");
      }
    } catch (err) {
      playAudio("I'm having trouble connecting. Please try again.");
    }

    setIsLoading(false);
  };

  // Keep the ref always pointing to the latest handleSend (fixes stale closure in SpeechRecognition useEffect)
  handleSendRef.current = handleSend;

  // Called when user drags a course between semesters on the DnD board
  const handleCourseMove = useCallback(async (courseCode: string, fromSemester: string, toSemester: string) => {
    if (!transcriptCtx.current) return;

    const moveMessage = `I just moved ${courseCode} from "${fromSemester}" to "${toSemester}". Is this a good idea? Does it affect my plan?`;

    // Include board state so AI knows the full picture
    const boardSummary = Object.entries(columns)
      .filter(([key]) => key !== "graduation")
      .map(([, col]) => {
        const courseCodes = (col.courses || []).map((c: any) => c.code).join(", ");
        return `${col.title}: ${courseCodes || "(empty)"} [${col.credits || 0} credits]`;
      }).join("\n");

    const fullContext = [
      transcriptCtx.current || "",
      `\nCURRENT BOARD STATE:\n${boardSummary}`,
      expectedGradDate ? `\nExpected Graduation: ${expectedGradDate}` : "",
    ].join("");

    try {
      const res = await fetch(`${API_BASE}/api/voice/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: moveMessage,
          history: chatHistory.current,
          transcript_context: fullContext,
          concise: true,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        chatHistory.current = data.history;
        playAudio(data.reply);
      }
    } catch {}
  }, [columns, expectedGradDate]);

  const handleMicToggle = useCallback(() => {
    if (isSpeaking) return; // Don't allow recording while AI is speaking
    if (isRecording && recognitionRef.current) {
      // Stop recording
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
      recognitionRef.current.stop();
      setIsRecording(false);
      setAdvisorStatus("idle");
    } else {
      startListening();
    }
  }, [isRecording, isSpeaking]);

  const handleExportPlan = useCallback(() => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(columns, null, 2));
    const a = document.createElement("a");
    a.href = dataStr;
    a.download = "comet-academic-plan.json";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }, [columns]);

  // State for feedback loading
  const [isGettingFeedback, setIsGettingFeedback] = useState(false);

  // Extract minor from chat history (defined here so it can be used by both handleGetFeedback and handleGeneratePlan)
  const extractMinorFromChat = useCallback(() => {
    const history = chatHistory.current;
    if (!history || history.length === 0) return null;
    const combinedText = history.map((m: any) => m.content || "").join(" ").toLowerCase();
    const minorPatterns = [
      /(?:want|pursuing|doing|have|taking|declared?|interested in)\s+(?:a\s+)?(\w+)\s+minor/i,
      /(\w+)\s+minor/i,
      /minor\s+in\s+(\w+)/i,
    ];
    for (const pattern of minorPatterns) {
      const match = combinedText.match(pattern);
      if (match) {
        const m = match[1].trim();
        if (!["a", "the", "my", "your", "this", "that"].includes(m.toLowerCase())) {
          return m.charAt(0).toUpperCase() + m.slice(1);
        }
      }
    }
    return null;
  }, []);

  // Get comprehensive feedback on the current board state
  const handleGetFeedback = useCallback(async () => {
    if (!transcriptCtx.current || isGettingFeedback || isLoading) return;
    setIsGettingFeedback(true);

    // Build detailed board state
    const boardSummary = Object.entries(columns)
      .filter(([key]) => key !== "graduation")
      .map(([, col]) => {
        const courseCodes = (col.courses || []).map((c: any) => c.code).join(", ");
        return `${col.title}: ${courseCodes || "(empty)"} [${col.credits || 0} credits]`;
      }).join("\n");

    const feedbackRequest = `Please review my ENTIRE current degree plan and give me comprehensive feedback.

CURRENT BOARD STATE:
${boardSummary}

Please evaluate:
1. Are there any prerequisite violations? (courses placed before their prereqs)
2. Are any semesters overloaded (>18 credits) or too light (<12 credits)?
3. Does the overall timeline make sense for graduation by ${expectedGradDate || "my expected date"}?
4. Any difficult courses bunched together that might hurt my GPA?
5. Am I making good progress toward my ${displayMajor} degree?
${extractMinorFromChat() ? `6. Am I on track for my ${extractMinorFromChat()} minor?` : ""}

Be concise but thorough. Point out specific issues if any.`;

    const fullContext = [
      transcriptCtx.current || "",
      `\nCURRENT BOARD STATE:\n${boardSummary}`,
      expectedGradDate ? `\nTarget Graduation: ${expectedGradDate}` : "",
    ].join("");

    try {
      const res = await fetch(`${API_BASE}/api/voice/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: feedbackRequest,
          history: chatHistory.current,
          transcript_context: fullContext,
          concise: false, // Want detailed feedback here
        }),
      });

      if (res.ok) {
        const data = await res.json();
        chatHistory.current = data.history;
        playAudio(data.reply);
      } else {
        playAudio("I had trouble generating feedback. Please try again.");
      }
    } catch {
      playAudio("Couldn't connect to get feedback. Please try again.");
    }

    setIsGettingFeedback(false);
  }, [columns, expectedGradDate, displayMajor, isGettingFeedback, isLoading, extractMinorFromChat]);

  const buildColumnsFromPlan = async (plan: {semesters: any[], graduation_semester: string, note?: string, prerequisite_chains?: Record<string, string[]>}) => {
    const newColumns: Record<string, any> = {};

    // Preserve all historical (past) semester columns
    Object.entries(columns).forEach(([key, col]) => {
      if (col.isHistorical) {
        newColumns[key] = col;
      }
    });

    // Preserve in-progress column
    newColumns.inProgress = columns.inProgress;

    // Fetch enriched data from /api/nebula
    const allCourseCodes = plan.semesters.flatMap((s: any) => (s.courses || []).map((c: any) => c.code));
    let profResults: Record<string, any> = {};
    if (allCourseCodes.length > 0) {
      try {
        const res = await fetch('/api/nebula', {
          method: 'POST',
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ course_codes: allCourseCodes }),
        });
        if (res.ok) {
          const data = await res.json();
          profResults = data.results || {};
        }
      } catch (e) {
        console.error("Failed to fetch from /api/nebula", e);
      }
    }

    plan.semesters.forEach((sem: any) => {
      const key = sem.semester.replace(/\s+/g, "_");
      const courses = (sem.courses || []).map((c: any) => {
        const pData = profResults[c.code];
        const profName = pData && pData.professor ? (pData.display || pData.professor) : "TBD";
        return {
          id: `${c.code}-${Math.random().toString(36).substr(2, 9)}`,
          code: c.code,
          title: c.title || c.code,
          professor: profName,
          badge: "Degree Plan" as const,
          whyText: c.reason || "Part of your degree plan.",
          credits: c.credits || 3,
          aRate: pData?.a_rate,
        };
      });
      const totalCredits = courses.reduce((sum: number, c: any) => sum + (c.credits || 3), 0);

      newColumns[key] = {
        title: sem.semester,
        credits: totalCredits,
        courses,
      };
    });

    // Add graduation marker column
    if (plan.graduation_semester) {
      const gradKey = "graduation";
      newColumns[gradKey] = {
        title: `🎓 ${plan.graduation_semester}`,
        credits: 0,
        courses: [],
      };
    }

    setColumns(newColumns);
    setPlanGenerated(true);

    // Store prerequisite chains for DnD validation
    if (plan.prerequisite_chains) {
      setPrereqMap(plan.prerequisite_chains);
    }

    // Update expected graduation from plan response
    if (plan.graduation_semester && plan.graduation_semester !== "Unknown") {
      setExpectedGradDate(plan.graduation_semester);
    }
  };

  const handleGeneratePlan = async () => {
    if (isGeneratingPlan || !transcriptCtx.current) return;
    setIsGeneratingPlan(true);

    try {
      const t = JSON.parse(sessionStorage.getItem("transcriptData") || "{}");

      // Determine the next semester to start planning from
      // Use the target semester from conversation, or compute from current date
      const planStartSemester = targetSemester;

      // Use persisted minor or extract from conversation history
      const detectedMinor = displayMinor || extractMinorFromChat();

      const res = await fetch(`${API_BASE}/api/recommend/full-plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          transcript_context: transcriptCtx.current,
          current_semester: planStartSemester,
          total_credit_hours: t.total_credit_hours || 0,
          gpa: t.gpa || null,
          start_semester: transcriptStartSem.current,
          target_graduation: expectedGradDate || transcriptExpectedGrad.current,
          major: transcriptMajor.current,
          completed_courses: transcriptCompletedCodes.current,
          accelerate: earlyGradMode,
          conversation_history: chatHistory.current,
          minor: detectedMinor,
        }),
      });

      if (res.ok) {
        const plan = await res.json();
        if (plan.semesters && plan.semesters.length > 0) {
          await buildColumnsFromPlan(plan);
          const noteText = plan.note ? ` ${plan.note}` : "";
          const accelMsg = earlyGradMode && plan.acceleration_possible === false
            ? " Early graduation isn't feasible with your remaining requirements."
            : earlyGradMode && plan.acceleration_possible
            ? " This is an accelerated schedule!"
            : "";
          playAudio(
            `Your ${plan.total_semesters}-semester plan is ready! Graduating ${plan.graduation_semester}.${accelMsg} Scroll right to see all semesters and drag to customize.${noteText}`
          );
        } else {
          playAudio("I had trouble building the plan. Try asking me about specific semesters instead.");
        }
      }
    } catch {
      playAudio("Couldn't generate the plan right now. Please try again.");
    }

    setIsGeneratingPlan(false);
  };

  // Handle confirm regeneration
  const handleConfirmRegenerate = useCallback(() => {
    setShowRegenConfirm(false);
    handleGeneratePlan();
  }, []);

  return (
    <div className="min-h-screen bg-background flex flex-col pt-24 pb-12 px-8">
      {/* Regeneration Confirmation Modal */}
      {showRegenConfirm && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center">
          <div className="bg-[#1a1a3a] border border-violet-500/30 rounded-2xl p-6 max-w-md mx-4 shadow-[0_0_40px_rgba(139,92,246,0.2)] animate-in fade-in zoom-in-95 duration-200">
            <h3 className="text-lg font-semibold text-foreground mb-2" style={{ fontFamily: "'Figtree', sans-serif" }}>
              Update Your Plan?
            </h3>
            <p className="text-muted-foreground text-sm mb-4">
              {regenReason}. Would you like me to generate an updated degree plan?
            </p>
            <div className="flex gap-3">
              <button
                onClick={handleConfirmRegenerate}
                className="flex-1 px-4 py-2.5 rounded-xl bg-violet-600 hover:bg-violet-500 text-white font-semibold text-sm transition-all"
              >
                Yes, Update Plan
              </button>
              <button
                onClick={() => setShowRegenConfirm(false)}
                className="flex-1 px-4 py-2.5 rounded-xl border border-white/10 text-muted-foreground hover:bg-white/5 font-semibold text-sm transition-all"
              >
                Not Now
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto w-full flex flex-col items-center">

        {/* End Session Button pinned to Navbar right corner */}
        {!sessionEnded && (
          <button
            onClick={() => {
              if (recognitionRef.current) {
                try { recognitionRef.current.abort(); } catch {}
              }
              if (audioRef.current) {
                audioRef.current.pause();
                audioRef.current.src = "";
              }
              setIsRecording(false);
              setIsSpeaking(false);
              setAdvisorStatus("idle");
              setSessionEnded(true);
            }}
            className="fixed top-3 right-6 z-[60] px-5 py-2.5 rounded-full border border-[#7B2FBE] text-[#F5F5FF] bg-transparent hover:bg-[#7B2FBE] transition-colors font-semibold text-sm"
          >
            End Session
          </button>
        )}

        {/* Top Center: Voice Avatar */}
        <div className="flex flex-col items-center mb-8 relative">
           <AIAvatar isSpeaking={isSpeaking} status={advisorStatus} />
           
           {isLoading && (
             <div className="mt-4 flex items-center gap-2 text-muted-foreground animate-pulse">
               <Loader2 className="w-4 h-4 animate-spin" />
               <span className="text-sm">Thinking...</span>
             </div>
           )}

           {/* Manual Mic Start/Stop Button */}
           {!isLoading && !isSpeaking && (
             <button 
               onClick={handleMicToggle}
               className={`mt-6 px-5 py-2.5 rounded-full border flex items-center gap-2.5 transition-all shadow-sm ${
                 isRecording
                   ? "border-red-500/50 bg-red-500/10 text-red-400 hover:bg-red-500/20"
                   : "border-violet/20 text-muted-foreground hover:bg-violet/10 hover:border-violet"
               }`}
             >
               <span className={`w-2.5 h-2.5 rounded-full ${isRecording ? "bg-red-500 animate-pulse" : "bg-green-500"}`} />
               {isRecording ? "Stop Recording" : "Start Recording"}
             </button>
           )}
        </div>

        {/* Graduation Summary Bar */}
        {transcriptCtx.current && (
          <div className="w-full mb-8">
            <div className="bg-[#141428]/60 border border-violet/10 rounded-2xl p-6 backdrop-blur-sm">
              <div className="flex items-center justify-between flex-wrap gap-4 mb-4">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">🎓</span>
                  <div>
                    <p className="text-[11px] text-muted-foreground uppercase tracking-wider font-medium">Expected Graduation</p>
                    <p className="text-xl font-bold text-foreground" style={{ fontFamily: "'Figtree', sans-serif" }}>
                      {expectedGradDate || "Generate a plan to see"}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-5 text-sm text-muted-foreground">
                  <div className="flex items-center gap-1.5">
                    <span className="text-base">📚</span>
                    <span>{displayCredits}<span className="text-muted-foreground/50">/{displayTotalRequired}</span></span>
                  </div>
                  {displayGpa !== null && (
                    <div className="flex items-center gap-1.5">
                      <span className="text-base">📊</span>
                      <span>{displayGpa.toFixed(2)}</span>
                    </div>
                  )}
                  <div className="flex items-center gap-1.5">
                    <span className="text-base">💻</span>
                    <span>{displayMajor}</span>
                  </div>
                  {displayMinor && (
                    <div className="flex items-center gap-1.5">
                      <span className="text-base">📖</span>
                      <span className="text-violet-400">{displayMinor} Minor</span>
                    </div>
                  )}
                </div>
              </div>
              
              <div className="flex items-center gap-3 pt-4 border-t border-white/5">
                <button
                  onClick={handleGeneratePlan}
                  disabled={isGeneratingPlan || isLoading}
                  className="px-6 py-3 rounded-xl bg-violet-600/80 hover:bg-violet-600 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-sm flex items-center gap-2.5 shadow-[0_0_20px_rgba(139,92,246,0.3)] hover:shadow-[0_0_30px_rgba(139,92,246,0.5)] transition-all"
                >
                  {isGeneratingPlan ? (
                    <><Loader2 className="w-4 h-4 animate-spin" /> Generating...</>
                  ) : (
                    <>🎓 Generate Full Plan</>
                  )}
                </button>

                {planGenerated && (
                  <button
                    onClick={handleGetFeedback}
                    disabled={isGettingFeedback || isLoading}
                    className="px-5 py-3 rounded-xl border border-cyan-500/30 bg-cyan-500/10 text-cyan-400 text-sm font-semibold flex items-center gap-2 hover:bg-cyan-500/20 hover:border-cyan-500/50 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                  >
                    {isGettingFeedback ? (
                      <><Loader2 className="w-4 h-4 animate-spin" /> Reviewing...</>
                    ) : (
                      <>💬 Get Feedback</>
                    )}
                  </button>
                )}


              </div>
            </div>
          </div>
        )}

        {/* Below Avatar: Drag and Drop Interactive Board */}
        <div className="w-full">
           <DndBoard
             columns={columns}
             setColumns={setColumns}
             prereqMap={prereqMap}
             completedCourses={transcriptCompletedCodes.current}
             onCourseMove={handleCourseMove}
             scrollContainerRef={boardScrollRef}
           />
        </div>

      </div>

      {/* Floating Export Button */}
      {sessionEnded && (
        <div className="fixed bottom-12 right-12 transition-all duration-500 z-50 animate-in fade-in zoom-in slide-in-from-bottom-8">
           <button onClick={handleExportPlan} className="px-6 py-4 rounded-xl bg-orange text-foreground font-[var(--font-heading)] font-semibold text-lg flex items-center gap-3 shadow-[0_0_30px_rgba(232,119,34,0.3)] hover:scale-105 transition-all">
             <Download className="w-5 h-5" />
             Export Final Plan
           </button>
        </div>
      )}

    </div>
  );
}
