import React, { useState, useEffect, useRef, useCallback } from 'react';
import MessageBubble from './MessageBubble';
import InputBox from './InputBox';
import toast from 'react-hot-toast';

const SUGGESTIONS = [
  "Explain the authentication system",
  "Where is JWT implemented?",
  "Show all API route handlers",
  "Explain the caching layer",
  "How does the database schema work?",
  "Find error handling patterns",
];

const LOADING_STEPS = [
  "Searching repository...",
  "Finding relevant code...",
  "Reranking results...",
  "Generating AI response...",
];

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);       // pre-stream (retrieval)
  const [isStreaming, setIsStreaming] = useState(false); // token streaming active
  const [loadingStep, setLoadingStep] = useState(0);
  const messagesEndRef = useRef(null);
  const loadingTimer = useRef(null);
  const abortRef = useRef(null);                        // AbortController

  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  useEffect(() => { scrollToBottom(); }, [messages, loading, isStreaming]);

  // Cycle loading steps during retrieval phase
  useEffect(() => {
    if (loading) {
      setLoadingStep(0);
      loadingTimer.current = setInterval(() => setLoadingStep(p => (p + 1) % LOADING_STEPS.length), 1800);
    } else {
      clearInterval(loadingTimer.current);
    }
    return () => clearInterval(loadingTimer.current);
  }, [loading]);

  /* ── Stop streaming ─────────────────────────────────────────── */
  const handleStop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsStreaming(false);
    setLoading(false);
    setMessages(prev => {
      const n = [...prev];
      if (n.length > 0) {
        n[n.length - 1].isStreaming = false;
        n[n.length - 1].isStopped = true;
      }
      return n;
    });
  }, []);

  /* ── Send question ──────────────────────────────────────────── */
  const handleSend = useCallback(async (text) => {
    // Cancel any existing stream
    abortRef.current?.abort();

    const history = messages.slice(-16).map(m => ({ role: m.role, content: m.content }));
    const controller = new AbortController();
    abortRef.current = controller;

    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setLoading(true);
    setIsStreaming(false);
    setMessages(prev => [...prev, { role: 'assistant', content: '', sources: [], isStreaming: true }]);

    try {
      const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
      const res = await fetch(`${API_URL}/api/v1/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: text, history, stream: true }),
        signal: controller.signal,
      });
      if (!res.ok) throw new Error(`Server returned ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let done = false, streamedContent = "";

      // Move from loading (retrieval) to streaming (token generation)
      setLoading(false);
      setIsStreaming(true);

      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        if (value) {
          for (const line of decoder.decode(value, { stream: true }).split('\n')) {
            if (line.startsWith('data: ')) {
              const ds = line.substring(6).trim();
              if (ds === '[DONE]') { done = true; break; }
              try {
                const data = JSON.parse(ds);
                if (data.type === 'sources') {
                  setMessages(prev => { const n = [...prev]; n[n.length - 1].sources = data.sources; return n; });
                } else if (data.type === 'token') {
                  streamedContent += data.content;
                  setMessages(prev => { const n = [...prev]; n[n.length - 1].content = streamedContent; return n; });
                } else if (data.type === 'error') {
                  streamedContent += "\n\n⚠ " + data.content;
                  setMessages(prev => { const n = [...prev]; n[n.length - 1].content = streamedContent; return n; });
                }
              } catch {}
            }
          }
        }
      }
    } catch (error) {
      if (error.name === 'AbortError') {
        // User cancelled — message already marked as stopped
        return;
      }
      console.error("Chat error:", error);
      setMessages(prev => {
        const n = [...prev];
        if (n.length > 0) {
          n[n.length - 1].content = "Generation interrupted. The server may be temporarily unavailable.";
          n[n.length - 1].isError = true;
        }
        return n;
      });
      toast.error("Failed to generate response.");
    } finally {
      setLoading(false);
      setIsStreaming(false);
      abortRef.current = null;
      setMessages(prev => {
        const n = [...prev];
        if (n.length > 0) n[n.length - 1].isStreaming = false;
        return n;
      });
    }
  }, [messages]);

  /* ── Regenerate last answer ────────────────────────────────── */
  const handleRegenerate = useCallback(() => {
    const lastUserMsg = messages.slice().reverse().find(m => m.role === 'user');
    if (lastUserMsg) {
      setMessages(prev => prev.slice(0, -1)); // Remove last assistant message
      handleSend(lastUserMsg.content);
    }
  }, [messages, handleSend]);

  return (
    <div className="flex flex-col h-[calc(100vh-80px)] w-full max-w-4xl mx-auto px-4 sm:px-6 relative">
      {/* New Chat */}
      {messages.length > 0 && (
        <div className="absolute top-4 right-4 sm:right-6 z-10 animate-fade-in">
          <button onClick={() => { handleStop(); setMessages([]); }} disabled={loading}
            className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-white/60 hover:text-white bg-surface-800/80 hover:bg-surface-700 border border-white/8 hover:border-white/15 rounded-lg backdrop-blur-sm transition-all disabled:opacity-50">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
            New Chat
          </button>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto py-6 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center animate-fade-in">
            <div className="w-16 h-16 rounded-2xl bg-brand-500/10 text-brand-400 flex items-center justify-center mb-6 shadow-[0_0_60px_rgba(47,129,247,0.12)] ring-1 ring-brand-500/15">
              <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M14.25 9.75L16.5 12l-2.25 2.25m-4.5 0L7.5 12l2.25-2.25M6 20.25h12A2.25 2.25 0 0020.25 18V6A2.25 2.25 0 0018 3.75H6A2.25 2.25 0 003.75 6v12A2.25 2.25 0 006 20.25z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">Welcome to CodeLens</h2>
            <p className="text-white/40 max-w-md text-sm mb-8">
              Ask questions about your indexed codebase using natural language. I'll find the relevant code and explain it.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 max-w-lg w-full">
              {SUGGESTIONS.map((s, i) => (
                <button key={i} onClick={() => handleSend(s)}
                  className="text-left px-4 py-3 rounded-xl border border-white/6 bg-white/[0.02] hover:bg-white/[0.05] hover:border-white/12 text-sm text-white/50 hover:text-white/80 transition-all group">
                  <span className="text-brand-400/60 group-hover:text-brand-400 mr-1.5">→</span> {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex flex-col">
            {messages.map((msg, i) => (
              <React.Fragment key={i}>
                <MessageBubble message={msg} onAskAbout={handleSend} />

                {/* Retry on error */}
                {msg.isError && i === messages.length - 1 && !loading && !isStreaming && (
                  <div className="flex justify-start mb-6 ml-11 animate-fade-in">
                    <button onClick={handleRegenerate}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-brand-400 bg-brand-500/10 hover:bg-brand-500/20 border border-brand-500/20 rounded-lg transition-colors">
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                      Retry
                    </button>
                  </div>
                )}

                {/* Stopped message */}
                {msg.isStopped && i === messages.length - 1 && !loading && !isStreaming && (
                  <div className="flex justify-start mb-6 ml-11 gap-2 animate-fade-in">
                    <span className="text-[11px] text-white/30 self-center">Generation stopped</span>
                    <button onClick={handleRegenerate}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-brand-400 bg-brand-500/10 hover:bg-brand-500/20 border border-brand-500/20 rounded-lg transition-colors">
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                      Regenerate
                    </button>
                  </div>
                )}

                {/* Regenerate after successful completion */}
                {msg.role === 'assistant' && !msg.isStreaming && !msg.isError && !msg.isStopped && i === messages.length - 1 && !loading && !isStreaming && msg.content && (
                  <div className="flex justify-start mb-6 ml-11 animate-fade-in">
                    <button onClick={handleRegenerate}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-white/30 hover:text-white/60 bg-white/[0.02] hover:bg-white/[0.05] border border-white/5 hover:border-white/10 rounded-lg transition-all">
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                      Regenerate Response
                    </button>
                  </div>
                )}
              </React.Fragment>
            ))}

            {/* Loading indicator (pre-stream retrieval phase) */}
            {loading && (
              <div className="flex w-full justify-start mb-6 animate-fade-in">
                <div className="flex gap-3">
                  <div className="shrink-0 w-8 h-8 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-md shadow-brand-500/20">
                    <svg className="w-4 h-4 text-white animate-spin" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                    </svg>
                  </div>
                  <div className="bg-surface-800/60 border border-white/5 rounded-2xl rounded-bl-sm px-5 py-3.5">
                    <div className="flex items-center gap-2.5">
                      <div className="flex gap-1">
                        <span className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce [animation-delay:-0.3s]" />
                        <span className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce [animation-delay:-0.15s]" />
                        <span className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce" />
                      </div>
                      <span className="text-sm text-white/40">{LOADING_STEPS[loadingStep]}</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} className="h-4" />
          </div>
        )}
      </div>

      {/* Input */}
      <div className="pt-2 pb-6">
        <InputBox onSend={handleSend} disabled={loading} isStreaming={isStreaming} onStop={handleStop} />
        <p className="text-center mt-3 text-[11px] text-white/20">
          AI can make mistakes · Always verify the provided code · Press <kbd className="px-1 py-0.5 bg-white/5 rounded text-[10px]">/</kbd> to focus · <kbd className="px-1 py-0.5 bg-white/5 rounded text-[10px]">Esc</kbd> to stop
        </p>
      </div>
    </div>
  );
}
