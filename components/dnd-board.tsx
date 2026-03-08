"use client";

import React, { useState } from "react";
import {
  DndContext,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragOverlay,
  defaultDropAnimationSideEffects,
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { CourseCard } from "./course-card";

export interface Course {
  id: string; // unique ID needed for dnd-kit
  code: string;
  title: string;
  professor: string;
  badge: "Core Requirement" | "Track Elective" | "Degree Plan";
  whyText: string;
  aRate?: number; // A-rate percentage (0-100)
  credits?: number; // credit hours (default 3)
}

interface ColumnProps {
  id: string;
  title: string;
  credits: number;
  courses: Course[];
  isCompleted?: boolean;
  isInProgress?: boolean;
}

// Draggable Sortable Item Wrapper
function SortableCourseCard({ course, isCompleted, index }: { course: Course, isCompleted: boolean, index: number }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: course.id, data: { ...course } });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
    cursor: "grab",
  };

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <CourseCard
        code={course.code}
        title={course.title}
        professor={course.professor}
        badge={course.badge}
        whyText={course.whyText}
        isCompleted={isCompleted}
        delay={index * 100}
        aRate={course.aRate}
      />
    </div>
  );
}

// Credit warning helper
function getCreditWarning(credits: number, semester: string): { color: string; warning: string | null } {
  const isSummer = semester.toLowerCase().includes("summer");
  const max = isSummer ? 9 : 18;
  const min = 12;

  if (credits > max) {
    return { color: "text-red-400", warning: "Exceeds max credits" };
  }
  if (credits > 15 && !isSummer) {
    return { color: "text-yellow-400", warning: "Heavy load" };
  }
  if (credits > 0 && credits < min && !isSummer) {
    return { color: "text-yellow-400", warning: "Below 12 hrs" };
  }
  return { color: "text-green-400", warning: null };
}

// Droppable Column Component
function DndColumn({ id, title, credits, courses, isCompleted, isInProgress }: ColumnProps) {
  const borderColor = isInProgress ? "border-amber-500/30" : isCompleted ? "border-green-500/20" : "border-violet/10";
  const creditStatus = getCreditWarning(credits, title);

  return (
    <div className={`flex flex-col bg-[#141428]/40 border ${borderColor} rounded-xl p-6 min-h-[400px] min-w-[300px] flex-shrink-0`}>
      <div className="mb-6 flex justify-between items-end">
        <div>
          <h2
            className={`font-[var(--font-heading)] font-black text-xl tracking-[-0.02em] ${
              isInProgress ? "text-amber-400" : isCompleted ? "text-green-400" : "text-foreground"
            }`}
            style={{ fontFamily: "'Figtree', sans-serif" }}
          >
            {isInProgress && "🟡 "}{title}
          </h2>
          <div className="flex items-center gap-2 mt-1">
            <span className={`text-sm ${creditStatus.color}`}>{credits} credits</span>
            {creditStatus.warning && (
              <span className="text-xs text-red-400/70">⚠ {creditStatus.warning}</span>
            )}
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-4 flex-1">
        <SortableContext id={id} items={courses.map((c) => c.id)} strategy={verticalListSortingStrategy}>
          {courses.map((course, index) => (
            <SortableCourseCard
              key={course.id}
              course={course}
              isCompleted={!!isCompleted}
              index={index}
            />
          ))}
        </SortableContext>
        {courses.length === 0 && (
          <div className="flex-1 flex items-center justify-center border-2 border-dashed border-violet/10 rounded-lg opacity-50">
            <span className="text-sm text-muted-foreground">Drop courses here</span>
          </div>
        )}
      </div>
    </div>
  );
}

interface DndBoardProps {
  columns: Record<string, ColumnProps>;
  setColumns: React.Dispatch<React.SetStateAction<Record<string, ColumnProps>>>;
}

