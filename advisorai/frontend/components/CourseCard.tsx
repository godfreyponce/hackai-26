interface CourseCardProps {
  code: string;
  name: string;
  credits: number;
  description?: string;
}

export function CourseCard({ code, name, credits, description }: CourseCardProps) {
  return (
    <div className="p-4 border rounded-lg shadow-sm">
      <h3 className="font-bold">{code}</h3>
      <p className="text-lg">{name}</p>
      <p className="text-sm text-gray-500">{credits} credits</p>
      {description && <p className="mt-2 text-sm">{description}</p>}
    </div>
  );
}
