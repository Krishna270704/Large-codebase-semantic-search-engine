import { useState, useEffect, useRef } from "react";
import { ingest, getIngestStatus } from "../services/api";
import toast from "react-hot-toast";

/**
 * RepoIngestion – form to ingest a local directory into the vector store.
 */
export default function RepoIngestion() {
  const [source, setSource] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [isOpen, setIsOpen] = useState(false);
  
  // Progress state
  const [progress, setProgress] = useState({
    status: "idle", // idle, running, completed, error
    percentage: 0,
    files_processed: 0,
    total_files: 0,
  });
  
  const pollInterval = useRef(null);

  const startPolling = () => {
    if (pollInterval.current) clearInterval(pollInterval.current);
    
    pollInterval.current = setInterval(async () => {
      try {
        const stat = await getIngestStatus();
        setProgress({
          status: stat.status,
          percentage: stat.percentage,
          files_processed: stat.files_processed,
          total_files: stat.total_files
        });
        
        if (stat.status === "completed") {
          clearInterval(pollInterval.current);
          setLoading(false);
          toast.success("Ingestion completed successfully!");
          setResult({
            status: "success",
            message: "Ingestion completed successfully.",
            files_processed: stat.files_processed
          });
        } else if (stat.status === "error" || stat.status === "failed") {
          clearInterval(pollInterval.current);
          setLoading(false);
          toast.error("Ingestion failed.");
          setError("An error occurred during ingestion. Please check the backend logs.");
        }
      } catch (err) {
        console.error("Polling error:", err);
      }
    }, 2000);
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (pollInterval.current) clearInterval(pollInterval.current);
    };
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!source.trim()) return;

    setLoading(true);
    setResult(null);
    setError(null);
    setProgress({ status: "running", percentage: 0, files_processed: 0, total_files: 0 });

    try {
      const val = source.trim();
      const payload = { reset: true };
      if (val.startsWith("http://") || val.startsWith("https://") || val.startsWith("git@") || val.startsWith("github.com/")) {
        payload.github_url = val;
      } else {
        payload.directory = val;
      }
      
      toast.loading("Starting ingestion...", { id: "ingest" });
      const data = await ingest(payload);
      toast.success("Ingestion queued!", { id: "ingest" });
      // Wait a moment and then start polling
      startPolling();
    } catch (err) {
      toast.error("Failed to start ingestion.", { id: "ingest" });
      const msg = err.response?.data?.detail || err.message || "Ingestion failed";
      setError(msg);
      setLoading(false);
      setProgress(p => ({ ...p, status: "error" }));
    }
  };

  return (
    <div className="glass-card overflow-hidden">
      {/* Toggle header */}
      <button
        onClick={() => setIsOpen((p) => !p)}
        className="flex w-full items-center justify-between px-5 py-4 text-left transition-colors hover:bg-white/[0.02]"
      >
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10">
            <svg className="h-4 w-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
            </svg>
          </div>
          <div>
            <p className="text-sm font-semibold text-white/80">Ingest Repository</p>
            <p className="text-xs text-white/30">Index local files into the vector store</p>
          </div>
        </div>
        <svg className={`h-4 w-4 text-white/30 transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Form body */}
      {isOpen && (
        <div className="border-t border-white/[0.04] px-5 py-5 animate-fade-in">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="repo-path" className="mb-1.5 block text-xs font-medium text-white/50">
                Directory Path or GitHub URL
              </label>
              <input
                id="repo-path"
                type="text"
                value={source}
                onChange={(e) => setSource(e.target.value)}
                placeholder="https://github.com/tiangolo/fastapi  or  ./data"
                className="input-ring w-full"
              />
            </div>

            <button type="submit" disabled={loading || !source.trim()} className="btn-primary w-full">
              {loading ? (
                <>
                  <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                  </svg>
                  Ingesting…
                </>
              ) : (
                "Ingest Repository"
              )}
            </button>
          </form>

          {/* Progress Bar & Status */}
          {progress.status === "running" && (
            <div className="mt-4 animate-fade-in">
              <div className="flex items-center justify-between text-xs text-white/50 mb-1">
                <span>Processing... {progress.files_processed} / {progress.total_files || "?"} files</span>
                <span>{progress.percentage}%</span>
              </div>
              <div className="h-1.5 w-full bg-white/[0.05] rounded-full overflow-hidden">
                <div 
                  className="h-full bg-emerald-500 transition-all duration-500 ease-out"
                  style={{ width: `${progress.percentage}%` }}
                />
              </div>
            </div>
          )}

          {/* Success */}
          {result && progress.status === "completed" && (
            <div className="mt-4 rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-3 animate-slide-up">
              <p className="text-sm font-medium text-emerald-300">
                ✓ {result.status === "warning" ? "Warning" : "Success"}
              </p>
              <p className="mt-1 text-xs text-emerald-200/60">{result.message}</p>
              {result.files_processed > 0 && (
                <div className="mt-2 flex gap-4 text-xs text-emerald-300/50">
                  <span>{result.files_processed} files ingested</span>
                </div>
              )}
            </div>
          )}

          {/* Error */}
          {error && progress.status !== "running" && (
            <div className="mt-4 rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-3 animate-slide-up">
              <p className="text-sm font-medium text-red-300">✕ Error</p>
              <p className="mt-1 text-xs text-red-200/60">{error}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
