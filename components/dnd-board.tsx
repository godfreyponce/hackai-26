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
  badge: "Core Requirement" | "Track Elective";
  whyText: string;
}

interface ColumnProps {
  id: string;
  title: string;
  credits: number;
  courses: Course[];
  isCompleted?: boolean;
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
      />
    </div>
  );
}

// Droppable Column Component
function DndColumn({ id, title, credits, courses, isCompleted }: ColumnProps) {
  return (
    <div className="flex flex-col bg-[#141428]/40 border border-violet/10 rounded-xl p-6 min-h-[400px]">
      <div className="mb-6 flex justify-between items-end">
        <div>
          <h2
            className="font-[var(--font-heading)] font-black text-xl tracking-[-0.02em] text-foreground"
            style={{ fontFamily: "'Figtree', sans-serif" }}
          >
            {title}
          </h2>
          <p className="text-muted-foreground text-sm mt-1">{credits} credits</p>
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
          credits: prev[activeColumnId].credits - 3, // Assuming 3 for demo
        },
        [overColumnId]: {
          ...prev[overColumnId],
          courses: [
            ...overItems.slice(0, newIndex),
            activeItems[activeIndex],
            ...overItems.slice(newIndex, overItems.length),
          ],
          credits: prev[overColumnId].credits + 3,
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
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 pb-32">
        {Object.keys(columns).map((colId) => (
          <DndColumn
            key={colId}
            id={colId}
            title={columns[colId].title}
            credits={columns[colId].credits}
            courses={columns[colId].courses}
            isCompleted={columns[colId].isCompleted}
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
            />
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}
