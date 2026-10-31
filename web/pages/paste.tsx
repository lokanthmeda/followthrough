/**
 * Direct Transcript Paste & Ingest Page (PRD §5.4 Channel D).
 */
import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';

export default function PastePage() {
  const router = useRouter();
  const [title, setTitle] = useState('Nimbus Launch Sync');
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [createdId, setCreatedId] = useState('');

  const demoScenarios = [
    {
      name: 'Meeting 1 — Product Planning (Your Team)',
      title: 'Meeting 1 — Product Planning Meeting',
      badge: 'Step 1: Ingest Baseline & Decisions',
      color: 'border-blue-500/30 bg-blue-950/20 text-blue-200',
      text: `Lokanath: Good morning everyone. Let's start with the product planning discussion for the Followthrough project. Our goal for this sprint is to launch the first working version by November 15th.
Priya: I think the first priority should be the transcript ingestion and decision extraction module. Without that, the rest of the workflow won't work.
Lokanath: Agreed. Let's make transcript ingestion the first priority. Priya, you own the transcript ingestion module. Please complete it by November 5th.
Priya: Sure, I'll take ownership of that.
Lokanath: Rahul, can you handle the task tracker integration?
Rahul: Yes. I'll integrate the task tracker and make sure tasks can be created automatically after confirmation. I'll complete it by November 7th.
Lokanath: Good. Anita, please work on the weekly digest functionality. I want every team member to receive a summary of their open tasks every Friday.
Anita: Okay. I'll complete the weekly digest by November 10th.
Lokanath: One more important decision: nothing should be automatically posted to the task tracker without a human confirmation. Even if the AI extracts an action item correctly, the user must confirm it before creating the task.
Priya: Understood.
Lokanath: And let's use the existing PostgreSQL database for storing meeting memory and decisions.
Rahul: Okay, I'll use PostgreSQL for that.`,
    },
    {
      name: 'Meeting 2 — Follow-up Meeting (Conflict & Deadline Demo)',
      title: 'Meeting 2 — Follow-up Meeting',
      badge: 'Step 2: Trigger Architecture Conflict & Deadline Extension',
      color: 'border-rose-500/30 bg-rose-950/20 text-rose-200',
      text: `Lokanath: Let's continue from our previous meeting. First, regarding transcript ingestion, Priya, what's the status?
Priya: The module is almost ready. I need another two days.
Lokanath: Okay. Next, regarding the task tracker integration, Rahul?
Rahul: The integration is ready. However, I think we should simplify the architecture. Instead of PostgreSQL, I suggest we remove PostgreSQL and store all meeting decisions directly inside the task tracker.
Lokanath: Wait. In our previous meeting, we decided that PostgreSQL would be the storage layer for meeting memory and decisions. So this is a change from our earlier decision. Let's flag this as a decision conflict rather than silently replacing the previous decision.
Rahul: Yes, that's intentional. I think we should change the decision.
Lokanath: Okay. Create a proposed decision change: Previous decision: PostgreSQL stores meeting memory and decisions. New proposal: store meeting decisions inside the task tracker. This change should require confirmation before becoming the new team decision.
Rahul: Agreed.
Lokanath: Now let's discuss deadlines. Priya's original deadline was November 5th. Priya, you said you need two more days. Are you requesting an extension?
Priya: Yes. I need to move the deadline from November 5th to November 7th.
Lokanath: Okay. Record that as a proposed deadline change requiring confirmation.
Anita: I also have an update. The weekly digest is ready earlier than expected.
Lokanath: Great. Mark the weekly digest as completed.
Anita: Done.`,
    },
    {
      name: 'M1 Pricing Baseline (PRD Spec)',
      title: 'M1 - Product Kickoff (Pricing)',
      badge: 'Pricing Baseline',
      color: 'border-indigo-500/30 bg-indigo-950/20 text-indigo-200',
      text: `Arjun: Pricing for v1 is strictly usage-based. We will not support tiered flat fees.\nMeera: Agreed. Ravi, please prepare the usage billing spec by Friday.\nRavi: Understood, I will handle the spec by Friday.`,
    },
    {
      name: 'M3 Pricing Contradiction (PRD Spec)',
      title: 'M3 - Pricing Alignment Sync',
      badge: 'Pricing Contradiction',
      color: 'border-amber-500/30 bg-amber-950/20 text-amber-200',
      text: `Meera: Team, our enterprise clients requested predictability. We decided pricing is hybrid — base fee plus usage, not pure usage-based.\nRavi: Got it. I will finalize the hybrid pricing copy by Monday.\nPriya: I will review with legal by end of the month.`,
    },
  ];

  const handleImport = async (overrideTitle?: string, overrideText?: string) => {
    const importTitle = overrideTitle || title;
    const importText = overrideText || text;

    if (!importText.trim()) {
      setError('Please provide transcript text.');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const res = await fetch('/api/meetings/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: importTitle, text: importText }),
      });
      let data: any = {};
      try {
        data = await res.json();
      } catch {
        throw new Error(`Server returned HTTP ${res.status}`);
      }
      if (!res.ok) throw new Error(data.detail || data.error || `Import failed (HTTP ${res.status})`);

      const meetingId = data.meeting_id;
      setCreatedId(meetingId);

      // Trigger automatic extraction
      const extractRes = await fetch(`/api/meetings/${meetingId}/extract`, { method: 'POST' });
      let extractData: any = {};
      try {
        extractData = await extractRes.json();
      } catch {
        // ignore parse error if redirection is needed
      }
      if (!extractRes.ok) {
        throw new Error(extractData.detail || extractData.error || `Extraction failed (HTTP ${extractRes.status})`);
      }

      router.push(`/meetings/${meetingId}`);
    } catch (e: any) {
      setError(e.message || 'Import failed');
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-indigo-900/60 via-blue-900/60 to-teal-900/60 border border-indigo-500/30 rounded-3xl p-6 text-white shadow-xl backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-500/20 border border-indigo-400/30 flex items-center justify-center text-xl shadow-inner">
            📝
          </div>
          <div>
            <h1 className="text-2xl font-black">Import Meeting Transcript</h1>
            <p className="text-indigo-200/80 text-xs sm:text-sm">
              Paste speaker-attributed transcripts, VTT cues, or select a pre-built demo scenario.
            </p>
          </div>
        </div>
      </div>

      {/* Preset Demo Scenarios */}
      <div className="space-y-3">
        <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
          <span>⚡</span>
          <span>1-Click Seed Scenarios (Hackathon Demo Script)</span>
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {demoScenarios.map((s) => (
            <div
              key={s.name}
              className={`p-5 rounded-2xl border ${s.color} backdrop-blur-md flex flex-col justify-between gap-3 shadow-lg hover:border-slate-600 transition-all`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="font-bold text-sm text-white">{s.name}</span>
                  <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-slate-800 border border-slate-700 text-slate-300">
                    {s.badge}
                  </span>
                </div>
                <p className="text-xs italic line-clamp-2 text-slate-400 font-mono">
                  "{s.text.split('\n')[0]}"
                </p>
              </div>
              <button
                onClick={() => {
                  setTitle(s.title);
                  setText(s.text);
                }}
                className="btn btn-secondary text-xs py-1.5 font-bold self-start"
              >
                Load Into Editor ↓
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Custom Form */}
      <div className="bg-slate-900/70 rounded-3xl border border-slate-800/80 shadow-xl p-6 sm:p-8 space-y-5 backdrop-blur-xl">
        <div>
          <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
            Meeting Title
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full px-4 py-3 rounded-2xl border border-slate-800 bg-slate-950/70 text-slate-100 placeholder-slate-600 focus:bg-slate-950 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-sm font-medium outline-none transition-all"
            placeholder="e.g. Sprint 42 Planning & Sync"
          />
        </div>

        <div>
          <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
            Raw Transcript (With Speaker Labels or Timestamps)
          </label>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={8}
            className="w-full p-4 rounded-2xl border border-slate-800 bg-slate-950/70 text-slate-100 placeholder-slate-600 focus:bg-slate-950 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-sm font-mono outline-none transition-all resize-y"
            placeholder="Arjun: We will price strictly usage-based.&#10;Meera: Agreed. Ravi will update docs by Friday."
          />
        </div>

        {error && (
          <div className="p-4 bg-rose-950/40 border border-rose-500/40 rounded-2xl text-rose-300 text-sm flex items-center gap-2">
            <span>⚠️</span>
            <span>{error}</span>
          </div>
        )}

        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pt-2">
          <span className="text-xs text-slate-400">
            Auto-normalizes utterances, extracts commitments, and runs conflict detection.
          </span>
          <button
            onClick={() => handleImport()}
            disabled={loading}
            className="btn btn-primary px-6 py-2.5 font-bold shadow-lg text-sm self-stretch sm:self-auto"
          >
            {loading ? 'Processing Pipeline…' : 'Ingest & Review Queue →'}
          </button>
        </div>
      </div>
    </div>
  );
}
