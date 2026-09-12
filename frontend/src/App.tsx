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
import { PricingPage } from './components/PricingPage';
import { InspectorView } from './components/InspectorView';
import { DemoRequestModal } from './components/DemoRequestModal';
import { AuthModal } from './components/AuthModal';
import type { PreprocessingData, VerificationResult, SampleLabel, Organization, User } from './types';
import { AlertCircle, ArrowLeft, Briefcase, Eye, Sparkles } from 'lucide-react';
import { API_BASE_URL, getAssetUrl } from './config';

// Set global base URL for Axios in production
if (API_BASE_URL) {
  axios.defaults.baseURL = API_BASE_URL;
}

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'verifier' | 'analytics' | 'pricing' | 'guide'>('verifier');
  const [step, setStep] = useState<'upload' | 'preview' | 'results'>('upload');
  const [roleView, setRoleView] = useState<'business' | 'inspector'>('business');

  const [samples, setSamples] = useState<SampleLabel[]>([]);
  const [preprocessingData, setPreprocessingData] = useState<PreprocessingData | null>(null);
  const [verificationResult, setVerificationResult] = useState<VerificationResult | null>(null);

  // Multi-tenant Organization & Auth state
  const [demoOrgs, setDemoOrgs] = useState<Organization[]>([]);
  const [currentOrg, setCurrentOrg] = useState<Organization | null>(null);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [isDemoModalOpen, setIsDemoModalOpen] = useState(false);
  const [demoPrefillType, setDemoPrefillType] = useState<string>('brand');

  const [highlightedRuleId, setHighlightedRuleId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [isDownloadingPdf, setIsDownloadingPdf] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [totalAudits, setTotalAudits] = useState(0);

  // Initial Load: Organizations, Samples, Audit Count
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        const [samplesRes, orgsRes] = await Promise.all([
          axios.get('/api/samples'),
          axios.get('/api/organizations/demo'),
        ]);

        setSamples(samplesRes.data.samples || []);
        const loadedOrgs: Organization[] = orgsRes.data.organizations || [];
        setDemoOrgs(loadedOrgs);

        // Check localStorage or default to primary brand demo org
        const savedOrgId = localStorage.getItem('labelcheck_org_id');
        const matchedOrg = loadedOrgs.find((o) => o.id === savedOrgId) || loadedOrgs[0] || null;
        if (matchedOrg) {
          setCurrentOrg(matchedOrg);
          setCurrentUser(matchedOrg.default_user || null);
          axios.defaults.headers.common['X-Organization-Id'] = matchedOrg.id;
        }

        // Load audit count for selected org
        const historyRes = await axios.get('/api/verifications', {
          headers: matchedOrg ? { 'X-Organization-Id': matchedOrg.id } : {}
        });
        setTotalAudits((historyRes.data.verifications || []).length);
      } catch (err) {
        console.error('Error loading initial data:', err);
      }
    };
    loadInitialData();
  }, []);

  // Update Axios headers when organization changes
  const handleSelectOrg = (org: Organization, user?: User, token?: string) => {
    setCurrentOrg(org);
    if (user) setCurrentUser(user);
    localStorage.setItem('labelcheck_org_id', org.id);
    if (token) localStorage.setItem('labelcheck_token', token);
    axios.defaults.headers.common['X-Organization-Id'] = org.id;

    // Refresh audit count for this organization
    axios.get('/api/verifications', { headers: { 'X-Organization-Id': org.id } })
      .then((res) => setTotalAudits((res.data.verifications || []).length))
      .catch(() => {});
  };

  // Step 1: Upload / select sample and trigger OpenCV preprocessing
  const handleFileSelect = async (file: File) => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      if (currentOrg) formData.append('organization_id', currentOrg.id);
      const resp = await axios.post<PreprocessingData>('/api/preprocess', formData);
      setPreprocessingData(resp.data);
      setStep('preview');
    } catch (err: any) {
      console.error('Preprocessing failed:', err);
      const serverDetail = err.response?.data?.detail;
      const statusText = err.response?.status ? `HTTP ${err.response.status} ${err.response.statusText || ''}`.trim() : null;
      const netMsg = err.message ? `${err.message}${!API_BASE_URL ? ' (VITE_API_BASE_URL is not configured)' : ` (connected to ${API_BASE_URL})`}` : null;
      setErrorMessage(serverDetail || statusText || netMsg || 'Failed to upload and preprocess image.');
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
      if (currentOrg) formData.append('organization_id', currentOrg.id);
      const resp = await axios.post<PreprocessingData>('/api/preprocess', formData);
      setPreprocessingData(resp.data);
      setStep('preview');
    } catch (err: any) {
      console.error('Sample loading failed:', err);
      const serverDetail = err.response?.data?.detail;
      const statusText = err.response?.status ? `HTTP ${err.response.status} ${err.response.statusText || ''}`.trim() : null;
      const netMsg = err.message ? `${err.message}${!API_BASE_URL ? ' (VITE_API_BASE_URL is not configured)' : ` (connected to ${API_BASE_URL})`}` : null;
      setErrorMessage(serverDetail || statusText || netMsg || 'Failed to load sample label.');
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
      if (currentOrg) formData.append('organization_id', currentOrg.id);
      const resp = await axios.post<VerificationResult>('/api/verify', formData, {
        headers: currentOrg ? { 'X-Organization-Id': currentOrg.id } : {}
      });

      if (resp.data.error_message && resp.data.evaluation_results.length === 0) {
        setErrorMessage(resp.data.error_message);
      } else {
        setVerificationResult(resp.data);
        setStep('results');
        setTotalAudits((prev) => prev + 1);
      }
    } catch (err: any) {
      console.error('Verification analysis failed:', err);
      const serverDetail = err.response?.data?.detail;
      const statusText = err.response?.status ? `HTTP ${err.response.status} ${err.response.statusText || ''}`.trim() : null;
      const netMsg = err.message ? `${err.message}${!API_BASE_URL ? ' (VITE_API_BASE_URL is not configured)' : ` (connected to ${API_BASE_URL})`}` : null;
      setErrorMessage(serverDetail || statusText || netMsg || 'Verification analysis failed.');
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
    const downloadUrl = getAssetUrl(`/api/verifications/${verificationResult.id}/pdf`);
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
        activeOrg={currentOrg}
        currentUser={currentUser}
        onOpenOrgModal={() => setIsAuthModalOpen(true)}
        onOpenDemoModal={() => {
          setDemoPrefillType(currentOrg?.type || 'brand');
          setIsDemoModalOpen(true);
        }}
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
              className="text-rose-500 hover:text-rose-700 text-xs font-bold cursor-pointer"
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
                  <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-sky-50 border border-sky-200 text-sky-700 text-xs font-semibold mb-1">
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>India Legal Metrology (Packaged Commodities) Rules, 2011</span>
                  </div>
                  <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
                    Verify Product Labels Before Printing or Dispatch
                  </h1>
                  <p className="text-sm text-slate-600 leading-relaxed">
                    Upload a packaged commodity label to verify mandatory statutory declarations (MRP, Net Quantity, Expiry, Manufacturer) with OpenCV preprocessing and Tesseract OCR.
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

            {/* Step 3: Verification Results with Role-Based View Toggle */}
            {step === 'results' && verificationResult && (
              <div className="space-y-6">
                {/* Control Bar: Back Button + Role-Based View Toggle (Business vs Inspector) */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-3 rounded-2xl border border-slate-200 shadow-2xs">
                  <button
                    onClick={handleReset}
                    className="inline-flex items-center space-x-2 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-slate-50 hover:bg-slate-100 border border-slate-200 px-3 py-1.5 rounded-xl transition-colors cursor-pointer"
                  >
                    <ArrowLeft className="w-3.5 h-3.5" />
                    <span>Check Another Label</span>
                  </button>

                  {/* Role-Based View Toggle */}
                  <div className="flex items-center space-x-2 bg-slate-100 p-1 rounded-xl text-xs font-bold">
                    <button
                      onClick={() => setRoleView('business')}
                      className={`px-3 py-1.5 rounded-lg transition-all flex items-center space-x-1.5 cursor-pointer ${
                        roleView === 'business'
                          ? 'bg-white text-slate-900 shadow-xs'
                          : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      <Briefcase className="w-3.5 h-3.5 text-sky-600" />
                      <span>Business View</span>
                    </button>

                    <button
                      onClick={() => setRoleView('inspector')}
                      className={`px-3 py-1.5 rounded-lg transition-all flex items-center space-x-1.5 cursor-pointer ${
                        roleView === 'inspector'
                          ? 'bg-white text-slate-900 shadow-xs'
                          : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      <Eye className="w-3.5 h-3.5 text-indigo-600" />
                      <span>Inspector Field View</span>
                    </button>
                  </div>

                  <span className="text-xs font-mono text-slate-400 hidden lg:inline">
                    File: <span className="text-slate-700 font-semibold">{verificationResult.filename}</span>
                  </span>
                </div>

                {/* VIEW 1: Business View (Interactive Overlays + Checklist) */}
                {roleView === 'business' && (
                  <div className="space-y-6">
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
                      {/* Left Column: Image with Bounding Box Overlay */}
                      <div className="lg:col-span-6 sticky top-20">
                        <BoundingBoxOverlay
                          imageUrl={getAssetUrl(verificationResult.preprocessed_image_url || verificationResult.raw_image_url)}
                          items={verificationResult.evaluation_results}
                          highlightedRuleId={highlightedRuleId}
                          onSelectRule={setHighlightedRuleId}
                        />
                      </div>

                      {/* Right Column: Detailed Rules Breakdown */}
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

                {/* VIEW 2: Inspector Field View (High-Impact Verdict + Touch Actions) */}
                {roleView === 'inspector' && (
                  <InspectorView
                    result={verificationResult}
                    onReset={handleReset}
                    onDownloadReport={handleDownloadReport}
                    isDownloading={isDownloadingPdf}
                  />
                )}
              </div>
            )}
          </div>
        )}

        {/* TAB 2: ANALYTICS & AUDIT HISTORY */}
        {activeTab === 'analytics' && (
          <HistoryDashboard
            onInspect={handleInspectAudit}
            activeOrg={currentOrg}
          />
        )}

        {/* TAB 3: PRICING */}
        {activeTab === 'pricing' && (
          <PricingPage
            onRequestDemo={(type) => {
              setDemoPrefillType(type || 'brand');
              setIsDemoModalOpen(true);
            }}
            onSelectStarter={() => {
              setActiveTab('verifier');
              setStep('upload');
            }}
          />
        )}

        {/* TAB 4: LEGAL RULES GUIDE */}
        {activeTab === 'guide' && (
          <LegalGuideModal />
        )}
      </main>

      {/* Shared Modals */}
      <DemoRequestModal
        isOpen={isDemoModalOpen}
        onClose={() => setIsDemoModalOpen(false)}
        prefillOrgType={demoPrefillType}
      />

      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        demoOrgs={demoOrgs}
        currentOrg={currentOrg}
        onSelectOrg={handleSelectOrg}
      />

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-6 text-center text-xs text-slate-400">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>
            <b>LabelCheck</b> &bull; India Legal Metrology (Packaged Commodities) Rules, 2011 Automated Verification
          </span>
          <span>FastAPI &bull; OpenCV &bull; Tesseract OCR &bull; ReportLab &bull; Recharts &bull; React + Tailwind</span>
        </div>
      </footer>
    </div>
  );
};

export default App;
