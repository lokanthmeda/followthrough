// Frontend client for WhisperFlow transcription (PRD §5 & §6.1)
export interface TranscriptionResult {
  text: string;
  segments?: Array<{ text: string; start?: number; end?: number }>;
  language?: string;
}

/**
 * Accepts a recorded audio Blob and returns the transcription.
 *
 * Flow:
 *  1. Browser MediaRecorder captures the user's voice.
 *  2. The audio blob is sent to Next.js API route /api/wispr/transcribe.
 *  3. That route proxies to the local LLM proxy's
 *     /v1/audio/transcriptions endpoint (OpenAI-compatible).
 *  4. The JSON result is returned here.
 */
export async function transcribeAudio(audioBlob: Blob): Promise<TranscriptionResult> {
  const formData = new FormData();
  formData.append('audio', audioBlob, 'recording.wav');

  const response = await fetch('/api/wispr/transcribe', {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.error || `Transcription failed (${response.status})`);
  }

  return (await response.json()) as TranscriptionResult;
}

export async function importTranscript(title: string, text: string, startedAt?: string) {
  const response = await fetch('/api/meetings/import', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, text, started_at: startedAt }),
  });
  if (!response.ok) throw new Error('Failed to import');
  return response.json();
}

export async function runExtraction(meetingId: string) {
  const response = await fetch(`/api/meetings/${meetingId}/extract`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error('Failed to extract');
  return response.json();
}