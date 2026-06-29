import ResultCard from "./ResultCard";

/**
 * ResultsList – renders search hits or status messages.
 */
export default function ResultsList({ results, loading, error, searched, query, totalIndexed }) {
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 animate-fade-in">
        <div className="relative">
          <div className="h-12 w-12 rounded-full border-2 border-brand-500/20" />
          <div className="absolute inset-0 h-12 w-12 animate-spin rounded-full border-2 border-transparent border-t-brand-400" />
        </div>
        <p className="mt-4 text-sm text-white/40">Searching through {totalIndexed ?? "…"} indexed chunks…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-card mx-auto max-w-lg animate-fade-in border-red-500/20 px-6 py-8 text-center">
        <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-red-500/10">
          <svg className="h-6 w-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
          </svg>
        </div>
        <p className="text-sm font-medium text-red-300">{error}</p>
        <p className="mt-1 text-xs text-white/30">Make sure the backend is running and the index is populated.</p>
      </div>
    );
  }

  if (searched && results.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 animate-fade-in">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-white/[0.03]">
          <svg className="h-8 w-8 text-white/20" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m5.231 13.481L15 17.25m-4.5-15H5.625c-.621 0-1.125.504-1.125 1.125v16.5c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9zm3.75 11.625a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
          </svg>
        </div>
        <p className="text-sm font-medium text-white/50">No results found</p>
        <p className="mt-1 text-xs text-white/25">Try a different query or ingest more files.</p>
      </div>
    );
  }

  if (!searched) {
    return (
      <div className="flex flex-col items-center justify-center py-16 animate-fade-in">
        <div className="mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-3xl bg-gradient-to-br from-brand-600/10 to-brand-400/5">
          <svg className="h-10 w-10 text-brand-400/40" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" />
          </svg>
        </div>
        <p className="text-sm text-white/30">Enter a natural language query to search your codebase</p>
      </div>
    );
  }

  return (
    <div className="animate-fade-in space-y-3">
      <div className="flex items-center justify-between px-1 text-xs text-white/35">
        <span>
          <span className="font-semibold text-white/60">{results.length}</span> result{results.length !== 1 ? "s" : ""} for <span className="font-medium text-brand-400/70">"{query}"</span>
        </span>
        <span>{totalIndexed} chunks indexed</span>
      </div>
      {results.map((r, i) => (
        <ResultCard key={`${r.file_path}-${r.start_line}-${i}`} result={r} rank={i + 1} />
      ))}
    </div>
  );
}
