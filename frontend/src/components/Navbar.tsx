import React from 'react';
import { ShieldCheck, History, BookOpen, Sparkles } from 'lucide-react';

interface NavbarProps {
  activeTab: 'verifier' | 'history' | 'guide';
  setActiveTab: (tab: 'verifier' | 'history' | 'guide') => void;
  totalAuditsCount?: number;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, setActiveTab, totalAuditsCount }) => {
  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-40 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Brand Logo */}
          <div 
            className="flex items-center space-x-3 cursor-pointer"
            onClick={() => setActiveTab('verifier')}
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-sky-100">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xl font-bold text-slate-900 tracking-tight">LabelCheck</span>
                <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                  LM Rules 2011
                </span>
              </div>
              <p className="text-xs text-slate-500 font-medium">AI Packaged Commodity Compliance Checker</p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex items-center space-x-1 sm:space-x-2">
            <button
              onClick={() => setActiveTab('verifier')}
              className={`px-3 sm:px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center space-x-2 ${
                activeTab === 'verifier'
                  ? 'bg-sky-50 text-sky-700 font-semibold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <Sparkles className="w-4 h-4" />
              <span>Verifier</span>
            </button>

            <button
              onClick={() => setActiveTab('history')}
              className={`px-3 sm:px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center space-x-2 relative ${
                activeTab === 'history'
                  ? 'bg-sky-50 text-sky-700 font-semibold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <History className="w-4 h-4" />
              <span>Audit History</span>
              {typeof totalAuditsCount === 'number' && totalAuditsCount > 0 && (
                <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-slate-200 text-slate-700">
                  {totalAuditsCount}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('guide')}
              className={`px-3 sm:px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center space-x-2 ${
                activeTab === 'guide'
                  ? 'bg-sky-50 text-sky-700 font-semibold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <BookOpen className="w-4 h-4" />
              <span>Rules Guide</span>
            </button>
          </nav>
        </div>
      </div>
    </header>
  );
};
