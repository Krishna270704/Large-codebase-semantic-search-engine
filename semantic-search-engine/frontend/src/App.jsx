import Navbar from "./components/Navbar";
import Home from "./pages/Home";
import { Toaster } from "react-hot-toast";

/**
 * App – root component.
 */
export default function App() {
  return (
    <div className="min-h-screen bg-surface-900">
      {/* Ambient background glow */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 left-1/2 h-[600px] w-[800px] -translate-x-1/2 rounded-full bg-brand-600/[0.06] blur-[120px]" />
        <div className="absolute -bottom-20 right-0 h-[400px] w-[500px] rounded-full bg-brand-500/[0.04] blur-[100px]" />
      </div>

      {/* Content */}
      <div className="relative z-10">
        <Toaster 
          position="top-right" 
          toastOptions={{
            style: {
              background: '#161b22',
              color: '#fff',
              border: '1px solid rgba(255,255,255,0.1)',
            }
          }} 
        />
        <Navbar />
        <Home />
      </div>
    </div>
  );
}
