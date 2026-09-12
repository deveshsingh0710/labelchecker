import React from 'react';
import {
  ShieldCheck,
  AlertTriangle,
  XCircle,
  FileDown,
  RotateCcw,
  Scale
} from 'lucide-react';
import type { VerificationResult } from '../types';
import { getAssetUrl } from '../config';

interface InspectorViewProps {
  result: VerificationResult;
  onReset: () => void;
  onDownloadReport: () => void;
  isDownloading: boolean;
}

export const InspectorView: React.FC<InspectorViewProps> = ({
  result,
  onReset,
  onDownloadReport,
  isDownloading
}) => {
  const isPass = result.compliance_status === 'COMPLIANT';
  const isFail = result.compliance_status === 'NON_COMPLIANT';
  const isReview = result.compliance_status === 'PARTIALLY_COMPLIANT';

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* 1. Instant High-Impact Verdict Header */}
      <div
        className={`rounded-3xl p-6 sm:p-8 text-white shadow-lg transition-all ${
          isPass
            ? 'bg-gradient-to-r from-emerald-600 to-teal-700 shadow-emerald-200'
            : isFail
            ? 'bg-gradient-to-r from-rose-600 to-red-700 shadow-rose-200'
            : 'bg-gradient-to-r from-amber-500 to-orange-600 shadow-amber-200'
        }`}
      >
        <div className="flex flex-col sm:flex-row items-center sm:items-start justify-between gap-6">
          <div className="flex items-center sm:items-start space-x-4 text-center sm:text-left">
            <div className="p-3.5 rounded-2xl bg-white/15 backdrop-blur-xs flex-shrink-0">
              {isPass && <ShieldCheck className="w-12 h-12 text-white" />}
              {isFail && <XCircle className="w-12 h-12 text-white" />}
              {isReview && <AlertTriangle className="w-12 h-12 text-white" />}
            </div>
            <div>
              <div className="inline-block px-2.5 py-0.5 rounded-full bg-white/20 text-xs font-bold uppercase tracking-wider mb-2">
                Field Inspection Verdict
              </div>
              <h2 className="text-2xl sm:text-3xl font-black tracking-tight">
                {isPass && 'PASSED STATUTORY INSPECTION'}
                {isFail && 'VIOLATION DETECTED — NON-COMPLIANT'}
                {isReview && 'PARTIAL COMPLIANCE — NEEDS REVIEW'}
              </h2>
              <p className="text-xs sm:text-sm text-white/85 mt-1 font-medium">
                {isPass && 'All mandatory declarations under Legal Metrology Rule 6(1) are present and verified.'}
                {isFail && `${result.total_failed} mandatory statutory declaration(s) violate Legal Metrology Rules, 2011.`}
                {isReview && `${result.total_needs_review} declaration(s) require manual inspector verification.`}
              </p>
            </div>
          </div>

          {/* Large Score Indicator */}
          <div className="bg-white/15 rounded-2xl p-4 text-center min-w-[120px] backdrop-blur-xs border border-white/20">
            <span className="text-xs font-bold text-white/80 uppercase tracking-wider block">Compliance</span>
            <span className="text-4xl font-black text-white">{result.overall_score}</span>
            <span className="text-xs text-white/70 block">/ 100</span>
          </div>
        </div>

        {/* Big Touch Action Buttons for Field Officers */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-6 pt-6 border-t border-white/20">
          <button
            onClick={onDownloadReport}
            disabled={isDownloading}
            className="py-3.5 px-4 rounded-xl bg-white text-slate-900 font-bold text-sm hover:bg-slate-100 transition-colors shadow-sm flex items-center justify-center space-x-2 cursor-pointer active:scale-98"
          >
            <FileDown className={`w-4 h-4 text-sky-600 ${isDownloading ? 'animate-bounce' : ''}`} />
            <span>{isDownloading ? 'Generating Report...' : 'Download Official Audit PDF'}</span>
          </button>

          <button
            onClick={onReset}
            className="py-3.5 px-4 rounded-xl bg-white/20 hover:bg-white/30 text-white font-bold text-sm transition-colors flex items-center justify-center space-x-2 cursor-pointer active:scale-98"
          >
            <RotateCcw className="w-4 h-4" />
            <span>Inspect Another Package</span>
          </button>
        </div>
      </div>

      {/* 2. Quick Evidence Snapshot & Statutory Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-start">
        {/* Left: Package Thumbnail */}
        <div className="md:col-span-4 bg-white rounded-2xl border border-slate-200 p-4 shadow-xs space-y-3">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span className="font-bold text-slate-700">Seized/Inspected Sample</span>
            <span className="font-mono">{result.filename}</span>
          </div>

          <div className="rounded-xl overflow-hidden bg-slate-100 border border-slate-200 aspect-3/4 flex items-center justify-center">
            <img
              src={getAssetUrl(result.preprocessed_image_url || result.raw_image_url)}
              alt="Inspected Packaging"
              className="w-full h-full object-contain"
            />
          </div>

          <div className="text-[11px] text-slate-400 text-center font-mono">
            OCR Confidence: <span className="text-slate-700 font-bold">{result.ocr_summary.average_confidence}%</span> &bull; Words: {result.ocr_summary.total_words}
          </div>
        </div>

        {/* Right: Statutory Checklist */}
        <div className="md:col-span-8 bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
              <Scale className="w-4 h-4 text-sky-600" />
              <span>Statutory Rule 6(1) Inspection Findings</span>
            </h3>
            <div className="flex items-center space-x-2 text-[11px] font-bold">
              <span className="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                {result.total_passed} Passed
              </span>
              <span className="text-rose-700 bg-rose-50 px-2 py-0.5 rounded-full border border-rose-200">
                {result.total_failed} Failed
              </span>
            </div>
          </div>

          {/* Quick-Glance Checklist */}
          <div className="space-y-2.5">
            {result.evaluation_results.map((item) => {
              const isItemPass = item.status === 'PASS';
              const isItemFail = item.status === 'FAIL';

              return (
                <div
                  key={item.rule_id}
                  className={`p-3 rounded-xl border transition-all flex items-start justify-between gap-3 ${
                    isItemPass
                      ? 'bg-emerald-50/40 border-emerald-200'
                      : isItemFail
                      ? 'bg-rose-50/60 border-rose-200 shadow-2xs'
                      : 'bg-amber-50/40 border-amber-200'
                  }`}
                >
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                        {item.legal_reference}
                      </span>
                      <span className="text-xs font-bold text-slate-900">{item.title}</span>
                    </div>

                    <p className="text-xs text-slate-600">
                      Value: <span className="font-medium text-slate-800 font-mono">{item.extracted_value || 'None (Missing)'}</span>
                    </p>

                    {isItemFail && (
                      <p className="text-[11px] text-rose-700 font-medium">
                        Violation: {item.explanation}
                      </p>
                    )}
                  </div>

                  {/* Verdict Pill */}
                  <span
                    className={`px-2.5 py-1 rounded-lg text-xs font-black uppercase flex-shrink-0 ${
                      isItemPass
                        ? 'bg-emerald-600 text-white'
                        : isItemFail
                        ? 'bg-rose-600 text-white'
                        : 'bg-amber-500 text-white'
                    }`}
                  >
                    {item.status}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
