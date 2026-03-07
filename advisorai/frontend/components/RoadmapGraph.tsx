"use client";

interface RoadmapGraphProps {
  semesters: Array<{
    term: string;
    courses: string[];
  }>;
}

export function RoadmapGraph({ semesters }: RoadmapGraphProps) {
  return (
    <div className="flex gap-4 overflow-x-auto p-4">
      {semesters.map((semester) => (
        <div key={semester.term} className="min-w-[200px] p-4 border rounded-lg">
          <h3 className="font-bold mb-2">{semester.term}</h3>
          <ul className="space-y-1">
            {semester.courses.map((course) => (
              <li key={course} className="text-sm">{course}</li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
