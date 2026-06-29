import React, { lazy, Suspense, useState, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

/* ── Code Block with copy ──────────────────────────────────── */
const CodeBlock = ({ language, children }) => {
  const [copied, setCopied] = useState(false);
  const code = String(children).replace(/\n$/, '');
  const lang = language || 'text';
  return (
    <div className="my-4 rounded-xl border border-white/8 overflow-hidden bg-[#0d1117] shadow-lg group">
      <div className="flex items-center justify-between px-4 py-2 bg-[#161b22] border-b border-white/5">
        <span className="text-[11px] text-white/40 font-mono uppercase tracking-wider">{lang}</span>
        <button onClick={() => { navigator.clipboard.writeText(code); setCopied(true); setTimeout(() => setCopied(false), 2000); }}
          className="text-[11px] text-white/40 hover:text-white/80 transition-colors flex items-center gap-1">
          {copied ? '✓ Copied' : 'Copy'}
        </button>
      </div>
      <SyntaxHighlighter language={lang} style={vscDarkPlus}
        customStyle={{ margin: 0, padding: '1rem', background: 'transparent', fontSize: '0.82rem' }}
        showLineNumbers>{code}</SyntaxHighlighter>
    </div>
  );
};

/* ── Markdown renderer ─────────────────────────────────────── */
const MarkdownContent = ({ content }) => {
  if (!content) return null;
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
      code({ node, inline, className, children, ...props }) {
        const match = /language-(\w+)/.exec(className || '');
        return !inline && match
          ? <CodeBlock language={match[1]}>{children}</CodeBlock>
          : <code className="px-1.5 py-0.5 rounded-md bg-white/8 text-brand-300 text-[13px] font-mono" {...props}>{children}</code>;
      },
      h1: ({ children }) => <h1 className="text-xl font-bold text-white mt-5 mb-3 first:mt-0">{children}</h1>,
      h2: ({ children }) => <h2 className="text-lg font-semibold text-white mt-4 mb-2 first:mt-0">{children}</h2>,
      h3: ({ children }) => <h3 className="text-base font-semibold text-white/90 mt-3 mb-2 first:mt-0">{children}</h3>,
      p: ({ children }) => <p className="mb-3 last:mb-0 leading-relaxed">{children}</p>,
      ul: ({ children }) => <ul className="mb-3 pl-5 list-disc space-y-1 marker:text-brand-400/60">{children}</ul>,
      ol: ({ children }) => <ol className="mb-3 pl-5 list-decimal space-y-1 marker:text-brand-400/60">{children}</ol>,
      li: ({ children }) => <li className="leading-relaxed">{children}</li>,
      strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
      em: ({ children }) => <em className="italic text-white/80">{children}</em>,
      blockquote: ({ children }) => <blockquote className="border-l-3 border-brand-500/40 pl-4 my-3 text-white/60 italic">{children}</blockquote>,
      table: ({ children }) => <div className="overflow-x-auto my-4 rounded-lg border border-white/8"><table className="min-w-full text-sm">{children}</table></div>,
      thead: ({ children }) => <thead className="bg-white/5 text-white/70 text-left">{children}</thead>,
      th: ({ children }) => <th className="px-4 py-2 font-medium text-xs uppercase tracking-wider">{children}</th>,
      td: ({ children }) => <td className="px-4 py-2 border-t border-white/5 text-white/60">{children}</td>,
      a: ({ href, children }) => <a href={href} className="text-brand-400 hover:underline" target="_blank" rel="noopener noreferrer">{children}</a>,
      hr: () => <hr className="my-4 border-white/8" />,
    }}>{content}</ReactMarkdown>
  );
};

