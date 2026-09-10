import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { History, Search, FileDown, ExternalLink, Calendar, CheckCircle2, XCircle, AlertTriangle, RefreshCw } from 'lucide-react';
import type { VerificationResult } from '../types';

interface HistoryDashboardProps {
  onInspect: (id: string) => void;
}

export const HistoryDashboard: React.FC<HistoryDashboardProps> = ({ onInspect }) => {
  const [verifications, setVerifications] = useState<VerificationResult[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  const fetchHistory = async () => {
    setIsLoading(true);
    try {
      const resp = await axios.get('/api/verifications');
      setVerifications(resp.data.verifications || []);
    } catch (err) {
      console.error('Failed to load history:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const filtered = verifications.filter((v) =>
    v.filename.toLowerCase().includes(searchTerm.toLowerCase()) ||
    v.compliance_status.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getStatusBadge = (status: string) => {
    if (status === 'COMPLIANT') {
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span>Compliant</span>
        </span>
      );
    }
    if (status === 'PARTIALLY_COMPLIANT') {
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-50 text-amber-700 border border-amber-200">
          <AlertTriangle className="w-3.5 h-3.5" />
          <span>Partially Compliant</span>
        </span>
      );
    }
    return (
      <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-bold bg-rose-50 text-rose-700 border border-rose-200">
        <XCircle className="w-3.5 h-3.5" />
        <span>Non-Compliant</span>
      </span>
    );
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-5">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center space-x-2">
            <History className="w-5 h-5 text-sky-600" />
            <span>Audit History & Verification Logs</span>
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Historical record of packaged commodity labels analyzed under the Legal Metrology Rules, 2011.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          {/* Search bar */}
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search filename or status..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9 pr-4 py-1.5 rounded-xl border border-slate-200 text-xs focus:outline-hidden focus:border-sky-500 w-48 sm:w-64"
            />
          </div>

          <button
            onClick={fetchHistory}
            className="p-2 rounded-xl border border-slate-200 hover:bg-slate-100 text-slate-600 transition-colors"
            title="Refresh history"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Content Table / Cards */}
      {isLoading ? (
        <div className="py-12 text-center text-slate-400 text-sm">
          <div className="w-6 h-6 border-2 border-sky-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
          Loading audit records...
        </div>
      ) : filtered.length === 0 ? (
        <div className="py-12 text-center text-slate-500 text-sm space-y-2">
          <History className="w-10 h-10 text-slate-300 mx-auto" />
          <p className="font-semibold text-slate-700">No verification history found</p>
          <p className="text-xs text-slate-400">Upload a label or run a sample test to record your first compliance audit.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-700 border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
                <th className="py-3 px-4">Label Preview</th>
                <th className="py-3 px-4">Filename / ID</th>
                <th className="py-3 px-4">Score</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Checked Date</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((item) => (
                <tr key={item.id} className="hover:bg-slate-50/70 transition-colors">
                  <td className="py-3 px-4">
                    <img
                      src={item.preprocessed_image_url || item.raw_image_url}
                      alt={item.filename}
                      className="w-12 h-12 object-cover rounded-lg border border-slate-200 shadow-xs"
                    />
                  </td>
                  <td className="py-3 px-4">
                    <span className="font-bold text-slate-900 block truncate max-w-[200px]">{item.filename}</span>
                    <span className="text-[10px] text-slate-400 font-mono">{item.id.slice(0, 8)}...</span>
                  </td>
                  <td className="py-3 px-4 font-bold text-slate-900 text-sm">
                    {item.overall_score}%
                  </td>
                  <td className="py-3 px-4">
                    {getStatusBadge(item.compliance_status)}
                  </td>
                  <td className="py-3 px-4 text-slate-500 text-[11px]">
                    <div className="flex items-center space-x-1">
                      <Calendar className="w-3.5 h-3.5 text-slate-400" />
                      <span>
                        {item.created_at
                          ? new Date(item.created_at).toLocaleDateString('en-GB', {
                              day: '2-digit',
                              month: 'short',
                              year: 'numeric',
                            })
                          : 'Recent'}
                      </span>
                    </div>
                  </td>
                  <td className="py-3 px-4 text-right space-x-2">
                    <button
                      onClick={() => onInspect(item.id)}
                      className="px-2.5 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-100 font-medium text-slate-700 transition-colors inline-flex items-center space-x-1"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                      <span>View</span>
                    </button>
                    <a
                      href={`/api/verifications/${item.id}/pdf`}
                      download
                      className="px-2.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white font-medium transition-colors inline-flex items-center space-x-1"
                    >
                      <FileDown className="w-3.5 h-3.5 text-sky-400" />
                      <span>PDF</span>
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
