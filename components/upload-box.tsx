"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { Upload, FileText, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface UploadBoxProps {
  onFileUploaded: (uploaded: boolean) => void;
}

export function UploadBox({ onFileUploaded }: UploadBoxProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const uploadToBackend = useCallback(async (selectedFile: File) => {
    setFile(selectedFile);
    setIsUploading(true);
    setUploadProgress(0);
    setError(null);

    // Start progress animation
    const progressInterval = setInterval(() => {
      setUploadProgress((prev) => {
        if (prev >= 85) {
          clearInterval(progressInterval);
          return 85; // Hold at 85% until backend responds
        }
        return prev + Math.random() * 10 + 3;
      });
    }, 150);

    try {
      // POST to backend /api/transcript
      const formData = new FormData();
      formData.append("file", selectedFile);

      const res = await fetch(`${API_BASE}/api/transcript/`, {
        method: "POST",
        body: formData,
      });

      clearInterval(progressInterval);

      if (!res.ok) {
        const errData = await res.json().catch(() => ({ detail: "Upload failed" }));
        throw new Error(errData.detail || `Server error: ${res.status}`);
      }

      const transcriptData = await res.json();

      // Store in sessionStorage for the plan page to use
      sessionStorage.setItem("transcriptData", JSON.stringify(transcriptData));

      // Complete!
      setUploadProgress(100);
      setIsUploading(false);
      setIsComplete(true);
    } catch (err: any) {
      clearInterval(progressInterval);
      setIsUploading(false);
      setUploadProgress(0);
      setFile(null);
      setError(err.message || "Failed to upload transcript");
      console.error("Upload error:", err);
    }
  }, []);

  useEffect(() => {
    if (isComplete) {
      onFileUploaded(true);
    }
  }, [isComplete, onFileUploaded]);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile && droppedFile.type === "application/pdf") {
        uploadToBackend(droppedFile);
      }
    },
    [uploadToBackend]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleClick = () => {
    inputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile && selectedFile.type === "application/pdf") {
      uploadToBackend(selectedFile);
    }
  };

  return (
    <div className="w-full max-w-xl mx-auto">
      <div
        onClick={!isUploading && !isComplete ? handleClick : undefined}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={cn(
          "relative rounded-2xl border-2 border-dashed border-[#7B2FBE] p-10 transition-all duration-300 cursor-pointer group",
          "bg-[#141428]/80 backdrop-blur-md",
          isDragOver && "border-teal/50 bg-teal/5 scale-[1.02]",
          !isDragOver && !isComplete && "hover:bg-[#1a1a3a]/80 hover:shadow-[0_0_40px_rgba(123,47,190,0.15)]",
          isComplete && "border-teal/30 bg-teal/5 cursor-default",
          isUploading && "cursor-wait",
          error && "border-red-500/50"
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          onChange={handleFileChange}
          className="hidden"
        />

        <div className="flex flex-col items-center gap-4 text-center">
          {!file && !isUploading && !isComplete && !error && (
            <>
              <div className="relative">
                <Upload className="w-12 h-12 text-muted-foreground group-hover:text-violet transition-colors" />
                <div className="absolute inset-0 blur-xl bg-purple/30 opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
              <div>
                <p className="text-foreground font-medium mb-1">
                  Drop your UTD transcript PDF here
                </p>
                <p className="text-muted-foreground text-sm">
                  or click to browse
                </p>
              </div>
            </>
          )}

          {error && (
            <div className="text-center">
              <p className="text-red-400 font-medium mb-1">Upload failed</p>
              <p className="text-red-300/70 text-sm mb-3">{error}</p>
              <button
                onClick={(e) => { e.stopPropagation(); setError(null); }}
                className="text-sm text-violet hover:text-violet/80 underline"
              >
                Try again
              </button>
            </div>
          )}

          {(isUploading || isComplete) && file && (
            <>
              <div className="flex items-center gap-3 text-left w-full">
                {isComplete ? (
                  <CheckCircle2 className="w-10 h-10 text-teal flex-shrink-0" />
                ) : (
                  <FileText className="w-10 h-10 text-violet flex-shrink-0" />
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-foreground font-medium truncate">
                    {file.name}
                  </p>
                  <p className="text-muted-foreground text-sm">
                    {isComplete
                      ? "Transcript parsed successfully ✓"
                      : `Analyzing transcript... ${Math.min(Math.round(uploadProgress), 100)}%`}
                  </p>
                </div>
              </div>

              {/* Progress Bar */}
              <div className="w-full h-2 bg-background rounded-full overflow-hidden">
                <div
                  className={cn(
                    "h-full rounded-full transition-all duration-300",
                    isComplete
                      ? "bg-teal"
                      : "bg-gradient-to-r from-purple to-teal"
                  )}
                  style={{ width: `${Math.min(uploadProgress, 100)}%` }}
                />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
