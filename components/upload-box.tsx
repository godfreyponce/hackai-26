"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { Upload, FileText, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface UploadBoxProps {
  onFileUploaded: (uploaded: boolean) => void;
}

export function UploadBox({ onFileUploaded }: UploadBoxProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const simulateUpload = useCallback((selectedFile: File) => {
    setFile(selectedFile);
    setIsUploading(true);
    setUploadProgress(0);
    
    const interval = setInterval(() => {
      setUploadProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          setIsUploading(false);
          setIsComplete(true);
          return 100;
        }
        return prev + Math.random() * 15 + 5;
      });
    }, 150);
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
        simulateUpload(droppedFile);
      }
    },
    [simulateUpload]
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
      simulateUpload(selectedFile);
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
          isUploading && "cursor-wait"
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
          {!file && !isUploading && !isComplete && (
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
                      ? "Upload complete"
                      : `Uploading... ${Math.min(Math.round(uploadProgress), 100)}%`}
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
