import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Navbar } from './components/Navbar';
import { ImageUploader } from './components/ImageUploader';
import { PreprocessingPreview } from './components/PreprocessingPreview';
import { ScoreBadge } from './components/ScoreBadge';
import { BoundingBoxOverlay } from './components/BoundingBoxOverlay';
import { ViolationsList } from './components/ViolationsList';
import { HistoryDashboard } from './components/HistoryDashboard';
import { LegalGuideModal } from './components/LegalGuideModal';
import type { PreprocessingData, VerificationResult, SampleLabel } from './types';
import { AlertCircle, ArrowLeft } from 'lucide-react';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'verifier' | 'history' | 'guide'>('verifier');
  const [step, setStep] = useState<'upload' | 'preview' | 'results'>('upload');
  
  const [samples, setSamples] = useState<SampleLabel[]>([]);
  const [preprocessingData, setPreprocessingData] = useState<PreprocessingData | null>(null);
  const [verificationResult, setVerificationResult] = useState<VerificationResult | null>(null);
  
  const [highlightedRuleId, setHighlightedRuleId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [isDownloadingPdf, setIsDownloadingPdf] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [totalAudits, setTotalAudits] = useState(0);

  // Fetch sample labels and initial audit count
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        const [samplesRes, historyRes] = await Promise.all([
          axios.get('/api/samples'),
          axios.get('/api/verifications'),
        ]);
        setSamples(samplesRes.data.samples || []);
        setTotalAudits((historyRes.data.verifications || []).length);
      } catch (err) {
        console.error('Error loading initial data:', err);
      }
    };
    loadInitialData();
  }, []);

  // Step 1: Upload / select sample and trigger OpenCV preprocessing
  const handleFileSelect = async (file: File) => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const resp = await axios.post<PreprocessingData>('/api/preprocess', formData);
      setPreprocessingData(resp.data);
      setStep('preview');
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Failed to upload and preprocess image.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSampleSelect = async (sampleId: string) => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const formData = new FormData();
      formData.append('sample_id', sampleId);
      const resp = await axios.post<PreprocessingData>('/api/preprocess', formData);
      setPreprocessingData(resp.data);
      setStep('preview');
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Failed to load sample label.');
    } finally {
      setIsLoading(false);
    }
  };

  // Step 2: Trigger OCR extraction and rule compliance evaluation
  const handleVerify = async () => {
    if (!preprocessingData) return;
    setIsVerifying(true);
    setErrorMessage(null);
    try {
      const formData = new FormData();
      formData.append('file_id', preprocessingData.file_id);
      const resp = await axios.post<VerificationResult>('/api/verify', formData);
      
      if (resp.data.error_message && resp.data.evaluation_results.length === 0) {
        setErrorMessage(resp.data.error_message);
      } else {
        setVerificationResult(resp.data);
        setStep('results');
        setTotalAudits((prev) => prev + 1);
      }
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Verification analysis failed.');
    } finally {
      setIsVerifying(false);
    }
  };

  const handleReset = () => {
    setStep('upload');
    setPreprocessingData(null);
    setVerificationResult(null);
    setHighlightedRuleId(null);
    setErrorMessage(null);
  };

  // Download PDF Report
  const handleDownloadReport = () => {
    if (!verificationResult?.id) return;
    setIsDownloadingPdf(true);
    const downloadUrl = `/api/verifications/${verificationResult.id}/pdf`;
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.setAttribute('download', `LabelCheck_Report_${verificationResult.id}.pdf`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(() => setIsDownloadingPdf(false), 1500);
  };

  // Inspect previous audit from History
  const handleInspectAudit = async (id: string) => {
    setIsLoading(true);
    try {
      const resp = await axios.get<VerificationResult>(`/api/verifications/${id}`);
      setVerificationResult(resp.data);
      setActiveTab('verifier');
      setStep('results');
    } catch (err) {
      console.error('Failed to load audit detail:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Top Navigation */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={(tab) => {
          setActiveTab(tab);
          setErrorMessage(null);
        }}
        totalAuditsCount={totalAudits}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Error Notification */}
        {errorMessage && (
          <div className="mb-6 p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-start space-x-3 shadow-xs">
            <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <span className="font-bold block">Analysis Notice:</span>
              <p>{errorMessage}</p>
            </div>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-rose-500 hover:text-rose-700 text-xs font-bold"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* TAB 1: VERIFIER */}
        {activeTab === 'verifier' && (
          <div className="space-y-6">
            {/* Step 1: Upload */}
            {step === 'upload' && (
              <div className="space-y-6">
                <div className="text-center max-w-2xl mx-auto space-y-2 mb-8">
                  <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
                    Verify Product Labels for Legal Metrology Compliance
                  </h1>
                  <p className="text-sm text-slate-600 leading-relaxed">
                    Upload a packaged commodity label to verify mandatory declarations against India's
                    Legal Metrology (Packaged Commodities) Rules, 2011 with OpenCV preprocessing and OCR extraction.
                  </p>
                </div>

                <ImageUploader
                  onFileSelect={handleFileSelect}
                  onSampleSelect={handleSampleSelect}
                  samples={samples}
                  isLoading={isLoading}
                />
              </div>
            )}

            {/* Step 2: OpenCV Preprocessing Preview */}
            {step === 'preview' && preprocessingData && (
              <div className="space-y-6">
                <PreprocessingPreview
                  data={preprocessingData}
                  onVerify={handleVerify}
                  onReset={handleReset}
                  isVerifying={isVerifying}
                />
              </div>
            )}

            {/* Step 3: Verification Results & Interactive Overlays */}
            {step === 'results' && verificationResult && (
              <div className="space-y-6">
                {/* Back / Reset Bar */}
                <div className="flex items-center justify-between">
                  <button
                    onClick={handleReset}
                    className="inline-flex items-center space-x-2 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-white border border-slate-200 hover:bg-slate-50 px-3 py-1.5 rounded-lg transition-colors shadow-2xs"
                  >
                    <ArrowLeft className="w-3.5 h-3.5" />
                    <span>Check Another Label</span>
                  </button>

                  <span className="text-xs font-mono text-slate-400">
                    File: <span className="text-slate-700 font-semibold">{verificationResult.filename}</span>
                  </span>
                </div>

                {/* Score Banner */}
                <ScoreBadge
                  score={verificationResult.overall_score}
                  status={verificationResult.compliance_status}
                  totalPassed={verificationResult.total_passed}
                  totalFailed={verificationResult.total_failed}
                  totalNeedsReview={verificationResult.total_needs_review}
                  onDownloadReport={handleDownloadReport}
                  isDownloading={isDownloadingPdf}
                />

                {/* Grid: Visual Bounding Boxes (Left) + Rule List (Right) */}
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
                  {/* Left Column: Image with Bounding Box Overlay (5 cols) */}
                  <div className="lg:col-span-6 sticky top-20">
                    <BoundingBoxOverlay
                      imageUrl={verificationResult.preprocessed_image_url || verificationResult.raw_image_url}
                      items={verificationResult.evaluation_results}
                      highlightedRuleId={highlightedRuleId}
                      onSelectRule={setHighlightedRuleId}
                    />
                  </div>

                  {/* Right Column: Detailed Rules Breakdown (7 cols) */}
                  <div className="lg:col-span-6">
                    <ViolationsList
                      items={verificationResult.evaluation_results}
                      highlightedRuleId={highlightedRuleId}
                      onSelectRule={setHighlightedRuleId}
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: AUDIT HISTORY */}
        {activeTab === 'history' && (
          <HistoryDashboard onInspect={handleInspectAudit} />
        )}

        {/* TAB 3: LEGAL METROLOGY GUIDE */}
        {activeTab === 'guide' && (
          <LegalGuideModal />
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-6 text-center text-xs text-slate-400">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>
            <b>LabelCheck</b> &bull; India Legal Metrology (Packaged Commodities) Rules, 2011 Compliance Verification
          </span>
          <span>FastAPI &bull; OpenCV &bull; Tesseract OCR &bull; ReportLab &bull; React + Tailwind</span>
        </div>
      </footer>
    </div>
  );
};

export default App;
