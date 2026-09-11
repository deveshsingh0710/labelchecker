import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts';
import {
  History,
  Search,
  FileDown,
  ExternalLink,
  Calendar,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  TrendingUp,
  ShieldCheck,
  Scale,
  Building2,
  PieChart as PieIcon
} from 'lucide-react';
import type { VerificationResult, AnalyticsData, Organization } from '../types';

interface HistoryDashboardProps {
  onInspect: (id: string) => void;
  activeOrg?: Organization | null;
}

export const HistoryDashboard: React.FC<HistoryDashboardProps> = ({ onInspect, activeOrg }) => {
  const [verifications, setVerifications] = useState<VerificationResult[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const [histResp, anaResp] = await Promise.all([
        axios.get('/api/verifications', {
          headers: activeOrg ? { 'X-Organization-Id': activeOrg.id } : {}
        }),
        axios.get('/api/analytics', {
          headers: activeOrg ? { 'X-Organization-Id': activeOrg.id } : {}
        })
      ]);

      setVerifications(histResp.data.verifications || []);
      setAnalytics(anaResp.data);
    } catch (err) {
      console.error('Failed to load analytics and history:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [activeOrg?.id]);

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
    <div className="space-y-8">
      {/* 1. Header & Organization Scope */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-xl font-black text-slate-900 tracking-tight">
              Compliance Analytics & Audit Log
            </h2>
            {activeOrg && (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-sky-50 text-sky-700 border border-sky-200 flex items-center space-x-1">
                <Building2 className="w-3 h-3" />
                <span>{activeOrg.name}</span>
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Aggregated metrics, statutory violation frequency trends, and historical verification records under Legal Metrology 2011.
          </p>
        </div>

        <button
          onClick={fetchData}
          className="p-2 rounded-xl border border-slate-200 hover:bg-slate-100 text-slate-600 transition-colors self-start sm:self-auto flex items-center space-x-1 text-xs font-semibold cursor-pointer"
          title="Refresh analytics data"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Sync Data</span>
        </button>
      </div>

      {/* 2. Key KPI Summary Cards */}
      {analytics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {/* Card 1: Overall Compliance Rate */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Overall Compliance</span>
              <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
                <ShieldCheck className="w-4 h-4" />
              </div>
            </div>
            <div className="flex items-baseline space-x-2">
              <span className="text-3xl font-black text-slate-900">{analytics.compliance_rate}%</span>
              <span className="text-xs text-slate-500">compliant labels</span>
            </div>
            <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
              <div
                className="bg-emerald-500 h-full rounded-full transition-all duration-500"
                style={{ width: `${Math.min(100, analytics.compliance_rate)}%` }}
              />
            </div>
          </div>

          {/* Card 2: Total Scans */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Total Scans</span>
              <div className="w-8 h-8 rounded-lg bg-sky-50 text-sky-600 flex items-center justify-center">
                <History className="w-4 h-4" />
              </div>
            </div>
            <div className="flex items-baseline space-x-2">
              <span className="text-3xl font-black text-slate-900">{analytics.total_scans}</span>
              <span className="text-xs text-slate-500">packaged products</span>
            </div>
            <div className="text-[11px] text-slate-500 flex items-center space-x-2 font-medium">
              <span className="text-emerald-600 font-bold">{analytics.compliant_count} Pass</span> &bull;
              <span className="text-amber-600 font-bold">{analytics.partially_compliant_count} Review</span> &bull;
              <span className="text-rose-600 font-bold">{analytics.non_compliant_count} Fail</span>
            </div>
          </div>

          {/* Card 3: Average Compliance Score */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Average Score</span>
              <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
                <TrendingUp className="w-4 h-4" />
              </div>
            </div>
            <div className="flex items-baseline space-x-2">
              <span className="text-3xl font-black text-slate-900">{analytics.average_score}</span>
              <span className="text-xs text-slate-500">/ 100 weighted</span>
            </div>
            <p className="text-[11px] text-slate-500 font-medium">
              Evaluated across all Rule 6 statutory clauses
            </p>
          </div>

          {/* Card 4: Top Violation Rate */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Top Risk Area</span>
              <div className="w-8 h-8 rounded-lg bg-rose-50 text-rose-600 flex items-center justify-center">
                <AlertTriangle className="w-4 h-4" />
              </div>
            </div>
            <div className="truncate">
              <span className="text-xl font-black text-slate-900 block truncate">
                {analytics.top_violations[0]?.rule_name || 'No Violations'}
              </span>
              <span className="text-xs text-rose-600 font-bold">
                {analytics.top_violations[0] ? `${analytics.top_violations[0].count} labels affected` : '100% clean'}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 truncate">
              {analytics.top_violations[0]?.legal_reference || 'Rule 6 compliance verified'}
            </p>
          </div>
        </div>
      )}

      {/* 3. Visual Charts Grid */}
      {analytics && analytics.total_scans > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
          {/* Left: Top Violations Bar Chart (8 cols) */}
          <div className="lg:col-span-8 bg-white rounded-2xl border border-slate-200 p-6 shadow-xs flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
                <div>
                  <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
                    <Scale className="w-4 h-4 text-sky-600" />
                    <span>Most Common Statutory Violations</span>
                  </h3>
                  <p className="text-xs text-slate-500">
                    Frequency of non-compliant statutory declarations across scans.
                  </p>
                </div>
              </div>

              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={analytics.top_violations}
                    layout="vertical"
                    margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                  >
                    <XAxis type="number" tick={{ fontSize: 11 }} />
                    <YAxis
                      dataKey="rule_name"
                      type="category"
                      width={160}
                      tick={{ fontSize: 11, fill: '#475569' }}
                    />
                    <Tooltip
                      formatter={(val: any, _name: any, item: any) => [
                        `${val} labels (${item.payload.percentage}%)`,
                        'Violations'
                      ]}
                      contentStyle={{ borderRadius: '12px', fontSize: '12px', borderColor: '#E2E8F0' }}
                    />
                    <Bar dataKey="count" fill="#F43F5E" radius={[0, 6, 6, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Right: Compliance Status Breakdown (4 cols) */}
          <div className="lg:col-span-4 bg-white rounded-2xl border border-slate-200 p-6 shadow-xs flex flex-col justify-between">
            <div>
              <div className="border-b border-slate-100 pb-3 mb-4">
                <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
                  <PieIcon className="w-4 h-4 text-indigo-600" />
                  <span>Compliance Breakdown</span>
                </h3>
                <p className="text-xs text-slate-500">Distribution across all historical scans.</p>
              </div>

              <div className="h-48 w-full flex items-center justify-center">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={analytics.status_breakdown}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={45}
                      outerRadius={75}
                      paddingAngle={4}
                    >
                      {analytics.status_breakdown.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(val: any) => [`${val} labels`, 'Count']}
                      contentStyle={{ borderRadius: '12px', fontSize: '12px' }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              {/* Chart Legend */}
              <div className="space-y-2 mt-4 pt-3 border-t border-slate-100 text-xs">
                {analytics.status_breakdown.map((item) => (
                  <div key={item.name} className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.color }} />
                      <span className="text-slate-600">{item.name}</span>
                    </div>
                    <span className="font-bold text-slate-800 font-mono">{item.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 4. Table of Past Verifications */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
          <div>
            <h3 className="text-base font-bold text-slate-900 flex items-center space-x-2">
              <History className="w-4 h-4 text-sky-600" />
              <span>Inspection Records</span>
            </h3>
            <p className="text-xs text-slate-500">
              Individual packaging scans evaluated against Legal Metrology 2011.
            </p>
          </div>

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
        </div>

        {isLoading ? (
          <div className="py-12 text-center text-slate-400 text-sm">
            <div className="w-6 h-6 border-2 border-sky-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            Loading audit records...
          </div>
        ) : filtered.length === 0 ? (
          <div className="py-12 text-center text-slate-500 text-sm space-y-2">
            <History className="w-10 h-10 text-slate-300 mx-auto" />
            <p className="font-semibold text-slate-700">No verification history found for this tenant</p>
            <p className="text-xs text-slate-400">Run a verification to generate records and compliance charts.</p>
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
                        className="px-2.5 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-100 font-medium text-slate-700 transition-colors inline-flex items-center space-x-1 cursor-pointer"
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
    </div>
  );
};
