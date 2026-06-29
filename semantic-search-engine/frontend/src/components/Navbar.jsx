import { useState } from "react";

/**
 * Navbar – top bar with project branding and a dark-mode toggle.
 */
export default function Navbar() {
  const [backendUp, setBackendUp] = useState(null); // null = unknown

  return (
    <header className="sticky top-0 z-50 border-b border-white/[0.06] bg-surface-900/80 backdrop-blur-lg">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        {/* Logo / Title */}
        <div className="flex items-center gap-3">
          {/* Animated lens icon */}
          <div className="relative flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 shadow-lg shadow-brand-600/30">
            <svg
              className="h-5 w-5 text-white"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"
              />
            </svg>
            <span className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-surface-900 bg-emerald-400" />
          </div>

          <div>
            <h1 className="text-lg font-bold tracking-tight">
              Code<span className="text-brand-400">Lens</span>
            </h1>
            <p className="text-[10px] font-medium uppercase tracking-widest text-white/30">
              Semantic Search
            </p>
          </div>
        </div>

        {/* Right side – links / status */}
        <nav className="flex items-center gap-4">
          <a
            href={`${import.meta.env.VITE_API_URL || "http://localhost:8000"}/docs`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs font-medium text-white/40 transition hover:text-white/80"
          >
            API Docs ↗
          </a>

          <div className="h-4 w-px bg-white/10" />

          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="text-white/40 transition hover:text-white/80"
          >
            <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
              <path
                fillRule="evenodd"
                d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
                clipRule="evenodd"
              />
            </svg>
          </a>
        </nav>
      </div>
    </header>
  );
}
