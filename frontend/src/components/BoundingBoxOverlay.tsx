import React, { useState } from 'react';
import { Layers, Eye, EyeOff } from 'lucide-react';
import type { EvaluationItem } from '../types';

interface BoundingBoxOverlayProps {
  imageUrl: string;
  items: EvaluationItem[];
  highlightedRuleId: string | null;
  onSelectRule: (ruleId: string | null) => void;
}

export const BoundingBoxOverlay: React.FC<BoundingBoxOverlayProps> = ({
  imageUrl,
  items,
  highlightedRuleId,
  onSelectRule,
}) => {
  const [filter, setFilter] = useState<'all' | 'fail' | 'pass' | 'review'>('all');
  const [showBoxes, setShowBoxes] = useState(true);

  // Filter items that have bounding box information
  const itemsWithBoxes = items.filter(
    (i) => i.bounding_box && i.bounding_box.normalized
  );

  const filteredItems = itemsWithBoxes.filter((i) => {
    if (filter === 'fail') return i.status === 'FAIL';
    if (filter === 'pass') return i.status === 'PASS';
    if (filter === 'review') return i.status === 'NEEDS_REVIEW';
    return true;
  });

  const getStatusColor = (status: string, isHighlighted: boolean) => {
    if (status === 'PASS') {
      return {
        border: isHighlighted ? 'border-emerald-500 ring-4 ring-emerald-400/40' : 'border-emerald-500',
        bg: isHighlighted ? 'bg-emerald-500/25' : 'bg-emerald-500/15',
        badge: 'bg-emerald-600 text-white',
      };
    }
    if (status === 'FAIL') {
      return {
        border: isHighlighted ? 'border-rose-600 ring-4 ring-rose-500/40' : 'border-rose-500',
        bg: isHighlighted ? 'bg-rose-500/30' : 'bg-rose-500/20',
        badge: 'bg-rose-600 text-white',
      };
    }
    // NEEDS_REVIEW
    return {
      border: isHighlighted ? 'border-amber-500 ring-4 ring-amber-400/40' : 'border-amber-500',
      bg: isHighlighted ? 'bg-amber-500/25' : 'bg-amber-500/15',
      badge: 'bg-amber-600 text-white',
    };
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-4">
      {/* Controls Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs border-b border-slate-100 pb-3">
        <div className="flex items-center space-x-2">
          <Layers className="w-4 h-4 text-slate-500" />
          <span className="font-bold text-slate-800">Visual Detection Overlay</span>
          <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 text-[11px] font-semibold">
            {filteredItems.length} regions
          </span>
        </div>

        <div className="flex items-center space-x-2">
          {/* Status Filter */}
          <div className="flex items-center bg-slate-100 p-0.5 rounded-lg text-[11px] font-medium text-slate-600">
            <button
              onClick={() => setFilter('all')}
              className={`px-2 py-1 rounded-md transition-all ${filter === 'all' ? 'bg-white text-slate-900 font-semibold shadow-xs' : 'hover:text-slate-900'}`}
            >
              All
            </button>
            <button
              onClick={() => setFilter('fail')}
              className={`px-2 py-1 rounded-md transition-all ${filter === 'fail' ? 'bg-rose-100 text-rose-800 font-semibold shadow-xs' : 'hover:text-rose-700'}`}
            >
              Violations
            </button>
            <button
              onClick={() => setFilter('review')}
              className={`px-2 py-1 rounded-md transition-all ${filter === 'review' ? 'bg-amber-100 text-amber-800 font-semibold shadow-xs' : 'hover:text-amber-700'}`}
            >
              Needs Review
            </button>
            <button
              onClick={() => setFilter('pass')}
              className={`px-2 py-1 rounded-md transition-all ${filter === 'pass' ? 'bg-emerald-100 text-emerald-800 font-semibold shadow-xs' : 'hover:text-emerald-700'}`}
            >
              Passed
            </button>
          </div>

          {/* Toggle Visibility */}
          <button
            onClick={() => setShowBoxes(!showBoxes)}
            className="p-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
            title={showBoxes ? 'Hide Bounding Boxes' : 'Show Bounding Boxes'}
          >
            {showBoxes ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4 text-slate-400" />}
          </button>
        </div>
      </div>

      {/* Image with Bounding Boxes */}
      <div className="relative rounded-xl border border-slate-200 overflow-hidden bg-slate-900/5 flex items-center justify-center min-h-[350px]">
        <img
          src={imageUrl}
          alt="Label with Bounding Boxes"
          className="w-full h-auto max-h-[560px] object-contain select-none block"
        />

        {showBoxes && (
          <div className="absolute inset-0 pointer-events-none">
            {filteredItems.map((item) => {
              const box = item.bounding_box!.normalized;
              const isHighlighted = highlightedRuleId === item.rule_id;
              const colors = getStatusColor(item.status, isHighlighted);

              return (
                <div
                  key={item.rule_id}
                  onClick={() => onSelectRule(item.rule_id)}
                  onMouseEnter={() => onSelectRule(item.rule_id)}
                  className={`absolute border-2 rounded-md pointer-events-auto cursor-pointer transition-all duration-150 ${colors.border} ${colors.bg}`}
                  style={{
                    top: `${box.top}%`,
                    left: `${box.left}%`,
                    width: `${Math.max(box.width, 3)}%`,
                    height: `${Math.max(box.height, 2)}%`,
                    zIndex: isHighlighted ? 30 : 10,
                  }}
                >
                  {/* Tag label */}
                  <span
                    className={`absolute -top-5 left-0 px-1.5 py-0.2 rounded text-[10px] font-bold tracking-tight shadow-xs whitespace-nowrap ${colors.badge}`}
                  >
                    {item.title}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Interactive Legend */}
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500 pt-1">
        <div className="flex items-center space-x-4">
          <span className="flex items-center space-x-1.5">
            <span className="w-3 h-3 rounded-sm bg-emerald-500 inline-block"></span>
            <span className="text-slate-700 font-medium">Passed (Compliant)</span>
          </span>
          <span className="flex items-center space-x-1.5">
            <span className="w-3 h-3 rounded-sm bg-rose-500 inline-block"></span>
            <span className="text-slate-700 font-medium">Violation (Non-Compliant)</span>
          </span>
          <span className="flex items-center space-x-1.5">
            <span className="w-3 h-3 rounded-sm bg-amber-500 inline-block"></span>
            <span className="text-slate-700 font-medium">Needs Review (Low Confidence)</span>
          </span>
        </div>
        <span className="text-[11px] text-slate-400 italic">Click any region to inspect rule details</span>
      </div>
    </div>
  );
};