/* ── Confidence badge ──────────────────────────────────────── */
const ConfidenceBadge = ({ sources }) => {
  if (!sources?.length) return null;
  const avg = sources.reduce((a, s) => a + (s.score || 0), 0) / sources.length;
  const pct = Math.round(avg * 100);
  const color = pct >= 90 ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' 
    : pct >= 70 ? 'text-amber-400 bg-amber-500/10 border-amber-500/20' 
    : 'text-red-400 bg-red-500/10 border-red-500/20';
  return (
    <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-[11px] font-mono ${color}`}>
      <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
      Confidence {pct}%
    </div>
  );
};

/* ── Source card ────────────────────────────────────────────── */
const SourceCard = ({ source }) => {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);
  const [explanation, setExplanation] = useState('');
  const [isExplaining, setIsExplaining] = useState(false);
  const filename = source.file_path?.split('/').pop() || 'unknown';
  const folder = source.relative_path || source.file_path?.replace(/\/[^/]+$/, '') || '/';
  const scorePct = Math.round((source.score || 0) * 100);
  const scoreColor = scorePct >= 90 ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
    : scorePct >= 70 ? 'text-amber-400 bg-amber-500/10 border-amber-500/20'
    : 'text-red-400 bg-red-500/10 border-red-500/20';

  const handleExplain = async (e) => {
    e.stopPropagation();
    if (explanation) return;
    setIsExplaining(true); setExpanded(true);
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const res = await fetch(`${API_URL}/api/v1/explain`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_path: source.file_path, snippet: source.snippet, stream: true }),
      });
      if (!res.ok) throw new Error('Failed');
      const reader = res.body.getReader(); const decoder = new TextDecoder('utf-8');
      let done = false, streamed = '';
      while (!done) {
        const { value, done: d } = await reader.read(); done = d;
        if (value) {
          for (const line of decoder.decode(value, { stream: true }).split('\n')) {
            if (line.startsWith('data: ')) {
              const ds = line.substring(6).trim();
              if (ds === '[DONE]') { done = true; break; }
              try { const data = JSON.parse(ds); if (data.type === 'token') { streamed += data.content; setExplanation(streamed); } } catch {}
            }
          }
        }
      }
    } catch { setExplanation('Failed to generate explanation.'); }
    finally { setIsExplaining(false); }
  };

  return (
    <div className="rounded-xl border border-white/6 bg-[#0d1117] overflow-hidden transition-all hover:border-white/10">
      {/* Header */}
      <button onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-white/[0.02] transition-colors">
        <span className="text-lg shrink-0">📄</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-white/90 truncate">{filename}</span>
            <span className="shrink-0 text-[10px] text-white/30 bg-white/5 px-1.5 py-0.5 rounded uppercase font-mono">{source.language}</span>
          </div>
          <div className="text-[11px] text-white/35 font-mono truncate mt-0.5">{folder}</div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className={`text-[11px] font-mono px-2 py-0.5 rounded-md border ${scoreColor}`}>{scorePct}%</span>
          <span className="text-[11px] text-brand-400 font-mono bg-brand-500/10 px-2 py-0.5 rounded-md border border-brand-500/20">
            L{source.start_line}–{source.end_line}
          </span>
          <svg className={`w-4 h-4 text-white/30 transition-transform ${expanded ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {expanded && (
        <div className="border-t border-white/5 animate-fade-in">
          {/* Toolbar */}
          <div className="flex items-center justify-between px-4 py-2 bg-[#161b22] border-b border-white/5">
            <span className="shrink-0 rounded bg-emerald-500/15 px-2 py-0.5 text-[10px] font-medium text-emerald-300 uppercase border border-emerald-500/20">
              Retrieved Context
            </span>
            <div className="flex items-center gap-1.5">
              <button onClick={handleExplain} disabled={isExplaining || !!explanation}
                className="px-2 py-1 text-[10px] text-blue-400 bg-blue-500/10 hover:bg-blue-500/20 rounded-md transition-colors disabled:opacity-40 flex items-center gap-1">
                {isExplaining ? '⟳ Explaining...' : '💡 Explain'}
              </button>
              <button onClick={(e) => { e.stopPropagation(); navigator.clipboard.writeText(source.snippet); setCopied(true); setTimeout(() => setCopied(false), 2000); }}
                className="px-2 py-1 text-[10px] text-white/50 bg-white/5 hover:bg-white/10 rounded-md transition-colors">
                {copied ? '✓ Copied' : '📋 Copy'}
              </button>
              <button onClick={() => setExpanded(false)}
                className="px-2 py-1 text-[10px] text-white/50 bg-white/5 hover:bg-white/10 rounded-md transition-colors">
                ▲ Collapse
              </button>
            </div>
          </div>
          {/* Why selected */}
          {source.reason && (
            <div className="px-4 py-2 bg-brand-500/5 border-b border-white/5 text-[11px] text-brand-200/80 flex items-start gap-2">
              <span className="text-brand-400 mt-0.5">💡</span>
              <span><strong className="text-brand-300">Why selected:</strong> {source.reason}</span>
            </div>
          )}
          {/* Code */}
          <div className="max-h-80 overflow-y-auto scrollbar-thin scrollbar-thumb-white/10">
            <SyntaxHighlighter
              language={source.language?.toLowerCase() || 'text'} style={vscDarkPlus}
              customStyle={{ margin: 0, padding: '1rem', background: 'transparent', fontSize: '0.82rem' }}
              showLineNumbers startingLineNumber={source.start_line} wrapLines
              lineProps={() => ({ style: { display: 'block', backgroundColor: 'rgba(47,129,247,0.04)', borderLeft: '3px solid rgba(47,129,247,0.3)', paddingLeft: '12px' } })}>
              {source.snippet}
            </SyntaxHighlighter>
          </div>
          {/* AI Explanation */}
          {(explanation || isExplaining) && (
            <div className="p-4 border-t border-white/8 bg-[#161b22]">
              <div className="text-[10px] font-semibold text-blue-400 uppercase tracking-wider mb-2 flex items-center gap-1">💡 AI Explanation</div>
              <div className="text-xs text-white/80 prose-sm">
                <MarkdownContent content={explanation} />
                {isExplaining && <span className="inline-block w-2 h-3 ml-1 bg-white/60 animate-pulse" />}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

/* ── Related Files ─────────────────────────────────────────── */
const RelatedFiles = ({ sources, onAskAbout }) => {
  if (!sources?.length) return null;
  const files = [...new Set(sources.map(s => s.file_path?.split('/').pop()))].filter(Boolean);
  if (files.length <= 1) return null;
  return (
    <div className="mt-4 pt-3 border-t border-white/6">
      <p className="text-[11px] font-medium text-white/35 uppercase tracking-wider mb-2">Related Files</p>
      <div className="flex flex-wrap gap-1.5">
        {files.map((f, i) => (
          <button key={i} onClick={() => onAskAbout?.(`Explain ${f}`)}
            className="px-2.5 py-1 text-[11px] text-white/60 bg-white/[0.04] hover:bg-white/[0.08] border border-white/6 hover:border-white/12 rounded-lg transition-all hover:text-white/80 flex items-center gap-1.5">
            📄 {f}
          </button>
        ))}
      </div>
    </div>
  );
};

/* ── Message Bubble ────────────────────────────────────────── */
export default function MessageBubble({ message, onAskAbout }) {
  const isUser = message.role === 'user';
  const ts = useMemo(() => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), []);

  if (isUser) {
    return (
      <div className="flex w-full justify-end mb-5 animate-fade-in">
        <div className="max-w-[80%] rounded-2xl rounded-br-sm px-5 py-3.5 bg-brand-600 text-white shadow-lg shadow-brand-600/15">
          <p className="text-[15px] leading-relaxed whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex w-full justify-start mb-6 animate-fade-in">
      <div className="max-w-[92%] w-full">
        {/* AI avatar + content */}
        <div className="flex gap-3">
          <div className="shrink-0 w-8 h-8 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-md shadow-brand-500/20 mt-1">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
            </svg>
          </div>
          <div className="flex-1 min-w-0">
            {/* Header */}
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs font-semibold text-white/70">CodeLens AI</span>
              <span className="text-[10px] text-white/25">{ts}</span>
              {message.sources?.length > 0 && <ConfidenceBadge sources={message.sources} />}
              {message.sources?.[0]?.repository_name && (
                <span className="text-[10px] text-white/30 bg-white/5 px-1.5 py-0.5 rounded font-mono">{message.sources[0].repository_name}</span>
              )}
            </div>
            {/* Answer body */}
            <div className="text-[14.5px] text-white/85 leading-relaxed">
              <MarkdownContent content={message.content} />
              {message.isStreaming && <span className="inline-block w-2 h-5 ml-0.5 bg-brand-400 animate-pulse rounded-sm align-middle" />}
            </div>
            {/* Error state */}
            {message.isError && (
              <div className="mt-3 flex items-center gap-2 px-4 py-2.5 rounded-xl bg-red-500/8 border border-red-500/15 text-red-300 text-sm">
                <span>⚠</span> <span>{message.content}</span>
              </div>
            )}
            {/* Sources */}
            {message.sources?.length > 0 && !message.isStreaming && (
              <div className="mt-5 pt-4 border-t border-white/6">
                <p className="text-[11px] font-semibold text-white/35 mb-3 uppercase tracking-wider flex items-center gap-1.5">
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>
                  Sources Used ({message.sources.length})
                </p>
                <div className="flex flex-col gap-2">
                  {message.sources.map((s, i) => <SourceCard key={i} source={s} />)}
                </div>
                <RelatedFiles sources={message.sources} onAskAbout={onAskAbout} />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
