import React from 'react';
import { AlertCircle, CheckCircle2, HelpCircle, FileText } from 'lucide-react';
import type { EvaluationItem } from '../types';

interface ViolationsListProps {
  items: EvaluationItem[];
  highlightedRuleId: string | null;
  onSelectRule: (ruleId: string | null) => void;
}

export const ViolationsList: React.FC<ViolationsListProps> = ({
  items,
  highlightedRuleId,
  onSelectRule,
}) => {
  // Sort order: FAIL first, then NEEDS_REVIEW, then PASS
  const sortedItems = [...items].sort((a, b) => {
    const order: Record<string, number> = { FAIL: 1, NEEDS_REVIEW: 2, PASS: 3 };
    return (order[a.status] || 4) - (order[b.status] || 4);
  });

  const getSeverityBadge = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return 'bg-rose-100 text-rose-800 border-rose-200';
      case 'major':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'PASS':
        return <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />;
      case 'FAIL':
        return <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0" />;
      default:
        return <HelpCircle className="w-5 h-5 text-amber-600 flex-shrink-0" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'PASS':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'FAIL':
        return 'bg-rose-50 text-rose-700 border-rose-200';
      default:
        return 'bg-amber-50 text-amber-700 border-amber-200';
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
      <div className="flex items-center justify-between border-b border-slate-100 pb-4">
        <div>
          <h3 className="text-base font-bold text-slate-900 flex items-center space-x-2">
            <FileText className="w-4 h-4 text-sky-600" />
            <span>Detailed Rule-by-Rule Compliance Checklist</span>
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Evaluated against the statutory requirements of Legal Metrology (Packaged Commodities) Rules, 2011.
          </p>
        </div>
        <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
          {items.length} Rules Checked
        </span>
      </div>

      {/* Rules Accordion / Cards List */}
      <div className="space-y-3">
        {sortedItems.map((item) => {
          const isHighlighted = highlightedRuleId === item.rule_id;

          return (
            <div
              key={item.rule_id}
              onClick={() => onSelectRule(item.rule_id)}
              onMouseEnter={() => onSelectRule(item.rule_id)}
              className={`p-4 rounded-xl border transition-all cursor-pointer ${
                isHighlighted
                  ? 'border-sky-500 bg-sky-50/40 ring-2 ring-sky-400/20 shadow-xs'
                  : item.status === 'FAIL'
                  ? 'border-rose-200 bg-rose-50/20 hover:border-rose-300'
                  : item.status === 'NEEDS_REVIEW'
                  ? 'border-amber-200 bg-amber-50/20 hover:border-amber-300'
                  : 'border-slate-200 bg-white hover:border-slate-300'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start space-x-3">
                  <div className="pt-0.5">{getStatusIcon(item.status)}</div>
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-bold text-slate-900 text-sm">{item.title}</span>
                      <span className={`px-2 py-0.2 rounded-full text-[10px] font-bold uppercase tracking-wider border ${getStatusBadge(item.status)}`}>
                        {item.status.replace('_', ' ')}
                      </span>
                      <span className={`px-2 py-0.2 rounded-full text-[10px] font-semibold uppercase border ${getSeverityBadge(item.severity)}`}>
                        {item.severity}
                      </span>
                    </div>

                    <p className="text-xs font-medium text-slate-500">
                      Legal Reference: <span className="text-slate-700 font-semibold">{item.legal_reference}</span>
                    </p>

                    <p className="text-xs text-slate-700 leading-relaxed pt-1">
                      {item.explanation}
                    </p>

                    {item.status !== 'PASS' && item.remediation && (
                      <div className="mt-2 p-2.5 rounded-lg bg-slate-50 border border-slate-200/80 text-xs text-slate-600">
                        <span className="font-bold text-slate-700 block mb-0.5">Required Remediation:</span>
                        {item.remediation}
                      </div>
                    )}
                  </div>
                </div>

                {/* Extracted Value & Confidence Pill */}
                <div className="flex flex-col items-end text-right flex-shrink-0 pl-2">
                  <span className="text-[11px] font-medium text-slate-400">Extracted</span>
                  <span className="text-xs font-semibold text-slate-800 max-w-[140px] truncate">
                    {item.extracted_value || <span className="text-slate-400 italic">None</span>}
                  </span>
                  {item.ocr_confidence > 0 && (
                    <span className="text-[10px] text-slate-500 mt-1 font-mono">
                      Conf: {Math.round(item.ocr_confidence)}%
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
