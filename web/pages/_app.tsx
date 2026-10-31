import '../styles/globals.css';
import type { AppProps } from 'next/app';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useState, useEffect } from 'react';

export default function App({ Component, pageProps }: AppProps) {
  const router = useRouter();
  const [isDark, setIsDark] = useState(true);

  useEffect(() => {
    // Default to dark theme as requested
    const saved = localStorage.getItem('followthrough-theme');
    if (saved) {
      setIsDark(saved === 'dark');
    } else {
      setIsDark(true);
      localStorage.setItem('followthrough-theme', 'dark');
    }
  }, []);

  const toggleTheme = () => {
    const next = !isDark;
    setIsDark(next);
    localStorage.setItem('followthrough-theme', next ? 'dark' : 'light');
  };

  const navItems = [
    { label: 'Home', href: '/', icon: '⚡' },
    { label: 'Record Voice', href: '/record', icon: '🎙️' },
    { label: 'Paste / Import', href: '/paste', icon: '📝' },
    { label: 'Meetings Queue', href: '/meetings', icon: '📁' },
  ];

  return (
    <div className={isDark ? 'dark' : ''}>
      <div className="min-h-screen bg-[#090d16] text-slate-100 flex flex-col font-sans transition-colors duration-300 relative overflow-x-hidden selection:bg-purple-500 selection:text-white">
        {/* Ambient Glows */}
        <div className="fixed top-0 left-1/4 w-96 h-96 bg-purple-600/10 rounded-full blur-3xl pointer-events-none -z-10" />
        <div className="fixed top-1/3 right-10 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none -z-10" />
        <div className="fixed bottom-10 left-10 w-96 h-96 bg-pink-600/10 rounded-full blur-3xl pointer-events-none -z-10" />

        {/* Top Colorful Accent Strip */}
        <div className="h-1 bg-gradient-to-r from-indigo-500 via-purple-500 via-pink-500 to-amber-400 w-full" />

        {/* Navigation Header */}
        <header className="bg-slate-900/70 backdrop-blur-xl sticky top-0 z-50 border-b border-slate-800/80 shadow-lg">
          <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2.5 group">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center text-white shadow-lg shadow-indigo-500/30 group-hover:scale-105 transition-transform">
                <span className="text-lg">🎯</span>
              </div>
              <div>
                <span className="text-xl font-black bg-gradient-to-r from-indigo-400 via-purple-300 to-pink-400 bg-clip-text text-transparent">
                  Followthrough
                </span>
                <span className="hidden sm:inline-block ml-2 px-2 py-0.5 text-[10px] uppercase font-bold tracking-wider rounded-full bg-gradient-to-r from-pink-500 to-rose-500 text-white shadow-xs">
                  Voice Agent
                </span>
              </div>
            </Link>

            <div className="flex items-center gap-2 sm:gap-3">
              <nav className="flex items-center gap-1 sm:gap-1.5">
                {navItems.map((item) => {
                  const isActive = router.pathname === item.href;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={`px-3 py-1.5 rounded-xl text-xs sm:text-sm font-semibold transition-all flex items-center gap-1.5 ${
                        isActive
                          ? 'bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 text-white shadow-md shadow-indigo-500/25'
                          : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'
                      }`}
                    >
                      <span>{item.icon}</span>
                      <span className="hidden sm:inline">{item.label}</span>
                    </Link>
                  );
                })}
              </nav>

              {/* Theme Toggle Button */}
              <button
                onClick={toggleTheme}
                title="Toggle Theme"
                className="w-8 h-8 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 flex items-center justify-center text-sm text-amber-300 transition-colors shadow-sm ml-1"
              >
                {isDark ? '🌙' : '☀️'}
              </button>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 py-8 px-4 max-w-5xl w-full mx-auto">
          <Component {...pageProps} />
        </main>

        {/* Footer */}
        <footer className="border-t border-slate-800/80 bg-slate-950/60 backdrop-blur-md py-4 text-center text-xs text-slate-500">
          <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between px-4 gap-2">
            <span className="flex items-center gap-1.5">
              <span>Engineered with</span>
              <span className="font-semibold text-purple-400">WhisperFlow</span>
              <span>+</span>
              <span className="font-semibold text-indigo-400">Decision Memory Ledger</span>
            </span>
            <span className="text-slate-500">Product Space Agentic AI Hackathon</span>
          </div>
        </footer>
      </div>
    </div>
  );
}
