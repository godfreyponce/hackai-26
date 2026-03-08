"use client";

import { useState, useCallback } from "react";
import { StepProgress } from "@/components/step-progress";
import { AIAvatar } from "@/components/ai-avatar";
import { ConversationFeed } from "@/components/conversation-feed";

interface Message {
  id: string;
  content: string;
  isAdvisor: boolean;
}

const ADVISOR_QUESTIONS = [
  "What is your current major or intended major?",
  "What is your goal after graduation — industry, grad school, or still deciding?",
  "Are you more interested in software engineering, AI/ML, systems, or something else?",
];

export default function SessionPage() {
  const [currentStep, setCurrentStep] = useState(1);
  const [messages, setMessages] = useState<Message[]>([
    { id: "1", content: ADVISOR_QUESTIONS[0], isAdvisor: true },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [advisorStatus, setAdvisorStatus] = useState<"listening" | "speaking">("listening");

  const handleSend = useCallback(() => {
    if (!inputValue.trim()) return;

    // Add student message
    const studentMessage: Message = {
      id: Date.now().toString(),
      content: inputValue.trim(),
      isAdvisor: false,
    };
    setMessages((prev) => [...prev, studentMessage]);
    setInputValue("");

    // Simulate advisor responding
    if (currentStep < 3) {
      setAdvisorStatus("speaking");
      setIsSpeaking(true);

      setTimeout(() => {
        const nextQuestion: Message = {
          id: (Date.now() + 1).toString(),
          content: ADVISOR_QUESTIONS[currentStep],
          isAdvisor: true,
        };
        setMessages((prev) => [...prev, nextQuestion]);
        setCurrentStep((prev) => prev + 1);
        setIsSpeaking(false);
        setAdvisorStatus("listening");
      }, 1500);
    } else {
      setCurrentStep(3);
    }
  }, [inputValue, currentStep]);

  const handleMicToggle = useCallback(() => {
    setIsRecording((prev) => !prev);
    if (!isRecording) {
      setAdvisorStatus("listening");
    }
  }, [isRecording]);

  const isComplete = currentStep === 3 && messages.filter((m) => !m.isAdvisor).length >= 3;

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Main content with top padding for nav */}
      <div className="flex-1 flex flex-col pt-16">
        {/* Progress bar */}
        <div className="px-8 py-5 border-b border-violet/10">
          <div className="max-w-4xl mx-auto">
            <StepProgress currentStep={currentStep} totalSteps={3} />
          </div>
        </div>

        {/* Split layout */}
        <div className="flex-1 flex flex-col lg:flex-row">
          {/* Left Column - AI Avatar */}
          <div className="lg:w-1/2 p-8 lg:p-12 border-b lg:border-b-0 lg:border-r border-violet/10 flex items-center justify-center min-h-[300px] lg:min-h-0">
            <AIAvatar isSpeaking={isSpeaking} status={advisorStatus} />
          </div>

          {/* Right Column - Conversation Feed */}
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

        {/* Bottom CTA - appears after Step 3 */}
        <div
          className={`p-8 border-t border-violet/10 transition-all duration-500 ${
            isComplete ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4 pointer-events-none"
          }`}
        >
          <button className="w-full py-4 rounded-full bg-gradient-to-r from-purple to-teal text-foreground font-[var(--font-heading)] font-semibold text-lg hover:opacity-90 transition-opacity">
            Generate My Plan →
          </button>
        </div>
      </div>
    </div>
  );
}
