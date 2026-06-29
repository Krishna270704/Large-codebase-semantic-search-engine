import { useState, useEffect, useRef, useCallback } from "react";

/**
 * SearchBar – Google-style centred search input with debounce.
 *
 * @param {object}  props
 * @param {function} props.onSearch   Called with the query string after debounce.
 * @param {boolean}  props.loading    Show a loading indicator inside the bar.
 */
export default function SearchBar({ onSearch, loading = false }) {
  const [query, setQuery] = useState("");
  const timerRef = useRef(null);

  // Debounced callback
  const debouncedSearch = useCallback(
    (value) => {
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => {
        if (value.trim()) onSearch(value.trim());
      }, 300);
    },
    [onSearch]
  );

  // Clean up on unmount
  useEffect(() => () => clearTimeout(timerRef.current), []);

  const handleChange = (e) => {
    const v = e.target.value;
    setQuery(v);
    debouncedSearch(v);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    clearTimeout(timerRef.current);
    if (query.trim()) onSearch(query.trim());
  };

  return (
    <form onSubmit={handleSubmit} className="relative mx-auto w-full max-w-2xl">
      {/* Glow ring effect */}
      <div className="absolute -inset-1 rounded-2xl bg-gradient-to-r from-brand-600/20 via-brand-400/10 to-brand-600/20 blur-lg transition-opacity duration-500 group-focus-within:opacity-100" />

      <div className="relative flex items-center">
        {/* Search icon */}
        <div className="pointer-events-none absolute left-4 text-white/30">
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
          </svg>
        </div>

        <input
          id="search-input"
          type="text"
          value={query}
          onChange={handleChange}
          placeholder="Search code with natural language…"
          autoComplete="off"
          className="w-full rounded-2xl border border-white/10 bg-white/[0.04] py-4 pl-12 pr-28
                     text-base text-white placeholder-white/30 shadow-xl shadow-black/20
                     backdrop-blur-xl
                     transition-all duration-300
                     focus:border-brand-500/50 focus:outline-none focus:ring-2 focus:ring-brand-500/20
                     hover:border-white/15"
        />

        {/* Right-side button */}
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="btn-primary absolute right-2 !rounded-xl !px-4 !py-2 text-xs"
        >
          {loading ? (
            <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
            </svg>
          ) : (
            "Search"
          )}
        </button>
      </div>

      {/* Keyboard hint */}
      <p className="mt-2 text-center text-xs text-white/20">
        Try: <span className="text-brand-400/60">"authentication logic"</span> or{" "}
        <span className="text-brand-400/60">"database connection"</span>
      </p>
    </form>
  );
}
