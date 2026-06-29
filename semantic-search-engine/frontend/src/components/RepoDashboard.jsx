import { useState, useEffect } from "react";
import { getRepoStats } from "../services/api";

export default function RepoDashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isOpen, setIsOpen] = useState(false);

  const fetchStats = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getRepoStats();
      setStats(data);
    } catch (err) {
      setError("No repository statistics found.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchStats();
    }
  }, [isOpen]);

  return (
    <div className="glass-card overflow-hidden mt-4">
      {/* Toggle header */}
      <button
        onClick={() => setIsOpen((p) => !p)}
        className="flex w-full items-center justify-between px-5 py-4 text-left transition-colors hover:bg-white/[0.02]"
      >
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500/10">
            <svg className="h-4 w-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
            </svg>
          </div>
          <div>
            <p className="text-sm font-semibold text-white/80">Repository Dashboard</p>
            <p className="text-xs text-white/30">View indexed codebase stats</p>
          </div>
        </div>
        <svg className={`h-4 w-4 text-white/30 transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Body */}
      {isOpen && (
        <div className="border-t border-white/[0.04] px-5 py-5 animate-fade-in bg-black/10">
          <button onClick={fetchStats} className="w-full mb-4 px-3 py-1.5 text-xs font-medium text-white/70 bg-white/5 hover:bg-white/10 rounded-md transition-colors flex items-center justify-center gap-2">
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
            Refresh Stats
          </button>

          {loading ? (
            <div className="flex justify-center py-6">
              <svg className="h-5 w-5 animate-spin text-brand-400" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
              </svg>
            </div>
          ) : error ? (
            <div className="text-center text-xs text-white/40 py-4">{error}</div>
          ) : stats ? (
            <div className="space-y-4">
              
              {/* Header Info */}
              <div className="flex flex-col gap-1">
                <h3 className="text-lg font-bold text-white/90 truncate" title={stats.repository_name}>{stats.repository_name}</h3>
                <a href={stats.github_url} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-400 hover:underline truncate">
                  {stats.github_url}
                </a>
                <p className="text-[10px] text-white/40 mt-1">Indexed: {new Date(stats.last_indexed).toLocaleString()}</p>
                <p className="text-[10px] text-white/40">Duration: {stats.index_duration}</p>
              </div>

              {/* Grid Stats */}
              <div className="grid grid-cols-2 gap-3 pt-3 border-t border-white/5">
                <div className="bg-white/5 p-3 rounded-lg border border-white/5 flex flex-col justify-between">
                  <div className="text-[10px] text-white/40 uppercase tracking-wider mb-1 flex items-center gap-1">
                    <svg className="w-3 h-3 text-brand-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                    Files
                  </div>
                  <div className="text-lg font-semibold text-white/90">{stats.file_count.toLocaleString()}</div>
                </div>
                <div className="bg-white/5 p-3 rounded-lg border border-white/5 flex flex-col justify-between">
                  <div className="text-[10px] text-white/40 uppercase tracking-wider mb-1 flex items-center gap-1">
                    <svg className="w-3 h-3 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>
                    Chunks
                  </div>
                  <div className="text-lg font-semibold text-white/90">{stats.chunk_count.toLocaleString()}</div>
                </div>
                <div className="bg-white/5 p-3 rounded-lg border border-white/5 flex flex-col justify-between">
                  <div className="text-[10px] text-white/40 uppercase tracking-wider mb-1 flex items-center gap-1">
                    <svg className="w-3 h-3 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" /></svg>
                    Folders
                  </div>
                  <div className="text-lg font-semibold text-white/90">{stats.folder_count.toLocaleString()}</div>
                </div>
                <div className="bg-white/5 p-3 rounded-lg border border-white/5 flex flex-col justify-between">
                  <div className="text-[10px] text-white/40 uppercase tracking-wider mb-1 flex items-center gap-1">
                    <svg className="w-3 h-3 text-pink-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" /></svg>
                    Languages
                  </div>
                  <div className="text-lg font-semibold text-white/90">{stats.languages.length}</div>
                </div>
              </div>

              {/* Largest Folders */}
              {stats.largest_folders && stats.largest_folders.length > 0 && (
                <div className="pt-3 border-t border-white/5">
                  <p className="text-[10px] text-white/40 uppercase tracking-wider mb-2">Largest Folders</p>
                  <div className="space-y-1">
                    {stats.largest_folders.map((folder, idx) => (
                      <div key={idx} className="flex justify-between items-center text-xs">
                        <span className="text-white/70 truncate mr-2" title={folder.name}>{folder.name || '/'}</span>
                        <span className="text-white/40 font-mono shrink-0">{folder.count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Languages */}
              {stats.languages && stats.languages.length > 0 && (
                <div className="pt-3 border-t border-white/5">
                  <p className="text-[10px] text-white/40 uppercase tracking-wider mb-2">Languages</p>
                  <div className="flex flex-wrap gap-2">
                    {stats.languages.map((lang, idx) => (
                      <span key={idx} className="px-2 py-1 text-[10px] bg-black/30 border border-white/10 rounded-md text-white/70 flex items-center gap-1">
                        {lang.name} <span className="text-white/30 font-mono">{lang.count}</span>
                      </span>
                    ))}
                  </div>
                </div>
              )}
              
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
