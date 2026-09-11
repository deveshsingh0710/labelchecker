import React, { useState } from 'react';
import axios from 'axios';
import { X, Send, CheckCircle2, Building, Mail, User as UserIcon, Sparkles } from 'lucide-react';
import type { DemoRequestForm } from '../types';

interface DemoRequestModalProps {
  isOpen: boolean;
  onClose: () => void;
  prefillOrgType?: string;
}

export const DemoRequestModal: React.FC<DemoRequestModalProps> = ({
  isOpen,
  onClose,
  prefillOrgType = 'brand'
}) => {
  const [formData, setFormData] = useState<DemoRequestForm>({
    name: '',
    email: '',
    organization_name: '',
    organization_type: prefillOrgType || 'brand',
    message: ''
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name || !formData.email || !formData.organization_name) {
      setErrorMessage('Please provide your name, email, and organization.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      await axios.post('/api/demo-request', formData);
      setIsSuccess(true);
      setTimeout(() => {
        setIsSuccess(false);
        onClose();
        setFormData({
          name: '',
          email: '',
          organization_name: '',
          organization_type: 'brand',
          message: ''
        });
      }, 2500);
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Failed to submit demo request. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="bg-white rounded-3xl border border-slate-200 shadow-2xl max-w-lg w-full overflow-hidden relative">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {isSuccess ? (
          <div className="p-8 text-center space-y-4 py-12">
            <div className="w-16 h-16 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto shadow-sm">
              <CheckCircle2 className="w-10 h-10" />
            </div>
            <h3 className="text-xl font-bold text-slate-900">Demo Request Submitted!</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto leading-relaxed">
              Thank you, <b>{formData.name}</b>. Our Legal Metrology compliance specialist will contact you at <b>{formData.email}</b> within 24 hours.
            </p>
          </div>
        ) : (
          <div className="p-6 sm:p-8 space-y-6">
            {/* Modal Title */}
            <div>
              <div className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full bg-sky-50 text-sky-700 text-xs font-bold mb-2">
                <Sparkles className="w-3.5 h-3.5" />
                <span>Enterprise & Enforcement Solutions</span>
              </div>
              <h2 className="text-xl font-black text-slate-900 tracking-tight">Request an Enterprise Demo</h2>
              <p className="text-xs text-slate-500 mt-1">
                See how LabelCheck automates bulk packaging audits, e-commerce catalog screening, and field inspections.
              </p>
            </div>

            {errorMessage && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-medium">
                {errorMessage}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Name */}
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Full Name *</label>
                <div className="relative">
                  <UserIcon className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="text"
                    required
                    placeholder="e.g. Sumanth Rao"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full pl-9 pr-3 py-2 rounded-xl border border-slate-200 text-xs focus:outline-hidden focus:border-sky-500 focus:ring-1 focus:ring-sky-500"
                  />
                </div>
              </div>

              {/* Email */}
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Work Email *</label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="email"
                    required
                    placeholder="e.g. sumanth@fmcgbrand.in"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full pl-9 pr-3 py-2 rounded-xl border border-slate-200 text-xs focus:outline-hidden focus:border-sky-500 focus:ring-1 focus:ring-sky-500"
                  />
                </div>
              </div>

              {/* Organization Name & Type Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Organization *</label>
                  <div className="relative">
                    <Building className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                    <input
                      type="text"
                      required
                      placeholder="e.g. Acme Foods Ltd"
                      value={formData.organization_name}
                      onChange={(e) => setFormData({ ...formData, organization_name: e.target.value })}
                      className="w-full pl-9 pr-3 py-2 rounded-xl border border-slate-200 text-xs focus:outline-hidden focus:border-sky-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Organization Type</label>
                  <select
                    value={formData.organization_type}
                    onChange={(e) => setFormData({ ...formData, organization_type: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs bg-white text-slate-800 focus:outline-hidden focus:border-sky-500"
                  >
                    <option value="brand">FMCG / Brand Manufacturer</option>
                    <option value="marketplace">E-Commerce Marketplace</option>
                    <option value="government">Legal Metrology Dept / Govt</option>
                    <option value="audit_firm">Packaging / Audit Firm</option>
                  </select>
                </div>
              </div>

              {/* Message */}
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Monthly Scan Volume / Use-Case</label>
                <textarea
                  rows={3}
                  placeholder="e.g., We have 4,000 SKUs needing pre-print verification..."
                  value={formData.message}
                  onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                  className="w-full p-3 rounded-xl border border-slate-200 text-xs focus:outline-hidden focus:border-sky-500 resize-none"
                />
              </div>

              {/* Submit CTA */}
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-sky-600 to-indigo-600 hover:from-sky-700 hover:to-indigo-700 text-white font-bold text-xs transition-all shadow-md shadow-sky-100 flex items-center justify-center space-x-2 disabled:opacity-50 cursor-pointer"
              >
                <Send className="w-3.5 h-3.5" />
                <span>{isSubmitting ? 'Submitting Request...' : 'Schedule Verification Demo'}</span>
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
};
