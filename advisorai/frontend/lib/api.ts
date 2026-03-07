const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function uploadTranscript(file: File) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/api/transcript`, {
    method: "POST",
    body: formData,
  });

  return response.json();
}

export async function getRecommendations(studentId: string) {
  const response = await fetch(`${API_BASE}/api/recommend/${studentId}`);
  return response.json();
}

export async function getCourses(query?: string) {
  const url = query
    ? `${API_BASE}/api/courses?q=${encodeURIComponent(query)}`
    : `${API_BASE}/api/courses`;
  const response = await fetch(url);
  return response.json();
}

export async function sendVoiceQuery(audioBlob: Blob) {
  const formData = new FormData();
  formData.append("audio", audioBlob);

  const response = await fetch(`${API_BASE}/api/voice/query`, {
    method: "POST",
    body: formData,
  });

  return response.json();
}
