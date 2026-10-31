/**
 * Review queue — approve items/decisions, resolve conflicts, confirm & post.
 */
import { useRouter } from 'next/router';
import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';

interface ReviewPayload {
  meeting: { id: string; title: string; started_at: string; status: string };
  decisions: Array<{
    id: string; statement: string; topic: string; decided_by?: string;
    evidence: any[]; status: string;
  }>;
  action_items: Array<{
    id: string; title: string; owner?: string; due_date?: string;
    flags: string[]; evidence: any[]; status: string; external_url?: string;
  }>;
  conflicts: Array<{
    id: string; type: string; relation: string; rationale: string;
    new_quote: string; prior_quote: string; severity: string; resolution?: string;
  }>;
}

export default function ReviewPage() {
  const router = useRouter();
  const { id } = router.query;
  const [data, setData] = useState<ReviewPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [preview, setPreview] = useState<any>(null);
  const [voiceCommand, setVoiceCommand] = useState('');
  const [proposedOps, setProposedOps] = useState<any[]>([]);

  const load = useCallback(async () => {
    if (!id || typeof id !== 'string') return;
    setLoading(true);
    setError('');
    try {
      const r = await fetch(`/api/meetings/${id}/review`);
      const json = await r.json();
      if (!r.ok) throw new Error(json.detail || json.error || 'Failed to load review');
      setData(json);
    } catch (e: any) {
      setError(e.message || 'Failed to load');
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  const run = async (label: string, fn: () => Promise<void>) => {
    setBusy(label);
    setError('');
    setMessage('');
    try {
      await fn();
    } catch (e: any) {
      setError(e.message || 'Action failed');
    } finally {
      setBusy('');
    }
  };

  const extract = () => run('extract', async () => {
    const r = await fetch(`/api/meetings/${id}/extract`, { method: 'POST' });
    const json = await r.json();
    if (!r.ok) throw new Error(json.detail || json.error || 'Extraction failed');
    setMessage('Extraction complete — review the decisions and action items below.');
    await load();
  });

  const patchItem = (itemId: string, body: object) => run('item', async () => {
    const r = await fetch(`/api/review/items/${itemId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const json = await r.json();
    if (!r.ok) throw new Error(json.detail || json.error || 'Item update failed');
    await load();
  });

  const patchDecision = (decisionId: string, body: object) => run('decision', async () => {
    const r = await fetch(`/api/review/decisions/${decisionId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const json = await r.json();
    if (!r.ok) throw new Error(json.detail || json.error || 'Decision update failed');
    await load();
  });

  const resolveConflict = (conflictId: string, resolution: string) => run('conflict', async () => {
    const r = await fetch(`/api/review/conflicts/${conflictId}/resolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resolution }),
    });
    const json = await r.json();
    if (!r.ok) throw new Error(json.detail || json.error || 'Resolve failed');
    setMessage(`Conflict resolved: ${resolution}`);
    await load();
  });

  const bulkApprove = () => run('approve', async () => {
    const r = await fetch('/api/review/bulk-approve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ meeting_id: id }),
    });
    const json = await r.json();
    if (!r.ok) throw new Error(json.detail || json.error || 'Bulk approve failed');
    setMessage(`Approved ${json.approved_items} items and ${json.approved_decisions} decisions.`);
    await load();
  });

  const showPreview = () => run('preview', async () => {
    const r = await fetch(`/api/meetings/${id}/post-preview`, { method: 'POST' });
    const json = await r.json();
    if (!r.ok) throw new Error(json.detail || json.error || 'Preview failed');
    setPreview(json);
    setMessage(`Post preview: ${json.count} approved item(s) ready.`);
  });

  const confirmAndPost = () => run('post', async () => {
    const r = await fetch(`/api/meetings/${id}/confirm`, { method: 'POST' });
    const json = await r.json();
    if (!r.ok) throw new Error(json.detail || json.error || 'Confirm & post failed');
    setMessage(
      `🎉 Successfully posted ${json.posted?.length || 0} task(s) to tracker and activated decisions in memory ledger!`
    );
    setPreview(null);
    await load();
  });

  const handleVoiceCommand = async () => {
    if (!voiceCommand.trim()) return;
    try {
      const res = await fetch('http://127.0.0.1:8000/review/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ meeting_id: id, dictation: voiceCommand }),
      });
      const data = await res.json();
      if (data.proposed_ops) {
        setProposedOps(data.proposed_ops);
        setMessage(`Proposed ${data.proposed_ops.length} operation(s) from dictation.`);
      }
    } catch (e: any) {
      setError('Command parsing failed: ' + e.message);
    }
  };

  if (!id) return null;
  if (loading && !data) {
    return (
      <div className="max-w-4xl mx-auto py-16 text-center space-y-4">
        <span className="text-4xl animate-bounce inline-block">⏳</span>
        <h2 className="text-xl font-bold text-white">Loading Review Queue...</h2>
        <p className="text-sm text-slate-400">Querying decisions, commitments, and conflict status.</p>
      </div>
    );
  }
  if (!data) return <div className="p-6 text-rose-400 font-bold">{error || 'No data found'}</div>;

  const openConflicts = data.conflicts.filter((c) => !c.resolution && c.severity === 'blocking');
  const canApprove = openConflicts.length === 0;
  const approvedCount = data.action_items.filter((a) => a.status === 'approved').length;
  const needsExtract = data.meeting.status === 'ingested' ||
    (data.decisions.length === 0 && data.action_items.length === 0);

  return (
    <div className="space-y-8 pb-16">
      {/* Top Banner Card */}
      <div className="bg-gradient-to-r from-indigo-950 via-purple-950 to-slate-900 border border-purple-500/30 rounded-3xl p-6 sm:p-8 text-white shadow-2xl flex flex-col md:flex-row md:items-center justify-between gap-4 backdrop-blur-md">
        <div>
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <span className="text-xs uppercase font-extrabold px-3 py-1 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
              Review &amp; Confirmation Gate
            </span>
            <span className={`text-xs font-bold uppercase tracking-wider px-3 py-1 rounded-full ${
              data.meeting.status === 'committed'
                ? 'bg-emerald-950 text-emerald-300 border border-emerald-500/40'
                : 'bg-amber-950 text-amber-300 border border-amber-500/40'
            }`}>
              {data.meeting.status}
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-white">{data.meeting.title}</h1>
          <p className="text-slate-400 text-xs sm:text-sm mt-1">
            Started: {new Date(data.meeting.started_at).toLocaleString()} · ID: {data.meeting.id.slice(0, 8)}...
            {busy ? ` · ⏳ ${busy}…` : ''}
          </p>
        </div>

        {needsExtract && (
          <button
            onClick={extract}
            disabled={!!busy}
            className="btn btn-primary text-sm font-bold px-6 py-3 shadow-lg hover:scale-105 transition-transform"
          >
            ⚡ Run Extraction Pipeline
          </button>
        )}
      </div>

      {/* Notifications */}
      {error && (
        <div className="p-4 bg-rose-950/40 border border-rose-500/40 rounded-2xl text-rose-300 text-sm flex items-center gap-3 shadow-lg">
          <span className="text-xl">⚠️</span>
          <span className="font-medium">{error}</span>
        </div>
      )}
      {message && (
        <div className="p-4 bg-emerald-950/40 border border-emerald-500/40 rounded-2xl text-emerald-300 text-sm flex items-center gap-3 shadow-lg">
          <span className="text-xl">✅</span>
          <span className="font-medium">{message}</span>
        </div>
      )}

      {/* Channel C: Voice Command Bar */}
      <div className="p-5 bg-slate-900/80 rounded-2xl border border-slate-800 text-white shadow-xl space-y-3 backdrop-blur-md">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wider text-purple-300 flex items-center gap-1.5">
            <span>🎙️</span>
            <span>Channel C: Dictated Queue Voice Commands</span>
          </span>
          <span className="text-[11px] text-slate-400">e.g. "Set owner of item 2 to Ravi and due Friday"</span>
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={voiceCommand}
            onChange={(e) => setVoiceCommand(e.target.value)}
            placeholder="Type or dictate review command here..."
            className="flex-1 px-4 py-2.5 text-sm rounded-xl bg-slate-950/80 border border-slate-800 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-purple-400 focus:ring-1 focus:ring-purple-400 font-mono"
          />
          <button
            onClick={handleVoiceCommand}
            className="btn btn-primary text-xs font-bold px-5 py-2.5"
          >
            Parse Ops
          </button>
        </div>
        {proposedOps.length > 0 && (
          <div className="flex flex-wrap gap-2 pt-1">
            {proposedOps.map((op, idx) => (
              <span key={idx} className="px-3 py-1 rounded-lg bg-purple-950/60 border border-purple-500/40 text-xs text-purple-200 font-mono">
                {op.op} → {op.target} ({op.value})
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Section 1: Conflicts */}
      {data.conflicts.length > 0 && (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-black text-rose-400 flex items-center gap-2">
              <span>🚨</span>
              <span>Decision Conflicts Detected ({data.conflicts.length})</span>
            </h2>
            {openConflicts.length > 0 && (
              <span className="px-3 py-1 rounded-full text-xs font-bold bg-rose-600 text-white shadow-lg shadow-rose-500/30">
                {openConflicts.length} Blocking Conflict(s)
              </span>
            )}
          </div>

          <div className="space-y-4">
            {data.conflicts.map((c) => (
              <div key={c.id} className="conflict-card">
                <div className="flex items-center justify-between mb-3 text-xs font-bold">
                  <span className="px-3 py-1 rounded-full bg-rose-950 text-rose-300 border border-rose-800 uppercase tracking-wider">
                    {c.relation} · {c.severity}
                  </span>
                  {c.resolution ? (
                    <span className="px-3 py-1 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-800 font-bold">
                      ✓ Resolved: {c.resolution}
                    </span>
                  ) : (
                    <span className="text-rose-400 animate-pulse font-semibold">
                      Requires resolution before approval
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-3">
                  <div className="p-4 bg-slate-950/60 rounded-xl border border-slate-800">
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">
                      Prior Decision in Ledger
                    </span>
                    <p className="text-sm italic font-mono text-slate-300">
                      &quot;{c.prior_quote}&quot;
                    </p>
                  </div>
                  <div className="p-4 bg-slate-950/60 rounded-xl border border-rose-900/50">
                    <span className="text-xs font-bold text-rose-400 uppercase tracking-wider block mb-1">
                      New Spoken Decision
                    </span>
                    <p className="text-sm italic font-mono text-rose-200 font-medium">
                      &quot;{c.new_quote}&quot;
                    </p>
                  </div>
                </div>

                <p className="text-sm text-slate-300 bg-slate-950/40 p-3.5 rounded-xl border border-slate-800/80 mb-3 leading-relaxed">
                  <strong className="text-rose-300">Analysis:</strong> {c.rationale}
                </p>

                {!c.resolution && (
                  <div className="flex flex-wrap items-center gap-2 pt-1">
                    <button
                      disabled={!!busy}
                      onClick={() => resolveConflict(c.id, 'supersede')}
                      className="btn btn-primary text-xs font-bold shadow-md"
                    >
                      Supersede (New Replaces Old)
                    </button>
                    <button
                      disabled={!!busy}
                      onClick={() => resolveConflict(c.id, 'keep_old')}
                      className="btn btn-secondary text-xs font-bold"
                    >
                      Keep Old (Reject New)
                    </button>
                    <button
                      disabled={!!busy}
                      onClick={() => resolveConflict(c.id, 'keep_both')}
                      className="btn btn-secondary text-xs font-bold"
                    >
                      Keep Both (Co-exist)
                    </button>
                    <button
                      disabled={!!busy}
                      onClick={() => resolveConflict(c.id, 'defer')}
                      className="btn btn-secondary text-xs font-bold"
                    >
                      Discuss Later
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Section 2: Decisions */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-black text-indigo-300 flex items-center gap-2">
            <span>⚖️</span>
            <span>Extracted Decisions ({data.decisions.length})</span>
          </h2>
          <span className="text-xs text-indigo-400 font-semibold">Commits to memory ledger on post</span>
        </div>

        {data.decisions.length === 0 && (
          <p className="text-sm text-slate-500 italic p-5 bg-slate-900/50 rounded-2xl border border-slate-800">No decisions extracted yet.</p>
        )}

        <div className="space-y-3">
          {data.decisions.map((d) => (
            <div
              key={d.id}
              className="p-5 bg-slate-900/70 rounded-2xl border-l-4 border-indigo-500 border border-slate-800 shadow-md hover:border-slate-700 transition-all backdrop-blur-md"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1">
                  <div className="font-bold text-white text-base">{d.statement}</div>
                  <div className="text-xs text-indigo-400 font-medium">
                    Topic: <span className="font-bold text-slate-200">{d.topic || 'General'}</span> {d.decided_by && `· Decided by: ${d.decided_by}`}
                  </div>
                </div>
                <span className={`text-xs px-3 py-1 rounded-full font-bold uppercase tracking-wider ${
                  d.status === 'active' || d.status === 'approved'
                    ? 'bg-emerald-950 text-emerald-300 border border-emerald-500/40'
                    : 'bg-indigo-950 text-indigo-300 border border-indigo-500/40'
                }`}>
                  {d.status}
                </span>
              </div>

              {d.evidence?.[0]?.quote && (
                <div className="evidence">
                  <span className="text-amber-300 font-semibold block text-[10px] uppercase">Verbatim Evidence:</span>
                  &quot;{d.evidence[0].quote}&quot;
                </div>
              )}

              {d.status === 'needs_review' && (
                <div className="flex gap-2 mt-4 pt-3 border-t border-slate-800">
                  <button
                    disabled={!!busy || !canApprove}
                    onClick={() => patchDecision(d.id, { action: 'approve' })}
                    className="btn btn-success text-xs font-bold py-1.5"
                  >
                    ✓ Approve
                  </button>
                  <button
                    disabled={!!busy}
                    onClick={() => patchDecision(d.id, { action: 'reject' })}
                    className="btn btn-danger text-xs font-bold py-1.5"
                  >
                    ✕ Reject
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Section 3: Action Items */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-black text-teal-300 flex items-center gap-2">
            <span>🎯</span>
            <span>Tracked Action Items ({data.action_items.length})</span>
          </h2>
          <span className="text-xs text-teal-400 font-semibold">Creates tasks in Linear on post</span>
        </div>

        {data.action_items.length === 0 && (
          <p className="text-sm text-slate-500 italic p-5 bg-slate-900/50 rounded-2xl border border-slate-800">No action items extracted.</p>
        )}

        <div className="space-y-3">
          {data.action_items.map((a) => (
            <div
              key={a.id}
              className="p-5 bg-slate-900/70 rounded-2xl border-l-4 border-teal-500 border border-slate-800 shadow-md hover:border-slate-700 transition-all backdrop-blur-md"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1">
                  <div className="font-bold text-white text-base">{a.title}</div>
                  <div className="text-xs text-slate-400 flex items-center gap-2 flex-wrap">
                    <span className="font-semibold text-teal-300">
                      👤 Owner: {a.owner || 'Needs Owner'}
                    </span>
                    <span>•</span>
                    <span className="font-semibold text-purple-300">
                      📅 Due: {a.due_date || 'Needs Deadline'}
                    </span>
                    {(a.flags || []).map((f) => (
                      <span key={f} className="flag-badge">
                        {f}
                      </span>
                    ))}
                  </div>
                </div>
                <span className={`text-xs px-3 py-1 rounded-full font-bold uppercase tracking-wider ${
                  a.status === 'posted'
                    ? 'bg-purple-950 text-purple-300 border border-purple-500/40'
                    : a.status === 'approved'
                    ? 'bg-emerald-950 text-emerald-300 border border-emerald-500/40'
                    : 'bg-teal-950 text-teal-300 border border-teal-500/40'
                }`}>
                  {a.status}
                </span>
              </div>

              {a.evidence?.[0]?.quote && (
                <div className="evidence">
                  <span className="text-amber-300 font-semibold block text-[10px] uppercase">Verbatim Evidence:</span>
                  &quot;{a.evidence[0].quote}&quot;
                </div>
              )}

              {a.external_url && (
                <div className="mt-2">
                  <a
                    href={a.external_url}
                    className="inline-flex items-center gap-1 text-xs font-bold text-indigo-400 hover:text-indigo-300 underline"
                    target="_blank"
                    rel="noreferrer"
                  >
                    <span>View Task in Linear Tracker →</span>
                  </a>
                </div>
              )}

              {a.status === 'needs_review' && (
                <div className="flex gap-2 mt-4 pt-3 border-t border-slate-800">
                  <button
                    disabled={!!busy || !canApprove}
                    onClick={() => patchItem(a.id, { action: 'approve' })}
                    className="btn btn-success text-xs font-bold py-1.5"
                  >
                    ✓ Approve Task
                  </button>
                  <button
                    disabled={!!busy}
                    onClick={() => patchItem(a.id, { action: 'reject' })}
                    className="btn btn-danger text-xs font-bold py-1.5"
                  >
                    ✕ Reject
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Post Preview Card */}
      {preview && (
        <div className="p-6 border border-indigo-500/40 rounded-2xl bg-indigo-950/40 shadow-xl space-y-3 backdrop-blur-md">
          <h3 className="font-bold text-indigo-200 text-base flex items-center gap-2">
            <span>📋</span>
            <span>Linear Tracker Submission Preview ({preview.count} Items)</span>
          </h3>
          <ul className="text-xs space-y-2 pl-4 list-disc text-slate-300">
            {(preview.items || []).map((i: any) => (
              <li key={i.id} className="font-mono">
                <strong className="text-white">{i.title}</strong> {i.due_date ? `(Due: ${i.due_date})` : ''}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Confirmation Bottom Action Bar */}
      <div className="sticky bottom-4 z-40 p-4 bg-slate-900/90 backdrop-blur-xl border border-slate-800 rounded-2xl shadow-2xl flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            disabled={!!busy || !canApprove || needsExtract}
            onClick={bulkApprove}
            className="btn btn-secondary text-xs font-bold px-4 py-2"
          >
            ✓ Bulk Approve All
          </button>
          <button
            disabled={!!busy || approvedCount === 0}
            onClick={showPreview}
            className="btn btn-secondary text-xs font-bold px-4 py-2"
          >
            👁️ Preview ({approvedCount})
          </button>
        </div>

        <button
          disabled={!!busy || !canApprove || (approvedCount === 0 && data.meeting.status !== 'extracted')}
          onClick={confirmAndPost}
          className="btn btn-primary text-sm font-extrabold px-6 py-2.5 shadow-lg shadow-indigo-500/30 hover:scale-105 transition-transform"
        >
          🚀 Confirm &amp; Post to Tracker
        </button>
      </div>

      {!canApprove && (
        <p className="text-center text-sm font-bold text-rose-300 bg-rose-950/50 p-4 rounded-2xl border border-rose-500/40 shadow-lg">
          🔒 Confirmation Gate Locked: You must resolve all blocking conflicts above before approving or posting.
        </p>
      )}
    </div>
  );
}
