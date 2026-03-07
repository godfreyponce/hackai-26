"use client";

interface ScheduleGridProps {
  courses: Array<{
    code: string;
    name: string;
    time: string;
    days: string[];
  }>;
}

export function ScheduleGrid({ courses }: ScheduleGridProps) {
  return (
    <div className="grid gap-4">
      {courses.map((course) => (
        <div key={course.code} className="p-3 border rounded">
          <span className="font-medium">{course.code}</span>
          <span className="ml-2">{course.days.join(", ")}</span>
          <span className="ml-2 text-gray-500">{course.time}</span>
        </div>
      ))}
    </div>
  );
}
