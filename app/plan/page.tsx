"use client";

import { useState, useEffect } from "react";
import { SummaryCard } from "@/components/summary-card";
import { SemesterColumn } from "@/components/semester-column";

// Fallback data if no real data available
const FALLBACK_COURSES = {
  completed: {
    title: "Completed",
    credits: 45,
    courses: [
      { code: "CS 3345", title: "Data Structures and Introduction to Algorithmic Analysis", professor: "Dr. Greg Ozbirn", badge: "Core Requirement" as const, whyText: "Foundation for all upper-division CS courses." },
      { code: "CS 3354", title: "Software Engineering", professor: "Dr. Wei Yang", badge: "Core Requirement" as const, whyText: "Essential for understanding software development lifecycle." },
      { code: "MATH 2418", title: "Linear Algebra", professor: "Dr. Zalman Balanov", badge: "Core Requirement" as const, whyText: "Mathematical foundation for graphics and ML courses." },
    ],
  },
  recommended: {
    title: "Recommended",
    credits: 15,
    courses: [
      { code: "CS 4348", title: "Operating Systems Concepts", professor: "Recommended", badge: "Core Requirement" as const, whyText: "Critical for systems programming and interviews." },
      { code: "CS 4349", title: "Advanced Algorithm Design and Analysis", professor: "Recommended", badge: "Core Requirement" as const, whyText: "Builds on CS 3345 and essential for technical interviews." },
    ],
  },
};

interface SemesterPlan {
  recommendations: Array<{
    course_code: string;
    course_name: string;
    reason: string;
    confidence_score: number;
    uncertainty_type: string | null;
  }>;
  advisor_message: string;
  total_credits: number;
  semester: string;
}

interface TranscriptData {
  student_name: string;
  major: string;
  gpa: number;
  total_credit_hours: number;
  completed_courses: Array<{
    course_code: string;
    course_name: string;
    grade: string;
    credit_hours: number;
    semester: string;
  }>;
}

export default function PlanPage() {
  const [plan, setPlan] = useState<SemesterPlan | null>(null);
  const [transcript, setTranscript] = useState<TranscriptData | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    // Load real data from sessionStorage
    const planData = sessionStorage.getItem("semesterPlan");
    const transcriptData = sessionStorage.getItem("transcriptData");

    if (planData) {
      setPlan(JSON.parse(planData));
    }
    if (transcriptData) {
      setTranscript(JSON.parse(transcriptData));
    }
    setIsLoaded(true);
  }, []);

  // Build completed courses for display (last 3 most recent semesters)
  const completedCourses = transcript
    ? transcript.completed_courses
        .filter((c) => c.grade !== "IP" && c.grade !== "W")
        .slice(-4)
        .map((c) => ({
          code: c.course_code,
          title: c.course_name,
          professor: `Grade: ${c.grade}`,
          badge: "Core Requirement" as const,
          whyText: `Completed in ${c.semester} with a grade of ${c.grade}.`,
        }))
    : FALLBACK_COURSES.completed.courses;

  // Build recommended courses from plan
  const recommendedCourses = plan
    ? plan.recommendations.map((r) => ({
        code: r.course_code,
        title: r.course_name,
        professor: r.uncertainty_type
          ? `Confidence: ${Math.round(r.confidence_score * 100)}% · ${r.uncertainty_type}`
          : `Confidence: ${Math.round(r.confidence_score * 100)}%`,
        badge: (r.reason.includes("Core") ? "Core Requirement" : "Track Elective") as "Core Requirement" | "Track Elective",
        whyText: r.reason,
      }))
    : FALLBACK_COURSES.recommended.courses;

  // Split recommendations into two semesters for visual display
  const midpoint = Math.ceil(recommendedCourses.length / 2);
  const semester1 = recommendedCourses.slice(0, midpoint);
  const semester2 = recommendedCourses.slice(midpoint);

  const completedCredits = transcript
    ? Math.round(transcript.total_credit_hours)
    : 45;

  const recCredits = plan ? plan.total_credits : 15;

  if (!isLoaded) return null;

  return (
    <main className="min-h-screen bg-background relative">
      <div className="relative z-10 pt-28 pb-16 px-8">
        <div className="max-w-7xl mx-auto">
          {/* Summary Card */}
          <SummaryCard
            advisorMessage={plan?.advisor_message}
            studentName={transcript?.student_name}
            completedCredits={completedCredits}
            major={transcript?.major}
            gpa={transcript?.gpa}
          />

          {/* Semester Columns */}
          <div className="mt-14 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            <SemesterColumn
              title={`Completed (${completedCredits} hrs)`}
              credits={completedCredits}
              courses={completedCourses}
              isCompleted={true}
              baseDelay={0}
            />
            <SemesterColumn
              title={plan?.semester || "Fall 2026"}
              credits={Math.round(recCredits * (midpoint / recommendedCourses.length))}
              courses={semester1}
              baseDelay={300}
            />
            {semester2.length > 0 && (
              <SemesterColumn
                title="Spring 2027"
                credits={Math.round(recCredits * (semester2.length / recommendedCourses.length))}
                courses={semester2}
                baseDelay={600}
              />
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
