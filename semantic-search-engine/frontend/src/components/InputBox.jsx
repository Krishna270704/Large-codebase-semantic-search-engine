import React, { useState, useRef, useEffect } from 'react';

export default function InputBox({ onSend, disabled, isStreaming, onStop }) {
  const [input, setInput] = useState('');
  const textareaRef = useRef(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  // Global shortcut: "/" to focus, Escape to stop
  useEffect(() => {
    const handleGlobalKeyDown = (e) => {
      if (e.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
        e.preventDefault();
        textareaRef.current?.focus();
      }
      if (e.key === 'Escape' && isStreaming) {
        onStop?.();
      }
    };
    window.addEventListener('keydown', handleGlobalKeyDown);
    return () => window.removeEventListener('keydown', handleGlobalKeyDown);
  }, [isStreaming, onStop]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = () => {
    if (input.trim() && !disabled && !isStreaming) {
      onSend(input.trim());
      setInput('');
    }
  };

  return (
    <div className="relative flex items-end w-full bg-surface-800 rounded-2xl border border-white/10 shadow-lg p-2 focus-within:border-brand-500/40 focus-within:ring-1 focus-within:ring-brand-500/20 transition-all">
      <textarea
        ref={textareaRef}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask a question about your codebase... (Press '/' to focus)"
        disabled={disabled || isStreaming}
        className="w-full max-h-[200px] bg-transparent text-white placeholder-white/30 resize-none py-3 pl-4 pr-14 focus:outline-none disabled:opacity-50 text-[15px] leading-relaxed"
        rows={1}
      />

      {isStreaming ? (
        /* ── Stop Generating button ─────────────────────────────── */
        <button
          onClick={onStop}
          className="absolute right-3 bottom-3 px-3 py-2 bg-red-500/15 text-red-400 border border-red-500/25 rounded-xl hover:bg-red-500/25 transition-colors flex items-center gap-1.5 text-xs font-medium shadow-md"
        >
          <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
            <rect x="6" y="6" width="12" height="12" rx="2" />
          </svg>
          Stop
        </button>
      ) : (
        /* ── Send button ────────────────────────────────────────── */
        <button
          onClick={handleSend}
          disabled={!input.trim() || disabled}
          className="absolute right-3 bottom-3 p-2 bg-brand-600 text-white rounded-xl hover:bg-brand-500 disabled:opacity-40 disabled:hover:bg-brand-600 transition-colors flex items-center justify-center shadow-md"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
            <path d="M3.478 2.404a.75.75 0 0 0-.926.941l2.432 7.905H13.5a.75.75 0 0 1 0 1.5H4.984l-2.432 7.905a.75.75 0 0 0 .926.94 60.519 60.519 0 0 0 18.445-8.986.75.75 0 0 0 0-1.218A60.517 60.517 0 0 0 3.478 2.404Z" />
          </svg>
        </button>
      )}
    </div>
  );
}
