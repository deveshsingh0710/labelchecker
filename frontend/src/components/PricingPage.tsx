import React from 'react';
import { Check, Sparkles, Building2, Shield, ArrowRight, Zap } from 'lucide-react';

interface PricingPageProps {
  onRequestDemo: (prefillType?: string) => void;
  onSelectStarter: () => void;
}

export const PricingPage: React.FC<PricingPageProps> = ({ onRequestDemo, onSelectStarter }) => {
  return (
    <div className="space-y-12 py-4">
      {/* Hero Header */}
      <div className="text-center max-w-3xl mx-auto space-y-4">
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-sky-50 border border-sky-200 text-sky-700 text-xs font-semibold">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Flexible Legal Metrology Compliance Plans</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-black text-slate-900 tracking-tight">
          Transparent Pricing for Brands, Marketplaces & Enforcement
        </h1>
        <p className="text-sm sm:text-base text-slate-600 leading-relaxed">
          From independent packaged goods producers testing labels before printing, to national e-commerce marketplaces auto-screening seller catalogs and state enforcement inspectors.
        </p>
      </div>

      {/* 3 Tiered Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto items-stretch">
        {/* Tier 1: Starter */}
        <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-xs hover:shadow-md transition-shadow flex flex-col justify-between">
          <div className="space-y-6">
            <div>
              <div className="inline-block px-2.5 py-1 rounded-md text-xs font-bold bg-slate-100 text-slate-700 mb-2">
                STARTER
              </div>
              <h3 className="text-xl font-black text-slate-900">Small Manufacturer</h3>
              <p className="text-xs text-slate-500 mt-1">
                For independent food, cosmetic & commodity makers verifying packaging before plate making.
              </p>
            </div>

            <div className="flex items-baseline space-x-2">
              <span className="text-4xl font-black text-slate-900">₹0</span>
              <span className="text-xs text-slate-500 font-medium">/ forever free</span>
            </div>

            <div className="border-t border-slate-100 pt-6 space-y-3">
              <p className="text-xs font-bold text-slate-800 uppercase tracking-wider">What's Included:</p>
              <ul className="space-y-2.5 text-xs text-slate-600">
                <li className="flex items-start space-x-2.5">
                  <Check className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                  <span>Up to <b>25 label scans / month</b></span>
                </li>
                <li className="flex items-start space-x-2.5">
                  <Check className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                  <span>Full Legal Metrology Rule 6 evaluation</span>
                </li>
                <li className="flex items-start space-x-2.5">
                  <Check className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                  <span>OpenCV auto-deskew & glare reduction</span>
                </li>
                <li className="flex items-start space-x-2.5">
                  <Check className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                  <span>Interactive bounding-box visual inspector</span>
                </li>
                <li className="flex items-start space-x-2.5">
                  <Check className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                  <span>Standard PDF compliance audit reports</span>
                </li>
              </ul>
            </div>
          </div>

          <div className="pt-8">
            <button
              onClick={onSelectStarter}
              className="w-full py-2.5 px-4 rounded-xl border border-slate-300 hover:border-slate-400 bg-white hover:bg-slate-50 text-slate-800 font-bold text-xs transition-colors shadow-2xs"
            >
              Start Free Verification
            </button>
          </div>
        </div>

        {/* Tier 2: Business (Featured) */}
        <div className="bg-white rounded-2xl border-2 border-sky-500 p-8 shadow-lg shadow-sky-100 relative flex flex-col justify-between">
          <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 bg-gradient-to-r from-sky-600 to-indigo-600 text-white text-[11px] font-bold px-3 py-0.5 rounded-full shadow-xs uppercase tracking-wider">
            Most Popular for Brands
          </div>

          <div className="space-y-6">
            <div>
              <div className="inline-block px-2.5 py-1 rounded-md text-xs font-bold bg-sky-50 text-sky-700 mb-2">
                BUSINESS
              </div>
              <h3 className="text-xl font-black text-slate-900">FMCG Brands & Audit Firms</h3>
              <p className="text-xs text-slate-500 mt-1">
                For brands doing high-volume pre-print compliance checks across multi-SKU product lines.
              </p>
            </div>

            <div className="flex items-baseline space-x-2">
              <span className="text-4xl font-black text-slate-900">₹299</span>
              <span className="text-xs text-slate-500 font-medium">/ month (billed annually)</span>
            </div>

            <div className="border-t border-slate-100 pt-6 space-y-3">
              <p className="text-xs font-bold text-slate-800 uppercase tracking-wider">Everything in Starter, plus:</p>
              <ul className="space-y-2.5 text-xs text-slate-600">
                <li className="flex items-start space-x-2.5">
                  <Check className="w-4 h-4 text-sky-600 flex-shrink-0 mt-0.5" />
                  <span><b>500 label scans / month</b></span>
                </li>
                <li className="flex items-start space-x-2.5">
                  <Check className="w-4 h-4 text-sky-600 flex-shrink-0 mt-0.5" />
                  <span>Multi-user team workspace & roles</span>
                </li>
                <li className="flex items-start space-x-2.5">
                  <Check className="w-4 h-4 text-sky-600 flex-shrink-0 mt-0.5" />
                  <span>High-resolution ReportLab PDF exports with branded logo</span>
                </li>
                <li className="flex items-start space-x-2.5">
                  <Check className="w-4 h-4 text-sky-600 flex-shrink-0 mt-0.5" />
                  <span>Violation frequency analytics & trends dashboard</span>
                </li>
                <li className="flex items-start space-x-2.5">
                  <Check className="w-4 h-4 text-sky-600 flex-shrink-0 mt-0.5" />
                  <span>Priority OCR processing queue (&lt; 2s latency)</span>
                </li>
              </ul>
            </div>
          </div>

          <div className="pt-8">
            <button
              onClick={() => onRequestDemo('brand')}
              className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-sky-600 to-indigo-600 hover:from-sky-700 hover:to-indigo-700 text-white font-bold text-xs transition-all shadow-md shadow-sky-100 flex items-center justify-center space-x-1.5"
            >
              <span>Get Started with Business</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Tier 3: Enterprise / Government */}
        <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-xs hover:shadow-md transition-shadow flex flex-col justify-between">
          <div className="space-y-6">
            <div>
              <div className="inline-block px-2.5 py-1 rounded-md text-xs font-bold bg-indigo-50 text-indigo-700 mb-2">
                ENTERPRISE / GOVT
              </div>
              <h3 className="text-xl font-black text-slate-900">Marketplaces & Enforcement</h3>
              <p className="text-xs text-slate-500 mt-1">
                For e-commerce platforms (Amazon, Blinkit, QuickCart) and Legal Metrology field inspection wings.
              </p>
            </div>

            <div className="flex items-baseline space-x-2">
              <span className="text-3xl font-black text-slate-900">Custom</span>
              <span className="text-xs text-slate-500 font-medium">/ volume-based contract</span>
            </div>

            <div className="border-t border-slate-100 pt-6 space-y-3">
              <p className="text-xs font-bold text-slate-800 uppercase tracking-wider">Enterprise Capabilities:</p>
              <ul className="space-y-2.5 text-xs text-slate-600">
                <li className="flex items-start space-x-2.5">
                  <Check className="w-4 h-4 text-indigo-600 flex-shrink-0 mt-0.5" />
                  <span><b>Unlimited scans</b> & automated catalog screening</span>
                </li>
                <li className="flex items-start space-x-2.5">
                  <Check className="w-4 h-4 text-indigo-600 flex-shrink-0 mt-0.5" />
                  <span>Full REST API integration for seller onboarding</span>
                </li>
                <li className="flex items-start space-x-2.5">
                  <Check className="w-4 h-4 text-indigo-600 flex-shrink-0 mt-0.5" />
                  <span>Mobile Inspector View for field raids & seizures</span>
                </li>
                <li className="flex items-start space-x-2.5">
                  <Check className="w-4 h-4 text-indigo-600 flex-shrink-0 mt-0.5" />
                  <span>Custom state/sector rule configurations & advisory</span>
                </li>
                <li className="flex items-start space-x-2.5">
                  <Check className="w-4 h-4 text-indigo-600 flex-shrink-0 mt-0.5" />
                  <span>Dedicated legal compliance SLA & on-prem deployment</span>
                </li>
              </ul>
            </div>
          </div>

          <div className="pt-8">
            <button
              onClick={() => onRequestDemo('government')}
              className="w-full py-2.5 px-4 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs transition-colors shadow-2xs flex items-center justify-center space-x-1.5"
            >
              <Building2 className="w-3.5 h-3.5" />
              <span>Contact Sales & Request Demo</span>
            </button>
          </div>
        </div>
      </div>

      {/* Feature Highlight Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto pt-6">
        <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs space-y-2">
          <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center">
            <Shield className="w-4 h-4" />
          </div>
          <h4 className="text-sm font-bold text-slate-900">Penalty Mitigation</h4>
          <p className="text-xs text-slate-500 leading-relaxed">
            Avoid compounding fines under Rule 32 and Section 36 of the Legal Metrology Act (fines up to ₹50,000 and seizure of stock).
          </p>
        </div>

        <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs space-y-2">
          <div className="w-8 h-8 rounded-lg bg-sky-50 text-sky-700 flex items-center justify-center">
            <Zap className="w-4 h-4" />
          </div>
          <h4 className="text-sm font-bold text-slate-900">Pre-Print Confidence</h4>
          <p className="text-xs text-slate-500 leading-relaxed">
            Catch missing tax declarations or illegal non-standard units (like 'gms' instead of 'g') before sending packaging art to cylinder/plate engraving.
          </p>
        </div>

        <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs space-y-2">
          <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-700 flex items-center justify-center">
            <Building2 className="w-4 h-4" />
          </div>
          <h4 className="text-sm font-bold text-slate-900">E-Commerce Marketplace Gatekeeper</h4>
          <p className="text-xs text-slate-500 leading-relaxed">
            Auto-screen third-party seller product listings upon image upload to prevent notice liabilities for intermediary platforms.
          </p>
        </div>
      </div>
    </div>
  );
};
