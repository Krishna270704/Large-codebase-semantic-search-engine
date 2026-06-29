import React, { useState, useEffect, useMemo } from 'react';
import { getRepoStats, getRepoFile } from '../services/api';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

const getFileIcon = (filename) => {
  if (filename.endsWith('.js') || filename.endsWith('.jsx')) return '🟨';
  if (filename.endsWith('.ts') || filename.endsWith('.tsx')) return '🟦';
  if (filename.endsWith('.py')) return '🐍';
  if (filename.endsWith('.html')) return '🟧';
  if (filename.endsWith('.css')) return '🔷';
  if (filename.endsWith('.json')) return '{}';
  if (filename.endsWith('.md')) return '📝';
  return '📄';
};

const getLanguage = (filename) => {
  const ext = filename.split('.').pop().toLowerCase();
  switch(ext) {
    case 'js': case 'jsx': return 'javascript';
    case 'ts': case 'tsx': return 'typescript';
    case 'py': return 'python';
    case 'html': return 'html';
    case 'css': return 'css';
    case 'json': return 'json';
    case 'md': return 'markdown';
    default: return 'text';
  }
}

const TreeNode = ({ node, level, onSelectFile }) => {
  const [expanded, setExpanded] = useState(level < 1);
  const isDir = !!node.children;

  if (node.hidden) return null;

  return (
    <div className="w-full">
      <div 
        className={`flex items-center py-1 hover:bg-white/5 cursor-pointer text-sm transition-colors ${level === 0 ? '' : 'ml-4'} border-l border-white/5`}
        onClick={() => {
          if (isDir) {
            setExpanded(!expanded);
          } else {
            onSelectFile(node.path);
          }
        }}
      >
        <span className="w-4 h-4 flex items-center justify-center shrink-0 ml-1 mr-2 text-white/40">
          {isDir ? (
            <svg className={`w-3 h-3 transition-transform ${expanded ? 'rotate-90' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          ) : getFileIcon(node.name)}
        </span>
        <span className={`truncate ${isDir ? 'text-white/80' : 'text-white/60 hover:text-white'} flex-1 flex justify-between pr-2`}>
          {node.name}
          {!isDir && <span className="w-2 h-2 rounded-full bg-emerald-500/50 flex-shrink-0 mt-1.5 ml-2" title="Indexed File"></span>}
        </span>
      </div>
      {isDir && expanded && (
        <div className="flex flex-col w-full">
          {Object.values(node.children)
            .sort((a, b) => {
              if (!!a.children === !!b.children) return a.name.localeCompare(b.name);
              return a.children ? -1 : 1;
            })
            .map((child, idx) => (
              <TreeNode key={idx} node={child} level={level + 1} onSelectFile={onSelectFile} />
          ))}
        </div>
      )}
    </div>
  );
};

export default function RepoExplorer() {
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [files, setFiles] = useState([]);
  const [search, setSearch] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileContent, setFileContent] = useState("");
  const [fileLoading, setFileLoading] = useState(false);
  const [fileError, setFileError] = useState("");

  useEffect(() => {
    if (isOpen && files.length === 0) {
      setLoading(true);
      getRepoStats()
        .then(data => {
          if (data.files) setFiles(data.files);
        })
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [isOpen, files.length]);

  const tree = useMemo(() => {
    const root = { name: 'root', children: {}, path: '' };
    
    files.forEach(filepath => {
      const parts = filepath.split('/');
      let current = root;
      
      let matchSearch = search ? filepath.toLowerCase().includes(search.toLowerCase()) : true;

      for (let i = 0; i < parts.length; i++) {
        const part = parts[i];
        if (!current.children[part]) {
          current.children[part] = {
            name: part,
            path: parts.slice(0, i + 1).join('/'),
            children: i === parts.length - 1 ? null : {},
            hidden: !matchSearch && i === parts.length - 1
          };
        } else if (matchSearch && i === parts.length - 1) {
            current.children[part].hidden = false;
        }
        current = current.children[part];
      }
    });

    // Mark folders hidden if all children are hidden
    const hideEmptyDirs = (node) => {
      if (!node.children) return node.hidden;
      let allHidden = true;
      for (const child of Object.values(node.children)) {
        if (!hideEmptyDirs(child)) allHidden = false;
      }
      node.hidden = allHidden;
      return allHidden;
    };
    
    if (search) hideEmptyDirs(root);

    return root;
  }, [files, search]);

  const handleSelectFile = async (path) => {
    setSelectedFile(path);
    setFileLoading(true);
    setFileContent("");
    setFileError("");
    try {
      const data = await getRepoFile(path);
      setFileContent(data.content);
    } catch (e) {
      setFileError("Failed to load file content.");
    } finally {
      setFileLoading(false);
    }
  };

  return (
    <div className="glass-card overflow-hidden mt-4">
      {/* Toggle header */}
      <button
        onClick={() => setIsOpen((p) => !p)}
        className="flex w-full items-center justify-between px-5 py-4 text-left transition-colors hover:bg-white/[0.02]"
      >
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10">
            <svg className="h-4 w-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
            </svg>
          </div>
          <div>
            <p className="text-sm font-semibold text-white/80">Repository Explorer</p>
            <p className="text-xs text-white/30">Browse indexed codebase</p>
          </div>
        </div>
        <svg className={`h-4 w-4 text-white/30 transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Body */}
      {isOpen && (
        <div className="border-t border-white/[0.04] animate-fade-in bg-black/10 flex flex-col max-h-[60vh]">
          {loading ? (
             <div className="flex justify-center py-6">
                <svg className="h-5 w-5 animate-spin text-emerald-400" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                </svg>
             </div>
          ) : (
            <div className="flex flex-col w-full h-full">
              {/* Search */}
              <div className="p-3 border-b border-white/5 bg-black/20">
                <div className="relative">
                  <svg className="absolute left-2.5 top-2.5 w-4 h-4 text-white/30" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
                  <input
                    type="text"
                    placeholder="Search files..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="w-full bg-white/5 border border-white/10 rounded-lg pl-9 pr-3 py-1.5 text-sm text-white/80 placeholder-white/30 focus:outline-none focus:border-emerald-500/50"
                  />
                </div>
              </div>
              
              {/* Tree */}
              <div className="overflow-y-auto p-2 scrollbar-thin scrollbar-thumb-white/10 max-h-60">
                {Object.values(tree.children).length === 0 ? (
                  <div className="text-center text-xs text-white/30 py-4">No files found.</div>
                ) : (
                  Object.values(tree.children)
                    .sort((a, b) => {
                      if (!!a.children === !!b.children) return a.name.localeCompare(b.name);
                      return a.children ? -1 : 1;
                    })
                    .map((child, idx) => (
                      <TreeNode key={idx} node={child} level={0} onSelectFile={handleSelectFile} />
                    ))
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* File Modal */}
      {selectedFile && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-fade-in" onClick={() => setSelectedFile(null)}>
          <div 
            className="w-full max-w-5xl h-[85vh] bg-surface-900 border border-white/10 rounded-xl shadow-2xl flex flex-col overflow-hidden relative"
            onClick={e => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 bg-black/40 border-b border-white/5">
              <div className="flex items-center gap-2 overflow-hidden">
                <span className="text-white/40">{getFileIcon(selectedFile)}</span>
                <h3 className="text-sm font-medium text-white/80 truncate font-mono">{selectedFile}</h3>
                <span className="ml-2 px-1.5 py-0.5 text-[10px] rounded border border-emerald-500/30 text-emerald-400 bg-emerald-500/10">Indexed</span>
              </div>
              <button 
                onClick={() => setSelectedFile(null)}
                className="p-1 text-white/40 hover:text-white bg-white/5 hover:bg-white/10 rounded-md transition-colors"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
            
            {/* Content */}
            <div className="flex-1 overflow-auto bg-[#1e1e1e]">
              {fileLoading ? (
                <div className="flex items-center justify-center h-full">
                  <svg className="h-6 w-6 animate-spin text-emerald-400" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                  </svg>
                </div>
              ) : fileError ? (
                <div className="flex items-center justify-center h-full text-red-400/80 text-sm">
                  {fileError}
                </div>
              ) : (
                <SyntaxHighlighter
                  language={getLanguage(selectedFile)}
                  style={vscDarkPlus}
                  customStyle={{ margin: 0, borderRadius: 0, fontSize: '0.85rem', background: 'transparent' }}
                  showLineNumbers={true}
                  wrapLines={true}
                >
                  {fileContent}
                </SyntaxHighlighter>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
