import { SummaryCard } from "@/components/summary-card";
import { SemesterColumn } from "@/components/semester-column";

const courseData = {
  completed: {
    title: "Completed",
    credits: 45,
    courses: [
      {
        code: "CS 3345",
        title: "Data Structures and Introduction to Algorithmic Analysis",
        professor: "Dr. Greg Ozbirn",
        badge: "Core Requirement" as const,
        whyText: "Foundation for all upper-division CS courses.",
      },
      {
        code: "CS 3354",
        title: "Software Engineering",
        professor: "Dr. Wei Yang",
        badge: "Core Requirement" as const,
        whyText: "Essential for understanding software development lifecycle.",
      },
      {
        code: "MATH 2418",
        title: "Linear Algebra",
        professor: "Dr. Zalman Balanov",
        badge: "Core Requirement" as const,
        whyText: "Mathematical foundation for graphics and ML courses.",
      },
    ],
  },
  fall2025: {
    title: "Fall 2025",
    credits: 12,
    courses: [
      {
        code: "CS 4348",
        title: "Operating Systems Concepts",
        professor: "Dr. Neeraj Gupta",
        badge: "Core Requirement" as const,
        whyText: "Critical for systems programming and interviews.",
      },
      {
        code: "CS 4349",
        title: "Advanced Algorithm Design and Analysis",
        professor: "Dr. Balaji Raghavachari",
        badge: "Core Requirement" as const,
        whyText: "Builds on CS 3345 and essential for technical interviews.",
      },
      {
        code: "CS 3341",
        title: "Probability and Statistics in Computer Science",
        professor: "Dr. Haim Schweitzer",
        badge: "Core Requirement" as const,
        whyText: "Required for machine learning and AI courses.",
      },
    ],
  },
  spring2026: {
    title: "Spring 2026",
    credits: 9,
    courses: [
      {
        code: "CS 4386",
        title: "Compiler Design",
        professor: "Dr. Kevin Hamlen",
        badge: "Track Elective" as const,
        whyText: "Deepens understanding of programming languages.",
      },
      {
        code: "CS 4389",
        title: "Data and Applications Security",
        professor: "Dr. Bhavani Thuraisingham",
        badge: "Track Elective" as const,
        whyText: "High-demand security skills for industry.",
      },
    ],
  },
  fall2026: {
    title: "Fall 2026",
    credits: 9,
    courses: [
      {
        code: "CS 4365",
        title: "Artificial Intelligence",
        professor: "Dr. Vibhav Gogate",
        badge: "Track Elective" as const,
        whyText: "Covers fundamental AI concepts and techniques.",
      },
      {
        code: "CS 4375",
        title: "Introduction to Machine Learning",
        professor: "Dr. Feng Chen",
        badge: "Track Elective" as const,
        whyText: "Practical ML skills highly valued in industry.",
      },
    ],
  },
};

export default function PlanPage() {
  return (
    <main className="min-h-screen bg-background relative">
      <div className="relative z-10 pt-28 pb-16 px-8">
        <div className="max-w-7xl mx-auto">
          {/* Summary Card */}
          <SummaryCard />

          {/* Semester Columns */}
          <div className="mt-14 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            <SemesterColumn
              {...courseData.completed}
              isCompleted={true}
              baseDelay={0}
            />
            <SemesterColumn
              {...courseData.fall2025}
              baseDelay={300}
            />
            <SemesterColumn
              {...courseData.spring2026}
              baseDelay={600}
            />
            <SemesterColumn
              {...courseData.fall2026}
              baseDelay={800}
            />
          </div>
        </div>
      </div>
    </main>
  );
}
