/**
 * WhisperFlow Voice Input Page (PRD §5.2 Channel B: Dictated voice recap).
 */
import { useState, useRef } from 'react';
import Link from 'next/link';
import { transcribeAudio, importTranscript } from '@/lib/whisperClient';

export default function RecordPage() {
  const [recording, setRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [importing, setImporting] = useState(false);
  const [meetingId, setMeetingId] = useState('');
  const [error, setError] = useState('');
  const [audioDuration, setAudioDuration] = useState(0);
  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<BlobPart[]>([]);
  const timerRef = useRef<any>(null);

  const sampleScript = "Meera: We will deploy the v2 backend on Monday. Ravi: I will finalize the API documentation by Friday.";

  const start = async () => {
    setError('');
    setAudioDuration(0);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder.current = new MediaRecorder(stream);
      chunks.current = [];
      mediaRecorder.current.ondataavailable = (e) => chunks.current.push(e.data);
      mediaRecorder.current.onstop = async () => {
        clearInterval(timerRef.current);
        const blob = new Blob(chunks.current, { type: 'audio/wav' });
        chunks.current = [];
        try {
          const result = await transcribeAudio(blob);
          setTranscript(result.text || '(empty transcription)');
        } catch (e: any) {
          setError(e.message || 'Transcription failed');
        }
      };
      mediaRecorder.current.start();
      setRecording(true);
      timerRef.current = setInterval(() => {
        setAudioDuration((prev) => prev + 1);
      }, 1000);
    } catch (e: any) {
      setError(`Microphone access denied: ${e.message}`);
    }
  };

  const stop = () => {
    mediaRecorder.current?.stop();
    setRecording(false);
    clearInterval(timerRef.current);
  };

  const handleImport = async () => {
    if (!transcript.trim()) return;
    setImporting(true);
    setError('');
    try {
      const result = await importTranscript('Voice Recap - Nimbus Launch', transcript);
      setMeetingId(result.meeting_id);
      // Automatically trigger LLM pipeline extraction
      await fetch(`/api/meetings/${result.meeting_id}/extract`, { method: 'POST' });
    } catch (e: any) {
      setError(e.message || 'Import failed');
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-purple-900/60 via-indigo-900/60 to-pink-900/60 border border-purple-500/30 rounded-3xl p-6 text-white shadow-xl backdrop-blur-md">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-xl bg-purple-500/20 border border-purple-400/30 flex items-center justify-center text-xl shadow-inner">
            🎙️
          </div>
          <div>
            <h1 className="text-2xl font-black">Wispr Flow Voice Ingestion</h1>
            <p className="text-purple-200/80 text-xs sm:text-sm">
              Speak naturally. Conversational fillers ("um", "uh") and mid-sentence corrections are resolved automatically.
            </p>
          </div>
        </div>
      </div>

      {/* Suggested Demo Prompt Card */}
      <div className="bg-amber-950/30 border border-amber-500/40 rounded-2xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-sm backdrop-blur-md">
        <div>
          <span className="font-bold text-amber-300 block text-xs uppercase tracking-wider mb-1">
            💡 Recommended Demo Dictation:
          </span>
          <span className="text-amber-200/90 italic font-mono text-xs">"{sampleScript}"</span>
        </div>
        <button
          onClick={() => setTranscript(sampleScript)}
          className="text-xs bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 border border-amber-500/40 font-semibold px-3 py-1.5 rounded-xl transition-all whitespace-nowrap active:scale-95"
        >
          Use as Transcript
        </button>
      </div>

      {/* Recorder Panel */}
      <div className="bg-slate-900/70 rounded-3xl border border-slate-800/80 shadow-xl p-6 sm:p-8 space-y-6 backdrop-blur-xl">
        <div className="flex flex-col items-center justify-center py-6 text-center space-y-4">
          {recording ? (
            <div className="flex flex-col items-center space-y-3">
              <div className="relative">
                <div className="w-24 h-24 rounded-full bg-rose-500/30 animate-ping absolute inset-0" />
                <div className="w-24 h-24 rounded-full bg-gradient-to-tr from-rose-600 to-pink-600 flex items-center justify-center text-white text-4xl shadow-xl shadow-rose-500/40 relative z-10">
                  🎙️
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-rose-500 animate-pulse" />
                <span className="font-bold text-rose-400 text-sm">Recording in progress ({audioDuration}s)...</span>
              </div>
              <p className="text-xs text-slate-400">Speak clearly. Mid-sentence corrections like "Friday — actually Monday" are fine.</p>
              <button onClick={stop} className="btn btn-danger text-sm px-6 py-2.5 shadow-lg">
                ⏹ Stop & Transcribe
              </button>
            </div>
          ) : (
            <div className="flex flex-col items-center space-y-3">
              <div className="w-24 h-24 rounded-full bg-gradient-to-tr from-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center text-white text-4xl shadow-xl shadow-indigo-500/30 border border-white/10">
                🎙️
              </div>
              <p className="text-sm text-slate-400 font-medium max-w-sm">
                Click below to start recording with your microphone. Audio is processed via the local Whisper proxy.
              </p>
              <button onClick={start} className="btn btn-primary text-sm px-6 py-2.5 shadow-lg">
                🎙 Start Recording
              </button>
            </div>
          )}
        </div>

        {error && (
          <div className="p-4 bg-rose-950/40 border border-rose-500/40 rounded-2xl text-rose-300 text-sm flex items-center gap-2">
            <span>⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {/* Live Transcription Result */}
        <div className="space-y-3 pt-4 border-t border-slate-800">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-slate-200 text-sm flex items-center gap-2">
              <span>📄</span>
              <span>Transcription Output</span>
            </h3>
            {transcript && (
              <span className="text-xs text-purple-300 font-mono bg-purple-950/60 px-2 py-0.5 rounded-full border border-purple-800/40">
                {transcript.split(' ').length} words
              </span>
            )}
          </div>

          <textarea
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            placeholder="Your transcribed speech will appear here. You can also edit or paste directly..."
            className="w-full h-32 p-4 text-sm rounded-2xl border border-slate-800 bg-slate-950/70 text-slate-100 placeholder-slate-600 focus:bg-slate-950 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none transition-all resize-y font-mono"
          />

          {transcript && (
            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={handleImport}
                disabled={importing}
                className="btn btn-success px-6 py-2.5 font-bold shadow-lg text-sm"
              >
                {importing ? (
                  <>
                    <span className="animate-spin text-sm">⏳</span>
                    <span>Extracting Decisions...</span>
                  </>
                ) : (
                  <>
                    <span>🚀 Ingest & Extract with LLM →</span>
                  </>
                )}
              </button>
            </div>
          )}
        </div>

        {/* Success Card */}
        {meetingId && (
          <div className="p-5 bg-gradient-to-r from-emerald-950/40 via-slate-900 to-indigo-950/40 border border-emerald-500/40 rounded-2xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-xl">
            <div className="flex items-center gap-3">
              <span className="text-2xl">✅</span>
              <div>
                <span className="font-bold text-emerald-300 block text-sm">Meeting Ingested & Extracted!</span>
                <span className="text-xs text-slate-400 font-mono">ID: {meetingId}</span>
              </div>
            </div>
            <Link
              href={`/meetings/${meetingId}`}
              className="btn btn-primary text-xs px-5 py-2.5 shadow-md hover:scale-105 transition-transform"
            >
              Open Review Queue →
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
