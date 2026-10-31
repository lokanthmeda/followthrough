import Link from 'next/link';

export default function Home() {
  const features = [
    {
      title: 'WhisperFlow Voice Capture',
      desc: 'Seamlessly transcribe meeting recordings & speech recaps while automatically stripping filler words and resolving self-corrections in real-time.',
      icon: '🎙️',
      color: 'from-pink-500 to-rose-500',
      border: 'border-pink-500/30 hover:border-pink-500/60',
      bg: 'bg-gradient-to-br from-pink-950/20 via-slate-900/60 to-slate-900/90',
      badge: 'Channel B & A',
    },
    {
      title: 'Cross-Meeting Memory',
      desc: 'Remembers every firm commitment and decision made in previous meetings. Never lose context or let commitments fade away across sprints.',
      icon: '🧠',
      color: 'from-indigo-500 to-purple-600',
      border: 'border-indigo-500/30 hover:border-indigo-500/60',
      bg: 'bg-gradient-to-br from-indigo-950/20 via-slate-900/60 to-slate-900/90',
      badge: 'Core Differentiator',
    },
    {
      title: 'Decision Conflict Engine',
      desc: 'Catches silent reversals and direct contradictions against past decisions with side-by-side evidence quotes and 1-click supersede workflows.',
      icon: '⚡',
      color: 'from-amber-500 to-orange-500',
      border: 'border-amber-500/30 hover:border-amber-500/60',
      bg: 'bg-gradient-to-br from-amber-950/20 via-slate-900/60 to-slate-900/90',
      badge: 'C1 & C2 Detection',
    },
    {
      title: 'Strict Confirmation Gate',
      desc: 'Zero autonomous task spam. Nothing is posted to Linear or committed to memory without explicit human approval and immutable audit logging.',
      icon: '🛡️',
      color: 'from-emerald-500 to-teal-600',
      border: 'border-emerald-500/30 hover:border-emerald-500/60',
      bg: 'bg-gradient-to-br from-emerald-950/20 via-slate-900/60 to-slate-900/90',
      badge: 'Hard Invariant',
    },
  ];

  return (
    <div className="space-y-12">
      {/* Hero Section */}
      <section className="text-center py-10 px-4 relative">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/30 mb-6 shadow-sm">
          <span className="w-2 h-2 rounded-full bg-pink-500 animate-ping" />
          <span className="text-xs font-bold uppercase tracking-wider bg-gradient-to-r from-indigo-400 via-purple-300 to-pink-400 bg-clip-text text-transparent">
            Agentic AI Meeting-to-Execution
          </span>
        </div>

        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tight text-white mb-6">
          Turns Spoken Meetings Into{' '}
          <span className="bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400 bg-clip-text text-transparent drop-shadow-sm">
            Tracked Execution
          </span>
        </h1>

        <p className="text-base sm:text-lg text-slate-400 max-w-2xl mx-auto mb-8 leading-relaxed font-normal">
          A transcript summarizer forgets. <strong className="text-purple-300 font-semibold">Followthrough remembers</strong>.
          It detects contradictions with previous decisions, grounds every item in verbatim quotes, and posts to your tracker only when approved.
        </p>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center justify-center gap-4">
          <Link href="/record" className="btn btn-primary text-sm px-6 py-3 hover:scale-105 transition-transform">
            <span>🎙️ Record Voice Recap</span>
          </Link>
          <Link href="/paste" className="btn btn-secondary text-sm px-6 py-3 hover:scale-105 transition-transform">
            <span>📝 Paste Transcript</span>
          </Link>
          <Link href="/meetings" className="btn bg-slate-900/80 border border-slate-700 text-slate-300 hover:bg-slate-800 text-sm px-6 py-3">
            <span>📁 View Meetings</span>
          </Link>
        </div>
      </section>

      {/* Feature Cards Grid */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {features.map((f) => (
          <div
            key={f.title}
            className={`p-6 rounded-2xl border ${f.border} ${f.bg} backdrop-blur-md shadow-lg hover:shadow-xl transition-all relative overflow-hidden group`}
          >
            <div className="flex items-start justify-between mb-4">
              <div className="w-12 h-12 rounded-xl bg-slate-800/80 border border-slate-700/80 shadow-md flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">
                {f.icon}
              </div>
              <span className={`text-[11px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full text-white bg-gradient-to-r ${f.color} shadow-xs`}>
                {f.badge}
              </span>
            </div>
            <h3 className="text-xl font-bold text-white mb-2">{f.title}</h3>
            <p className="text-sm text-slate-400 leading-relaxed">{f.desc}</p>
          </div>
        ))}
      </section>

      {/* Quick Interactive Seed Banner */}
      <section className="p-8 rounded-3xl bg-gradient-to-r from-indigo-950 via-purple-950 to-slate-900 border border-purple-800/40 text-white shadow-2xl flex flex-col md:flex-row items-center justify-between gap-6 relative overflow-hidden">
        <div className="space-y-1.5 text-center md:text-left z-10">
          <div className="inline-block px-3 py-1 rounded-full bg-purple-500/20 text-purple-300 text-xs font-semibold border border-purple-500/30 mb-2">
            ⚡ Quick Demo Flow
          </div>
          <h3 className="text-2xl font-black">Ready to see conflict detection in action?</h3>
          <p className="text-sm text-purple-200/80 max-w-xl">
            Test how Followthrough catches contradictions when "Pricing is usage-based" changes to "Pricing is hybrid".
          </p>
        </div>
        <div className="z-10">
          <Link href="/paste" className="btn btn-primary font-bold px-6 py-3 shadow-lg hover:scale-105 transition-transform">
            Try Demo Scenario →
          </Link>
        </div>
      </section>
    </div>
  );
}
