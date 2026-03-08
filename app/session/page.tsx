"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { StepProgress } from "@/components/step-progress";
import { AIAvatar } from "@/components/ai-avatar";
import { ConversationFeed } from "@/components/conversation-feed";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Message {
  id: string;
  content: string;
  isAdvisor: boolean;
}

interface ChatHistoryItem {
  role: "user" | "model";
  content: string;
}

export default function SessionPage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(1);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [advisorStatus, setAdvisorStatus] = useState<"listening" | "speaking">("speaking");
  const [isGenerating, setIsGenerating] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const chatHistory = useRef<ChatHistoryItem[]>([]);
  const answersRef = useRef<string[]>([]);
  const messageCount = useRef(0);
  const transcriptCtx = useRef<string | null>(null);

  // Build transcript context from sessionStorage on mount
  useEffect(() => {
    const raw = sessionStorage.getItem("transcriptData");
    if (raw) {
      try {
        const t = JSON.parse(raw);
        const courseList = (t.completed_courses || [])
          .filter((c: any) => c.grade !== "W")
          .map((c: any) => `${c.course_code} (${c.course_name}, grade: ${c.grade}, ${c.semester})`)
          .join("; ");
        transcriptCtx.current = [
          `Student Name: ${t.student_name}`,
          `Student ID: ${t.student_id}`,
          `Major: ${t.major}`,
          `GPA: ${t.gpa}`,
          `Total Credit Hours: ${t.total_credit_hours}`,
          `Completed Courses: ${courseList}`,
        ].join("\n");
      } catch {}
    }
  }, []);

  // Start conversation with Gemini greeting on mount
  useEffect(() => {
    const startChat = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/voice/start`, {
          method: "POST",
        });
        if (res.ok) {
          const data = await res.json();
          setMessages([{
            id: "greeting",
            content: data.reply,
            isAdvisor: true,
          }]);
          chatHistory.current = data.history;
          setAdvisorStatus("listening");
          setIsSpeaking(false);
        }
      } catch (err) {
        // Fallback greeting
        setMessages([{
          id: "greeting",
          content: "Hey there! I'm Comet Advisor. What are you looking for this semester?",
          isAdvisor: true,
        }]);
        setAdvisorStatus("listening");
        setIsSpeaking(false);
      }
    };
    startChat();
  }, []);

  const handleSend = useCallback(async () => {
    if (!inputValue.trim() || isLoading) return;

    const userText = inputValue.trim();
    answersRef.current.push(userText);
    messageCount.current += 1;

    // Add student message immediately
    const studentMessage: Message = {
      id: Date.now().toString(),
      content: userText,
      isAdvisor: false,
    };
    setMessages((prev) => [...prev, studentMessage]);
    setInputValue("");
    setIsLoading(true);
    setAdvisorStatus("speaking");
    setIsSpeaking(true);

    // Update step progress
    const newStep = Math.min(messageCount.current, 3);
    setCurrentStep(newStep);

    try {
      // Call Gemini via our backend
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

        const advisorMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: data.reply,
          isAdvisor: true,
        };
        setMessages((prev) => [...prev, advisorMessage]);
      } else {
        setMessages((prev) => [...prev, {
          id: (Date.now() + 1).toString(),
          content: "I had trouble understanding that. Could you try again?",
          isAdvisor: true,
        }]);
      }
    } catch (err) {
      setMessages((prev) => [...prev, {
        id: (Date.now() + 1).toString(),
        content: "I'm having trouble connecting. Please try again.",
        isAdvisor: true,
      }]);
    }

    setIsLoading(false);
    setIsSpeaking(false);
    setAdvisorStatus("listening");
  }, [inputValue, isLoading]);

  const handleMicToggle = useCallback(() => {
    setIsRecording((prev) => !prev);
    if (!isRecording) {
      setAdvisorStatus("listening");
    }
  }, [isRecording]);

  const handleGeneratePlan = useCallback(async () => {
    setIsGenerating(true);

    try {
      const transcriptData = sessionStorage.getItem("transcriptData");
      const answers = answersRef.current;
      const careerGoal = answers.length >= 3 ? answers[2] : answers[answers.length - 1] || "";

      sessionStorage.setItem("careerGoal", careerGoal);
      sessionStorage.setItem("sessionAnswers", JSON.stringify({
        major: answers[0] || "",
        goal: answers[1] || "",
        interest: answers[2] || "",
      }));

      if (transcriptData) {
        const transcript = JSON.parse(transcriptData);
        const res = await fetch(`${API_BASE}/api/recommend/from-data`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ transcript, career_goal: careerGoal }),
        });
        if (res.ok) {
          const plan = await res.json();
          sessionStorage.setItem("semesterPlan", JSON.stringify(plan));
        }
      }

      router.push("/plan");
    } catch (err) {
      router.push("/plan");
    }
  }, [router]);

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <div className="flex-1 flex flex-col pt-16">
        {/* Progress bar */}
        <div className="px-8 py-5 border-b border-violet/10">
          <div className="max-w-4xl mx-auto">
            <StepProgress currentStep={currentStep} totalSteps={3} />
          </div>
        </div>

        {/* Split layout */}
        <div className="flex-1 flex flex-col lg:flex-row">
          <div className="lg:w-1/2 p-8 lg:p-12 border-b lg:border-b-0 lg:border-r border-violet/10 flex items-center justify-center min-h-[300px] lg:min-h-0">
            <AIAvatar isSpeaking={isSpeaking} status={advisorStatus} />
          </div>
          <div className="lg:w-1/2 flex flex-col flex-1 min-h-[400px] lg:min-h-0">
            <ConversationFeed
              messages={messages}
              inputValue={inputValue}
              onInputChange={setInputValue}
              onSend={handleSend}
              isRecording={isRecording}
              onMicToggle={handleMicToggle}
            />
          </div>
        </div>

        {/* Bottom CTA */}
        <div className="p-8 border-t border-violet/10">
          <button
            onClick={handleGeneratePlan}
            disabled={isGenerating}
            className={`w-full py-4 rounded-full bg-[#7B2FBE] text-foreground font-[var(--font-heading)] font-semibold text-lg transition-colors ${
              isGenerating ? "opacity-60 cursor-wait" : "hover:bg-[#9B5DE5]"
            }`}
          >
            {isGenerating ? "Generating your plan..." : "Generate My Plan →"}
          </button>
        </div>
      </div>
    </div>
  );
}
