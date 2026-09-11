import React from 'react';
import {
  ShieldCheck,
  BarChart3,
  BookOpen,
  Sparkles,
  Tag,
  Building2,
  ChevronDown,
  CalendarDays
} from 'lucide-react';
import type { Organization, User } from '../types';

interface NavbarProps {
  activeTab: 'verifier' | 'analytics' | 'pricing' | 'guide';
  setActiveTab: (tab: 'verifier' | 'analytics' | 'pricing' | 'guide') => void;
  totalAuditsCount?: number;
  activeOrg?: Organization | null;
  currentUser?: User | null;
  onOpenOrgModal: () => void;
  onOpenDemoModal: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  totalAuditsCount,
  activeOrg,
  currentUser,
  onOpenOrgModal,
  onOpenDemoModal,
}) => {
  const getOrgBadgeColor = (type?: string) => {
    if (type === 'government') return 'bg-indigo-50 text-indigo-700 border-indigo-200';
    if (type === 'marketplace') return 'bg-amber-50 text-amber-700 border-amber-200';
    return 'bg-emerald-50 text-emerald-700 border-emerald-200';
  };

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-40 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Brand Logo */}
          <div
            className="flex items-center space-x-3 cursor-pointer"
            onClick={() => setActiveTab('verifier')}
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-sky-100 flex-shrink-0">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xl font-bold text-slate-900 tracking-tight">LabelCheck</span>
                <span className="hidden sm:inline-block px-2 py-0.5 text-[10px] font-semibold rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 uppercase">
                  LM Rules 2011
                </span>
              </div>
              <p className="hidden sm:block text-[11px] text-slate-500 font-medium">Packaged Commodity Compliance</p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="hidden md:flex items-center space-x-1 lg:space-x-1.5">
            <button
              onClick={() => setActiveTab('verifier')}
              className={`px-3 py-2 rounded-lg text-xs font-bold transition-all flex items-center space-x-1.5 cursor-pointer ${
                activeTab === 'verifier'
                  ? 'bg-sky-50 text-sky-700 shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Verifier</span>
            </button>

            <button
              onClick={() => setActiveTab('analytics')}
              className={`px-3 py-2 rounded-lg text-xs font-bold transition-all flex items-center space-x-1.5 relative cursor-pointer ${
                activeTab === 'analytics'
                  ? 'bg-sky-50 text-sky-700 shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <BarChart3 className="w-3.5 h-3.5" />
              <span>Analytics & History</span>
              {typeof totalAuditsCount === 'number' && totalAuditsCount > 0 && (
                <span className="ml-0.5 px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-slate-200 text-slate-700">
                  {totalAuditsCount}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('pricing')}
              className={`px-3 py-2 rounded-lg text-xs font-bold transition-all flex items-center space-x-1.5 cursor-pointer ${
                activeTab === 'pricing'
                  ? 'bg-sky-50 text-sky-700 shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <Tag className="w-3.5 h-3.5" />
              <span>Pricing</span>
            </button>

            <button
              onClick={() => setActiveTab('guide')}
              className={`px-3 py-2 rounded-lg text-xs font-bold transition-all flex items-center space-x-1.5 cursor-pointer ${
                activeTab === 'guide'
                  ? 'bg-sky-50 text-sky-700 shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <BookOpen className="w-3.5 h-3.5" />
              <span>Legal Rules</span>
            </button>
          </nav>

          {/* Right Action: Org Switcher + Demo CTA */}
          <div className="flex items-center space-x-2">
            {/* Organization / Tenant Badge */}
            <button
              onClick={onOpenOrgModal}
              className="px-2.5 sm:px-3 py-1.5 rounded-xl border border-slate-200 hover:border-slate-300 bg-white hover:bg-slate-50 text-slate-700 transition-colors flex items-center space-x-2 cursor-pointer shadow-2xs"
              title={currentUser ? `Signed in as ${currentUser.name} (${activeOrg?.name})` : "Click to switch organization or tenant"}
            >
              <Building2 className="w-3.5 h-3.5 text-slate-400" />
              <div className="text-left hidden sm:block max-w-[140px] truncate">
                <span className="text-[11px] font-bold text-slate-900 block truncate">
                  {activeOrg ? activeOrg.name : 'Select Org'}
                </span>
                <span className={`text-[9px] font-extrabold uppercase px-1 py-0.2 rounded border ${getOrgBadgeColor(activeOrg?.type)}`}>
                  {currentUser ? `${currentUser.name.split(' ')[0]} • ${activeOrg?.type}` : (activeOrg ? activeOrg.type : 'Guest')}
                </span>
              </div>
              <ChevronDown className="w-3 h-3 text-slate-400" />
            </button>

            {/* Request a Demo CTA */}
            <button
              onClick={onOpenDemoModal}
              className="bg-gradient-to-r from-sky-600 to-indigo-600 hover:from-sky-700 hover:to-indigo-700 text-white font-bold text-xs px-3 sm:px-3.5 py-2 rounded-xl transition-all shadow-sm shadow-sky-100 flex items-center space-x-1.5 cursor-pointer"
            >
              <CalendarDays className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Request a Demo</span>
              <span className="sm:hidden">Demo</span>
            </button>
          </div>
        </div>

        {/* Mobile Navigation Row */}
        <div className="flex md:hidden overflow-x-auto py-2 border-t border-slate-100 space-x-2 text-xs no-scrollbar">
          <button
            onClick={() => setActiveTab('verifier')}
            className={`px-2.5 py-1 rounded-lg font-bold flex-shrink-0 ${
              activeTab === 'verifier' ? 'bg-sky-50 text-sky-700' : 'text-slate-600'
            }`}
          >
            Verifier
          </button>
          <button
            onClick={() => setActiveTab('analytics')}
            className={`px-2.5 py-1 rounded-lg font-bold flex-shrink-0 ${
              activeTab === 'analytics' ? 'bg-sky-50 text-sky-700' : 'text-slate-600'
            }`}
          >
            Analytics & History
          </button>
          <button
            onClick={() => setActiveTab('pricing')}
            className={`px-2.5 py-1 rounded-lg font-bold flex-shrink-0 ${
              activeTab === 'pricing' ? 'bg-sky-50 text-sky-700' : 'text-slate-600'
            }`}
          >
            Pricing
          </button>
          <button
            onClick={() => setActiveTab('guide')}
            className={`px-2.5 py-1 rounded-lg font-bold flex-shrink-0 ${
              activeTab === 'guide' ? 'bg-sky-50 text-sky-700' : 'text-slate-600'
            }`}
          >
            Rules Guide
          </button>
        </div>
      </div>
    </header>
  );
};
