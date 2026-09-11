import React, { useState } from 'react';
import axios from 'axios';
import { X, Building2, Shield, ShoppingCart, Lock, Mail, Check } from 'lucide-react';
import type { Organization, User } from '../types';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  demoOrgs: Organization[];
  currentOrg: Organization | null;
  onSelectOrg: (org: Organization, user?: User, token?: string) => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  demoOrgs,
  currentOrg,
  onSelectOrg,
}) => {
  const [activeTab, setActiveTab] = useState<'demo' | 'login' | 'signup'>('demo');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [orgName, setOrgName] = useState('');
  const [orgType, setOrgType] = useState('brand');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleDemoSelect = (org: Organization) => {
    onSelectOrg(org, org.default_user, `token-${org.default_user?.id || 'demo'}`);
    onClose();
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const resp = await axios.post('/api/auth/login', { email, password });
      onSelectOrg(resp.data.organization, resp.data.user, resp.data.token);
      onClose();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Login failed. Check your credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const resp = await axios.post('/api/auth/signup', {
        email,
        password,
        name,
        organization_name: orgName,
        organization_type: orgType,
      });
      onSelectOrg(resp.data.organization, resp.data.user, resp.data.token);
      onClose();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Registration failed.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="bg-white rounded-3xl border border-slate-200 shadow-2xl max-w-lg w-full overflow-hidden relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="p-6 sm:p-8 space-y-6">
          <div>
            <h2 className="text-xl font-black text-slate-900 tracking-tight">
              Organization & Multi-Tenant Workspace
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              Switch between demo tenants or sign in with your enterprise organization.
            </p>
          </div>

          {/* Mode Switcher Tabs */}
          <div className="flex rounded-xl bg-slate-100 p-1 text-xs font-bold text-slate-600">
            <button
              onClick={() => { setActiveTab('demo'); setErrorMsg(null); }}
              className={`flex-1 py-1.5 rounded-lg transition-all ${
                activeTab === 'demo' ? 'bg-white text-slate-900 shadow-xs' : 'hover:text-slate-900'
              }`}
            >
              1-Click Demo Switcher
            </button>
            <button
              onClick={() => { setActiveTab('login'); setErrorMsg(null); }}
              className={`flex-1 py-1.5 rounded-lg transition-all ${
                activeTab === 'login' ? 'bg-white text-slate-900 shadow-xs' : 'hover:text-slate-900'
              }`}
            >
              Sign In
            </button>
            <button
              onClick={() => { setActiveTab('signup'); setErrorMsg(null); }}
              className={`flex-1 py-1.5 rounded-lg transition-all ${
                activeTab === 'signup' ? 'bg-white text-slate-900 shadow-xs' : 'hover:text-slate-900'
              }`}
            >
              Register Org
            </button>
          </div>

          {errorMsg && (
            <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-medium">
              {errorMsg}
            </div>
          )}

          {/* TAB 1: 1-Click Demo Orgs */}
          {activeTab === 'demo' && (
            <div className="space-y-3">
              <p className="text-xs text-slate-500 font-medium">
                Select a tenant profile to experience persona-specific audits and scoped data:
              </p>

              <div className="space-y-2.5">
                {demoOrgs.map((org) => {
                  const isSelected = currentOrg?.id === org.id;
                  const isBrand = org.type === 'brand';
                  const isGovt = org.type === 'government';
                  const isMkt = org.type === 'marketplace';

                  return (
                    <div
                      key={org.id}
                      onClick={() => handleDemoSelect(org)}
                      className={`p-3.5 rounded-2xl border cursor-pointer transition-all flex items-center justify-between ${
                        isSelected
                          ? 'border-sky-500 bg-sky-50/60 shadow-xs'
                          : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                      }`}
                    >
                      <div className="flex items-center space-x-3">
                        <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${
                          isBrand ? 'bg-emerald-100 text-emerald-700' :
                          isGovt ? 'bg-indigo-100 text-indigo-700' :
                          'bg-amber-100 text-amber-700'
                        }`}>
                          {isBrand && <Building2 className="w-4 h-4" />}
                          {isGovt && <Shield className="w-4 h-4" />}
                          {isMkt && <ShoppingCart className="w-4 h-4" />}
                        </div>

                        <div>
                          <div className="flex items-center space-x-2">
                            <span className="text-xs font-bold text-slate-900">{org.name}</span>
                            <span className="text-[10px] font-bold px-1.5 py-0.2 rounded-full uppercase bg-slate-200 text-slate-700">
                              {org.type}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-500">
                            User: {org.default_user?.name || 'Admin'}
                          </p>
                        </div>
                      </div>

                      {isSelected && (
                        <div className="w-6 h-6 rounded-full bg-sky-600 text-white flex items-center justify-center">
                          <Check className="w-3.5 h-3.5" />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* TAB 2: Login */}
          {activeTab === 'login' && (
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Email</label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="email"
                    required
                    placeholder="name@company.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 rounded-xl border border-slate-200 text-xs focus:outline-hidden focus:border-sky-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Password</label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="password"
                    required
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 rounded-xl border border-slate-200 text-xs focus:outline-hidden focus:border-sky-500"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-2.5 rounded-xl bg-sky-600 hover:bg-sky-700 text-white font-bold text-xs transition-colors shadow-xs"
              >
                {isLoading ? 'Signing In...' : 'Sign In to Workspace'}
              </button>
            </form>
          )}

          {/* TAB 3: Register */}
          {activeTab === 'signup' && (
            <form onSubmit={handleSignup} className="space-y-3">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Your Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Ramesh Chandra"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:outline-hidden focus:border-sky-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Email</label>
                <input
                  type="email"
                  required
                  placeholder="ramesh@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:outline-hidden focus:border-sky-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Organization Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Organic Foods Private Ltd"
                  value={orgName}
                  onChange={(e) => setOrgName(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:outline-hidden focus:border-sky-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Organization Type</label>
                <select
                  value={orgType}
                  onChange={(e) => setOrgType(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs bg-white text-slate-800 focus:outline-hidden focus:border-sky-500"
                >
                  <option value="brand">Brand Manufacturer</option>
                  <option value="government">Government / Legal Metrology</option>
                  <option value="marketplace">E-Commerce Marketplace</option>
                  <option value="audit_firm">Packaging / Audit Firm</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Password</label>
                <input
                  type="password"
                  required
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:outline-hidden focus:border-sky-500"
                />
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-2.5 rounded-xl bg-gradient-to-r from-sky-600 to-indigo-600 hover:from-sky-700 hover:to-indigo-700 text-white font-bold text-xs transition-all shadow-xs"
              >
                {isLoading ? 'Creating Workspace...' : 'Create Organization Workspace'}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
