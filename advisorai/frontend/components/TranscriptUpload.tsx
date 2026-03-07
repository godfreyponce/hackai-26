"use client";

import { useState } from "react";

export function TranscriptUpload() {
  const [file, setFile] = useState<File | null>(null);

  const handleUpload = async () => {
    if (!file) return;
    // TODO: Implement upload logic
  };

  return (
    <div className="p-4 border rounded-lg">
      <input
        type="file"
        accept=".pdf,.txt"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
      />
      <button
        onClick={handleUpload}
        className="mt-2 px-4 py-2 bg-blue-500 text-white rounded"
      >
        Upload Transcript
      </button>
    </div>
  );
}
