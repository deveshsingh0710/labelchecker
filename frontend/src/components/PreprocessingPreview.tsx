import React, { useState } from 'react';
import { Sparkles, CheckCircle2, RotateCcw, ArrowRight } from 'lucide-react';
import type { PreprocessingData } from '../types';
import { getAssetUrl } from '../config';

interface PreprocessingPreviewProps {
  data: PreprocessingData;
  onVerify: () => void;
  onReset: () => void;
  isVerifying: boolean;
}

export const PreprocessingPreview: React.FC<PreprocessingPreviewProps> = ({
  data,
  onVerify,
  onReset,
  isVerifying,
}) => {
  const [activeView, setActiveView] = useState<'preprocessed' | 'raw' | 'split'>('preprocessed');

  return (
    <div className="w-full bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 shadow-sm space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-5">
        <div>
          <div className="flex items-center space-x-2">
            <span className="p-1.5 rounded-lg bg-sky-100 text-sky-700">
              <Sparkles className="w-4 h-4" />
            </span>
            <h3 className="text-lg font-bold text-slate-900">Step 1: OpenCV Preprocessing Complete</h3>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Optimized image for optical character recognition via adaptive thresholding, glare balancing, and deskewing.
          </p>
        </div>

        {/* View Switcher */}
        <div className="flex items-center bg-slate-100 p-1 rounded-xl text-xs font-semibold text-slate-600 self-start sm:self-auto">
          <button
            onClick={() => setActiveView('preprocessed')}
            className={`px-3 py-1.5 rounded-lg transition-all ${
              activeView === 'preprocessed' ? 'bg-white text-sky-700 shadow-xs' : 'hover:text-slate-900'
            }`}
          >
            Preprocessed (Optimized)
          </button>
          <button
            onClick={() => setActiveView('raw')}
            className={`px-3 py-1.5 rounded-lg transition-all ${
              activeView === 'raw' ? 'bg-white text-slate-900 shadow-xs' : 'hover:text-slate-900'
            }`}
          >
            Original Upload
          </button>
          <button
            onClick={() => setActiveView('split')}
            className={`px-3 py-1.5 rounded-lg transition-all ${
              activeView === 'split' ? 'bg-white text-slate-900 shadow-xs' : 'hover:text-slate-900'
            }`}
          >
            Side-by-Side
          </button>
        </div>
      </div>

      {/* Image Preview Container */}
      <div className="relative bg-slate-900/5 rounded-xl border border-slate-200 overflow-hidden flex items-center justify-center min-h-[340px] max-h-[500px]">
        {activeView === 'split' ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 w-full h-full divide-y sm:divide-y-0 sm:divide-x divide-slate-200">
            <div className="p-4 flex flex-col items-center justify-center">
              <span className="mb-2 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                Original Image
              </span>
              <img
                src={getAssetUrl(data.raw_image_url)}
                alt="Original Upload"
                className="max-h-[380px] object-contain rounded-lg shadow-sm"
              />
            </div>
            <div className="p-4 flex flex-col items-center justify-center bg-sky-50/20">
              <span className="mb-2 text-[11px] font-semibold text-sky-700 uppercase tracking-wider flex items-center space-x-1">
                <CheckCircle2 className="w-3 h-3 text-sky-600" />
                <span>OpenCV Preprocessed</span>
              </span>
              <img
                src={getAssetUrl(data.preprocessed_image_url)}
                alt="Preprocessed Label"
                className="max-h-[380px] object-contain rounded-lg shadow-sm"
              />
            </div>
          </div>
        ) : (
          <div className="p-4 flex flex-col items-center justify-center w-full">
            <img
              src={getAssetUrl(activeView === 'preprocessed' ? data.preprocessed_image_url : data.raw_image_url)}
              alt="Preview"
              className="max-h-[440px] object-contain rounded-lg shadow-sm"
            />
          </div>
        )}
      </div>

      {/* Preprocessing Diagnostics & Pipeline Details */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-50 p-4 rounded-xl border border-slate-200/80 text-xs">
        <div className="space-y-0.5">
          <span className="text-slate-400 font-medium">Deskew Correction</span>
          <p className="font-semibold text-slate-800">
            {data.deskew_angle === 0 ? '0.0° (Level)' : `${data.deskew_angle > 0 ? '+' : ''}${data.deskew_angle}°`}
          </p>
        </div>
        <div className="space-y-0.5">
          <span className="text-slate-400 font-medium">Glare Equalization</span>
          <p className="font-semibold text-slate-800">CLAHE (LAB Channel)</p>
        </div>
        <div className="space-y-0.5">
          <span className="text-slate-400 font-medium">Denoising</span>
          <p className="font-semibold text-slate-800">Bilateral Filter</p>
        </div>
        <div className="space-y-0.5">
          <span className="text-slate-400 font-medium">Image Resolution</span>
          <p className="font-semibold text-slate-800">
            {data.preprocessed_dimensions[0]} &times; {data.preprocessed_dimensions[1]} px
          </p>
        </div>
      </div>

      {/* Action Footer */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
        <button
          onClick={onReset}
          disabled={isVerifying}
          className="w-full sm:w-auto px-4 py-2.5 rounded-xl border border-slate-300 hover:bg-slate-100 text-slate-700 font-medium text-sm transition-all flex items-center justify-center space-x-2 cursor-pointer"
        >
          <RotateCcw className="w-4 h-4" />
          <span>Upload Another Photo</span>
        </button>

        <button
          onClick={onVerify}
          disabled={isVerifying}
          className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-gradient-to-r from-sky-600 to-indigo-600 hover:from-sky-700 hover:to-indigo-700 text-white font-semibold text-sm shadow-md shadow-sky-200 transition-all flex items-center justify-center space-x-2 cursor-pointer disabled:opacity-60"
        >
          {isVerifying ? (
            <>
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              <span>Running OCR & Rule Engine...</span>
            </>
          ) : (
            <>
              <span>Extract & Verify Legal Metrology Compliance</span>
              <ArrowRight className="w-4 h-4" />
            </>
          )}
        </button>
      </div>
    </div>
  );
};
