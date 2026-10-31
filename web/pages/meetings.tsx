/**
 * Meetings list page (PRD §11.1 screen 1).
 */
import { useEffect, useState } from 'react';
import Link from 'next/link';

interface Meeting {
  id: string;
  title: string;
  started_at: string;
  timezone: string;
  source: string;
  status: string;
}

export default function MeetingsPage() {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const r = await fetch('/api/meetings');
        const data = await r.json();
        setMeetings(Array.isArray(data) ? data : []);
      } catch (e) {
        setMeetings([]);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'committed':
        return 'bg-emerald-950/80 text-emerald-300 border border-emerald-500/40 shadow-xs';
      case 'extracted':
        return 'bg-purple-950/80 text-purple-300 border border-purple-500/40 shadow-xs';
      case 'in_review':
        return 'bg-blue-950/80 text-blue-300 border border-blue-500/40 shadow-xs';
      default:
        return 'bg-slate-800 text-slate-300 border border-slate-700';
    }
  };

  const getSourceIcon = (source: string) => {
    if (source.includes('voice')) return '🎙️';
    if (source.includes('paste')) return '📝';
    return '📁';
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-gradient-to-r from-indigo-900/60 via-purple-900/60 to-pink-900/60 border border-indigo-500/30 rounded-3xl p-6 text-white shadow-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4 backdrop-blur-md">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xl">📁</span>
            <h1 className="text-2xl font-black">Meeting Ledger &amp; Queues</h1>
          </div>
          <p className="text-purple-200/80 text-xs sm:text-sm">
            All meetings ingested into the Followthrough decision pipeline.
          </p>
        </div>
        <div className="flex gap-2">
          <Link href="/paste" className="btn btn-secondary text-xs font-bold px-3.5 py-2">
            + Paste Transcript
          </Link>
          <Link href="/record" className="btn btn-primary text-xs font-bold px-4 py-2">
            🎙️ Record Voice
          </Link>
        </div>
      </div>

      {loading && (
        <div className="text-center py-16 space-y-3">
          <span className="text-3xl animate-spin inline-block">⏳</span>
          <p className="text-slate-400 text-sm font-medium">Loading meeting ledgers...</p>
        </div>
      )}

      {!loading && meetings.length === 0 && (
        <div className="bg-slate-900/60 rounded-3xl border-2 border-dashed border-slate-800 p-12 text-center space-y-4 backdrop-blur-md">
          <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 flex items-center justify-center text-3xl mx-auto shadow-inner">
            📋
          </div>
          <h3 className="text-lg font-bold text-white">No Meetings Ingested Yet</h3>
          <p className="text-slate-400 text-sm max-w-md mx-auto">
            Record a voice recap with WhisperFlow or paste an existing meeting transcript to seed the decision ledger.
          </p>
          <div className="flex justify-center gap-3 pt-2">
            <Link href="/paste" className="btn btn-primary text-xs px-5 py-2.5">
              Paste Sample Transcript
            </Link>
            <Link href="/record" className="btn btn-secondary text-xs px-5 py-2.5">
              Record Speech
            </Link>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4">
        {[...meetings].reverse().map((m) => (
          <div
            key={m.id}
            className="p-5 bg-slate-900/70 border border-slate-800/80 hover:border-indigo-500/50 rounded-2xl shadow-lg hover:shadow-xl transition-all flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 group backdrop-blur-md"
          >
            <div className="space-y-1.5 flex-1">
              <div className="flex items-center gap-2.5 flex-wrap">
                <span className="text-lg">{getSourceIcon(m.source)}</span>
                <h3 className="font-bold text-white text-base group-hover:text-indigo-400 transition-colors">
                  {m.title}
                </h3>
                <span className={`text-[11px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full ${getStatusBadge(m.status)}`}>
                  {m.status}
                </span>
              </div>
              <p className="text-xs text-slate-400 flex items-center gap-3 flex-wrap">
                <span>🕒 {new Date(m.started_at).toLocaleString()}</span>
                <span>•</span>
                <span>Source: <strong className="text-slate-300">{m.source}</strong></span>
                <span>•</span>
                <span className="font-mono text-slate-500 text-[11px]">ID: {m.id.slice(0, 8)}...</span>
              </p>
            </div>

            <Link
              href={`/meetings/${m.id}`}
              className="btn btn-primary text-xs font-bold px-4 py-2 self-stretch sm:self-auto shadow-sm"
            >
              Open Review Queue →
            </Link>
          </div>
        ))}
      </div>
    </div>
  );
}
