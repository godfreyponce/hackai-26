"use client";

interface StepProgressProps {
  currentStep: number;
  totalSteps: number;
}

export function StepProgress({ currentStep, totalSteps }: StepProgressProps) {
  const progress = (currentStep / totalSteps) * 100;

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-2 px-1">
        <span className="text-sm text-muted-foreground font-sans">
          Step {currentStep} of {totalSteps}
        </span>
        <span className="text-sm text-muted-foreground font-sans">
          {Math.round(progress)}%
        </span>
      </div>
      <div className="w-full h-2 bg-card rounded-full overflow-hidden border border-purple/20">
        <div
          className="h-full bg-gradient-to-r from-purple to-violet rounded-full transition-all duration-500 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}