export function DndBoard({ columns, setColumns }: DndBoardProps) {
  const [activeCourse, setActiveCourse] = useState<Course | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 5,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragStart = (event: any) => {
    const { active } = event;
    const course = active.data.current;
    if (course) {
      setActiveCourse(course as Course);
    }
  };

  const findColumnOfCourse = (courseId: string) => {
    return Object.keys(columns).find((key) =>
      columns[key].courses.some((c) => c.id === courseId)
    );
  };

  const handleDragOver = (event: any) => {
    const { active, over } = event;
    if (!over) return;

    const activeId = active.id;
    const overId = over.id;

    if (activeId === overId) return;

    const activeColumnId = findColumnOfCourse(activeId);
    const overColumnId =
      Object.keys(columns).find((key) => key === overId) ||
      findColumnOfCourse(overId);

    if (!activeColumnId || !overColumnId || activeColumnId === overColumnId) {
      return;
    }

    setColumns((prev) => {
      const activeItems = prev[activeColumnId].courses;
      const overItems = prev[overColumnId].courses;

      const activeIndex = activeItems.findIndex((c) => c.id === activeId);
      const overIndex = overItems.findIndex((c) => c.id === overId);

      let newIndex;
      if (overId in prev) {
         // Dropping directly onto an empty column
         newIndex = overItems.length + 1;
      } else {
         const isBelowOverItem =
           over &&
           active.rect.current.translated &&
           active.rect.current.translated.top > over.rect.top + over.rect.height;
  
         const modifier = isBelowOverItem ? 1 : 0;
         newIndex = overIndex >= 0 ? overIndex + modifier : overItems.length + 1;
      }

      return {
        ...prev,
        [activeColumnId]: {
          ...prev[activeColumnId],
          courses: activeItems.filter((c) => c.id !== activeId),
          credits: prev[activeColumnId].credits - (activeItems[activeIndex]?.credits ?? 3),
        },
        [overColumnId]: {
          ...prev[overColumnId],
          courses: [
            ...overItems.slice(0, newIndex),
            activeItems[activeIndex],
            ...overItems.slice(newIndex, overItems.length),
          ],
          credits: prev[overColumnId].credits + (activeItems[activeIndex]?.credits ?? 3),
        },
      };
    });
  };

  const handleDragEnd = (event: any) => {
    const { active, over } = event;
    setActiveCourse(null);
    if (!over) return;

    const activeId = active.id;
    const overId = over.id;

    const activeColumnId = findColumnOfCourse(activeId);
    const overColumnId = findColumnOfCourse(overId) || (Object.keys(columns).includes(overId) ? overId : null);

    if (activeColumnId && overColumnId && activeColumnId === overColumnId) {
      const items = columns[activeColumnId].courses;
      const activeIndex = items.findIndex((c) => c.id === activeId);
      const overIndex = items.findIndex((c) => c.id === overId);

      if (activeIndex !== overIndex) {
        setColumns((prev) => ({
          ...prev,
          [activeColumnId]: {
            ...prev[activeColumnId],
            courses: arrayMove(items, activeIndex, overIndex),
          },
        }));
      }
    }
  };

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
    >
      <div className="flex flex-nowrap overflow-x-auto gap-8 pb-32 -mx-2 px-2" style={{ scrollbarWidth: 'thin' }}>
        {Object.keys(columns).map((colId) => (
          <DndColumn
            key={colId}
            id={colId}
            title={columns[colId].title}
            credits={columns[colId].credits}
            courses={columns[colId].courses}
            isCompleted={columns[colId].isCompleted}
            isInProgress={columns[colId].isInProgress}
          />
        ))}
      </div>

      <DragOverlay dropAnimation={{ sideEffects: defaultDropAnimationSideEffects({ styles: { active: { opacity: "0.4" } } }) }}>
        {activeCourse ? (
          <div className="cursor-grabbing">
            <CourseCard
              code={activeCourse.code}
              title={activeCourse.title}
              professor={activeCourse.professor}
              badge={activeCourse.badge}
              whyText={activeCourse.whyText}
              aRate={activeCourse.aRate}
            />
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}
