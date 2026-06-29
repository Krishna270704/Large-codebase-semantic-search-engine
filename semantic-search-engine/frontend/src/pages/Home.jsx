import { useState } from "react";
import RepoIngestion from "../components/RepoIngestion";
import RepoDashboard from "../components/RepoDashboard";
import RepoExplorer from "../components/RepoExplorer";
import Chat from "../components/Chat";

/**
 * Home – Main application layout.
 */
export default function Home() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-[calc(100vh-64px)] overflow-hidden">
      
      {/* Mobile sidebar toggle overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/60 z-40 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div 
        className={`fixed md:static inset-y-0 left-0 z-50 w-80 bg-surface-900 border-r border-white/5 transform transition-transform duration-300 flex flex-col pt-16 md:pt-0
        ${sidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}
        `}
      >
        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-6">
          <div className="mb-2">
            <h3 className="text-sm font-medium text-white/50 uppercase tracking-wider mb-4 px-2">Project Settings</h3>
            <RepoIngestion />
            <RepoDashboard />
            <RepoExplorer />
          </div>
          
          <div className="mt-auto px-2 pb-4 text-xs text-white/20 text-center">
            Semantic Code Search Engine<br/>
            FastAPI + ChromaDB + React
          </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-surface-950 relative">
        {/* Mobile header / Sidebar toggle */}
        <div className="md:hidden flex items-center p-4 border-b border-white/5 absolute top-0 left-0 right-0 z-30 bg-surface-950/80 backdrop-blur-md">
          <button 
            onClick={() => setSidebarOpen(true)}
            className="p-2 -ml-2 text-white/70 hover:text-white transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
            </svg>
          </button>
          <h1 className="font-semibold ml-2">Code Assistant</h1>
        </div>

        <main className="flex-1 relative md:pt-0 pt-14">
          <Chat />
        </main>
      </div>

    </div>
  );
}
