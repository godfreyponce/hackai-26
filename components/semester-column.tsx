import { CourseCard } from "./course-card";

interface Course {
  code: string;
  title: string;
  professor: string;
  badge: "Core Requirement" | "Track Elective";
  whyText: string;
}

interface SemesterColumnProps {
  title: string;
  credits: number;
  courses: Course[];
  isCompleted?: boolean;
  baseDelay?: number;
}

export function SemesterColumn({
  title,
  credits,
  courses,
  isCompleted = false,
  baseDelay = 0,
}: SemesterColumnProps) {
  return (
    <div className="flex flex-col">
      {/* Header */}
      <div className="mb-6">
        <h2 
          className="font-[var(--font-heading)] font-black text-xl tracking-[-0.02em] text-foreground"
          style={{ fontFamily: "'Figtree', sans-serif" }}
        >
          {title}
        </h2>
        <p className="text-muted-foreground text-sm mt-1">
          {credits} credits
        </p>
      </div>

      {/* Course cards */}
      <div className="flex flex-col gap-4">
        {courses.map((course, index) => (
          <CourseCard
            key={course.code}
            {...course}
            isCompleted={isCompleted}
            delay={baseDelay + index * 100}
          />
        ))}
      </div>
    </div>
  );
}
