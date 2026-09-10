import React from 'react';
import { ShieldCheck, AlertTriangle, XCircle, FileDown } from 'lucide-react';

interface ScoreBadgeProps {
  score: number;
  status: 'COMPLIANT' | 'PARTIALLY_COMPLIANT' | 'NON_COMPLIANT';
  totalPassed: number;
  totalFailed: number;
  totalNeedsReview: number;
  onDownloadReport: () => void;
  isDownloading?: boolean;
}

export const ScoreBadge: React.FC<ScoreBadgeProps> = ({
  score,
  status,
  totalPassed,
  totalFailed,
  totalNeedsReview,
  onDownloadReport,
  isDownloading,
}) => {
  const getStatusConfig = () => {
    if (status === 'COMPLIANT') {
      return {
        bg: 'bg-emerald-50 text-emerald-800 border-emerald-200',
        ring: 'text-emerald-500',
        icon: <ShieldCheck className="w-5 h-5 text-emerald-600" />,
        label: 'Fully Compliant',
        thresholdNote: 'Meets mandatory Legal Metrology declarations (≥ 85%)',
      };
    }
    if (status === 'PARTIALLY_COMPLIANT') {
      return {
        bg: 'bg-amber-50 text-amber-800 border-amber-200',
        ring: 'text-amber-500',
        icon: <AlertTriangle className="w-5 h-5 text-amber-600" />,
        label: 'Partially Compliant',
        thresholdNote: 'Minor formatting issues or conditional requirements require review (60–84%)',
      };
    }
    return {
      bg: 'bg-rose-50 text-rose-800 border-rose-200',
      ring: 'text-rose-500',
      icon: <XCircle className="w-5 h-5 text-rose-600" />,
      label: 'Non-Compliant',
      thresholdNote: 'Critical mandatory declarations missing or incorrect (< 60%)',
    };
  };

  const config = getStatusConfig();
  const circumference = 2 * Math.PI * 38;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-6">
      {/* Left: Circular Score Gauge & Status */}
      <div className="flex items-center space-x-5">
        {/* SVG Circular Gauge */}
        <div className="relative w-24 h-24 flex-shrink-0 flex items-center justify-center">
          <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
            <circle
              cx="50"
              cy="50"
              r="38"
              className="text-slate-100"
              strokeWidth="8"
              stroke="currentColor"
              fill="transparent"
            />
            <circle
              cx="50"
              cy="50"
              r="38"
              className={`${config.ring} transition-all duration-1000 ease-out`}
              strokeWidth="8"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
              stroke="currentColor"
              fill="transparent"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
            <span className="text-2xl font-black tracking-tight text-slate-900">{score}%</span>
            <span className="text-[10px] font-semibold text-slate-400 uppercase -mt-1">Score</span>
          </div>
        </div>

        {/* Status Text & Rule Reference */}
        <div className="space-y-1.5">
          <div className="flex items-center space-x-2">
            <span className={`inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-bold border ${config.bg}`}>
              {config.icon}
              <span>{config.label}</span>
            </span>
          </div>
          <h3 className="text-base font-bold text-slate-900">Legal Metrology Rules, 2011 Verification</h3>
          <p className="text-xs text-slate-500 max-w-md">{config.thresholdNote}</p>
        </div>
      </div>

      {/* Right: Metrics & Download Button */}
      <div className="flex flex-col sm:flex-row items-center gap-4 w-full sm:w-auto">
        {/* Breakdown Counts */}
        <div className="grid grid-cols-3 gap-2 text-center bg-slate-50 p-2 rounded-xl border border-slate-200/80 text-xs w-full sm:w-auto">
          <div className="px-3 py-1">
            <span className="text-emerald-700 font-bold text-base block">{totalPassed}</span>
            <span className="text-slate-500 text-[10px] font-medium">Passed</span>
          </div>
          <div className="px-3 py-1 border-x border-slate-200">
            <span className="text-rose-700 font-bold text-base block">{totalFailed}</span>
            <span className="text-slate-500 text-[10px] font-medium">Violations</span>
          </div>
          <div className="px-3 py-1">
            <span className="text-amber-700 font-bold text-base block">{totalNeedsReview}</span>
            <span className="text-slate-500 text-[10px] font-medium">Review</span>
          </div>
        </div>

        {/* Download PDF Button */}
        <button
          onClick={onDownloadReport}
          disabled={isDownloading}
          className="w-full sm:w-auto px-5 py-3 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-semibold text-sm shadow-sm transition-all flex items-center justify-center space-x-2 cursor-pointer disabled:opacity-50"
        >
          {isDownloading ? (
            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          ) : (
            <FileDown className="w-4 h-4 text-sky-400" />
          )}
          <span>Download PDF Audit</span>
        </button>
      </div>
    </div>
  );
};
