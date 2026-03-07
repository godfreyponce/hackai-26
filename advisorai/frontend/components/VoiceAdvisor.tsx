"use client";

import { useState } from "react";

export function VoiceAdvisor() {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");

  const toggleListening = () => {
    setIsListening(!isListening);
    // TODO: Implement voice recognition
  };

  return (
    <div className="p-6 border rounded-lg">
      <button
        onClick={toggleListening}
        className={`px-6 py-3 rounded-full ${
          isListening ? "bg-red-500" : "bg-blue-500"
        } text-white`}
      >
        {isListening ? "Stop" : "Start"} Listening
      </button>
      {transcript && (
        <p className="mt-4 p-3 bg-gray-100 rounded">{transcript}</p>
      )}
    </div>
  );
}
