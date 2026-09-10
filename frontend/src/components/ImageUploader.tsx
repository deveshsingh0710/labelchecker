import React, { useState, useRef } from 'react';
import { UploadCloud, CheckCircle, AlertTriangle, Globe, ArrowRight, Loader2 } from 'lucide-react';
import type { SampleLabel } from '../types';

interface ImageUploaderProps {
  onFileSelect: (file: File) => void;
  onSampleSelect: (sampleId: string) => void;
  samples: SampleLabel[];
  isLoading: boolean;
}

export const ImageUploader: React.FC<ImageUploaderProps> = ({
  onFileSelect,
  onSampleSelect,
  samples: _samples,
  isLoading,
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      onFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      onFileSelect(e.target.files[0]);
    }
  };

  return (
    <div className="w-full space-y-8">
      {/* Upload Box */}
      <div
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`relative border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center cursor-pointer transition-all duration-200 ${
          isDragOver
            ? 'border-sky-500 bg-sky-50/70 scale-[1.005]'
            : 'border-slate-300 hover:border-sky-400 bg-white hover:bg-slate-50/50 shadow-xs'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp,image/bmp,image/heic"
          className="hidden"
          onChange={handleFileInputChange}
          disabled={isLoading}
        />

        <div className="flex flex-col items-center justify-center space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-sky-100 text-sky-600 flex items-center justify-center shadow-inner">
            {isLoading ? (
              <Loader2 className="w-8 h-8 animate-spin text-sky-600" />
            ) : (
              <UploadCloud className="w-8 h-8" />
            )}
          </div>

          <div className="space-y-1">
            <h3 className="text-lg font-semibold text-slate-800">
              {isLoading ? 'Processing Label Image...' : 'Drop your product package label here'}
            </h3>
            <p className="text-sm text-slate-500">
              Drag & drop or <span className="text-sky-600 font-medium hover:underline">browse files</span>
            </p>
          </div>

          <div className="flex items-center space-x-2 text-xs text-slate-400 pt-2">
            <span className="px-2 py-0.5 rounded-md bg-slate-100 border border-slate-200">JPG</span>
            <span className="px-2 py-0.5 rounded-md bg-slate-100 border border-slate-200">PNG</span>
            <span className="px-2 py-0.5 rounded-md bg-slate-100 border border-slate-200">WebP</span>
            <span className="px-2 py-0.5 rounded-md bg-slate-100 border border-slate-200">HEIC</span>
            <span>&bull; Up to 15MB</span>
          </div>
        </div>
      </div>

      {/* Preset Demo Samples */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold text-slate-700 uppercase tracking-wider flex items-center space-x-2">
            <span>Or test with verified sample labels</span>
            <span className="text-xs font-normal text-slate-400 lowercase">(1-click demo)</span>
          </h4>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Sample 1: Compliant */}
          <div
            onClick={() => !isLoading && onSampleSelect('sample_compliant')}
            className="group p-4 bg-white border border-slate-200 hover:border-emerald-500 rounded-xl shadow-xs hover:shadow-md transition-all cursor-pointer flex flex-col justify-between"
          >
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  <CheckCircle className="w-3 h-3" />
                  <span>100% Compliant</span>
                </span>
                <span className="text-xs text-slate-400">Food Item</span>
              </div>
              <h5 className="font-semibold text-slate-900 group-hover:text-emerald-700 transition-colors text-sm">
                Organic Roasted Almonds
              </h5>
              <p className="text-xs text-slate-500 leading-relaxed">
                Contains complete mandatory declarations: Net Qty in grams, MRP incl. taxes, Mfg date, and active Consumer Care.
              </p>
            </div>
            <div className="pt-3 mt-2 border-t border-slate-100 flex items-center justify-between text-xs font-medium text-emerald-600">
              <span>Test Compliant Label</span>
              <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
            </div>
          </div>

          {/* Sample 2: Violations */}
          <div
            onClick={() => !isLoading && onSampleSelect('sample_violations')}
            className="group p-4 bg-white border border-slate-200 hover:border-rose-500 rounded-xl shadow-xs hover:shadow-md transition-all cursor-pointer flex flex-col justify-between"
          >
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
                  <AlertTriangle className="w-3 h-3" />
                  <span>Critical Violations</span>
                </span>
                <span className="text-xs text-slate-400">Confectionery</span>
              </div>
              <h5 className="font-semibold text-slate-900 group-hover:text-rose-700 transition-colors text-sm">
                Choco Crunch Cookies
              </h5>
              <p className="text-xs text-slate-500 leading-relaxed">
                Contains multiple infractions: non-standard unit 'gms', missing 'inclusive of all taxes', and missing customer care.
              </p>
            </div>
            <div className="pt-3 mt-2 border-t border-slate-100 flex items-center justify-between text-xs font-medium text-rose-600">
              <span>Test Violations Label</span>
              <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
            </div>
          </div>

          {/* Sample 3: Imported */}
          <div
            onClick={() => !isLoading && onSampleSelect('sample_imported')}
            className="group p-4 bg-white border border-slate-200 hover:border-sky-500 rounded-xl shadow-xs hover:shadow-md transition-all cursor-pointer flex flex-col justify-between"
          >
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-sky-50 text-sky-700 border border-sky-200">
                  <Globe className="w-3 h-3" />
                  <span>Imported Product</span>
                </span>
                <span className="text-xs text-slate-400">Import</span>
              </div>
              <h5 className="font-semibold text-slate-900 group-hover:text-sky-700 transition-colors text-sm">
                Swiss Dark Chocolate 85%
              </h5>
              <p className="text-xs text-slate-500 leading-relaxed">
                Tests Rule 6(1)(n) imported declarations including Country of Origin (Switzerland) and registered Importer address.
              </p>
            </div>
            <div className="pt-3 mt-2 border-t border-slate-100 flex items-center justify-between text-xs font-medium text-sky-600">
              <span>Test Imported Label</span>
              <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
