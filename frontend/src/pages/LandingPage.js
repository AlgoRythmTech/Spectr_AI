import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Scale, FileText, Workflow, BookOpen, Shield, ChevronRight,
  Gavel, Calculator, Building2, ArrowRight, Users, Clock, Zap, Globe
} from 'lucide-react';

const FEATURES = [
  {
    icon: Scale,
    title: 'AI Legal Assistant',
    desc: 'Query Indian law with precision. Every response structured as a senior partner\'s memo — with exact sections, case citations, and rupee calculations.',
    tag: 'IndianKanoon Powered'
  },
  {
    icon: FileText,
    title: 'Document Vault',
    desc: 'Upload any document — contracts, notices, financials. Associate finds what you missed. Anomaly detection, deadline extraction, automatic responses.',
    tag: 'OCR Enabled'
  },
  {
    icon: Workflow,
    title: '20 Pre-built Workflows',
    desc: 'Cheque bounce notices, GST SCN responses, bail applications, IT notice replies. Fill 5 fields, get a court-ready document in under 3 minutes.',
    tag: 'Zero Prompt Engineering'
  },
  {
    icon: BookOpen,
    title: 'Firm Library',
    desc: 'Your firm\'s brain that grows daily. Templates, playbooks, client profiles, and annotations. Associate learns your drafting style.',
    tag: 'Adaptive Intelligence'
  },
];

const STATS = [
  { value: '50M+', label: 'Pending Cases in India', icon: Gavel },
  { value: '1.5M', label: 'Practising Lawyers', icon: Users },
  { value: '160K+', label: 'Chartered Accountants', icon: Calculator },
  { value: '18+', label: 'Indian Statutes Indexed', icon: BookOpen },
];

const USE_CASES = [
  { title: 'For Litigation Lawyers', items: ['Section 138 NI Act notices in 2 minutes', 'Bail applications with cited precedents', 'Contract review with risk matrix', 'Writ petition briefs with constitutional grounds'] },
  { title: 'For Chartered Accountants', items: ['GST SCN responses with AAR precedents', 'IT notice replies (143/148) with computation reconciliation', 'PMLA compliance notes', 'Due diligence reports with live MCA data'] },
  { title: 'For Corporate Counsel', items: ['IBC Section 9 applications', 'Director disqualification checks', 'FEMA compounding applications', 'SEBI regulation compliance analysis'] },
];

export default function LandingPage() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const handleGetStarted = () => {
    if (user) {
      navigate('/app/assistant');
    } else {
      // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
      const redirectUrl = window.location.origin + '/app/assistant';
      window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
    }
  };

  return (
    <div className="min-h-screen bg-white" data-testid="landing-page">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-white/90 backdrop-blur-md border-b border-[#E2E8F0]" data-testid="landing-nav">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-[#1A1A2E] rounded-sm flex items-center justify-center">
              <Scale className="w-4 h-4 text-white" />
            </div>
            <span className="text-lg font-bold tracking-tight text-[#1A1A2E]">Associate</span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm text-[#4A4A4A]">
            <a href="#features" className="hover:text-[#0D0D0D] transition-colors">Features</a>
            <a href="#workflows" className="hover:text-[#0D0D0D] transition-colors">Workflows</a>
            <a href="#use-cases" className="hover:text-[#0D0D0D] transition-colors">Use Cases</a>
          </div>
          <button
            data-testid="nav-get-started-btn"
            onClick={handleGetStarted}
            className="bg-[#1A1A2E] text-white text-sm font-medium px-5 py-2 rounded-sm hover:bg-[#0D0D0D] transition-colors"
          >
            {user ? 'Open Dashboard' : 'Get Started'}
          </button>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-32 pb-24 px-6" data-testid="hero-section">
        <div className="max-w-7xl mx-auto">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-[#F8FAFC] border border-[#E2E8F0] rounded-sm text-xs font-medium text-[#4A4A4A] mb-8 animate-fade-in-up">
              <Shield className="w-3 h-3" />
              Built for India's Legal System — 18+ Statutes Indexed
            </div>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-[#1A1A2E] leading-[1.1] mb-6 animate-fade-in-up" style={{animationDelay: '0.1s'}}>
              Your senior partner.<br />
              <span className="text-[#64748B]">Available at midnight.</span>
            </h1>
            <p className="text-lg text-[#4A4A4A] leading-relaxed mb-10 max-w-2xl animate-fade-in-up" style={{animationDelay: '0.2s'}}>
              Associate is the AI legal and financial intelligence platform built specifically for Indian law.
              Every response structured as a partner's memo — with exact section citations, case law from IndianKanoon,
              and rupee-precise calculations.
            </p>
            <div className="flex items-center gap-4 animate-fade-in-up" style={{animationDelay: '0.3s'}}>
              <button
                data-testid="hero-get-started-btn"
                onClick={handleGetStarted}
                className="bg-[#1A1A2E] text-white font-medium px-8 py-3 rounded-sm hover:bg-[#0D0D0D] transition-colors flex items-center gap-2 text-sm"
              >
                {user ? 'Open Dashboard' : 'Start Using Associate'}
                <ArrowRight className="w-4 h-4" />
              </button>
              <a href="#features" className="text-sm text-[#4A4A4A] hover:text-[#0D0D0D] transition-colors flex items-center gap-1">
                See how it works <ChevronRight className="w-3 h-3" />
              </a>
            </div>
          </div>

          {/* Demo Response Card Preview */}
          <div className="mt-16 border border-[#E2E8F0] rounded-sm bg-white shadow-[0_4px_16px_rgba(0,0,0,0.06)] p-6 max-w-4xl animate-fade-in-up" style={{animationDelay: '0.4s'}}>
            <div className="flex items-center gap-2 mb-4">
              <div className="w-2 h-2 bg-[#166534] rounded-full" />
              <span className="text-xs font-semibold tracking-wider text-[#64748B] uppercase">Sample Response</span>
            </div>
            <div className="space-y-3">
              <div className="border-l-2 border-[#1A1A2E] pl-4">
                <p className="text-xs font-semibold tracking-wider text-[#1A1A2E] uppercase mb-1">Issue Identified</p>
                <p className="text-[15px] text-[#0D0D0D]">Client received a cheque bounce notice under Section 138, Negotiable Instruments Act, 1881. Cheque dishonoured due to "insufficient funds."</p>
              </div>
              <div className="border-l-2 border-[#E2E8F0] pl-4">
                <p className="text-xs font-semibold tracking-wider text-[#1A1A2E] uppercase mb-1">Applicable Law</p>
                <p className="font-mono text-[13px] text-[#4A4A4A]">Section 138, Negotiable Instruments Act, 1881 (as amended by NI Amendment Act, 2015)</p>
                <p className="font-mono text-[13px] text-[#4A4A4A]">Section 141 — Liability of Directors in case of company</p>
              </div>
              <div className="border-l-2 border-[#E2E8F0] pl-4">
                <p className="text-xs font-semibold tracking-wider text-[#1A1A2E] uppercase mb-1">Financial Exposure</p>
                <p className="font-mono text-[13px] text-[#0D0D0D]">Principal: ₹15,00,000 | Interest @18% p.a.: ₹2,70,000 | Penalty: ₹15,00,000</p>
                <p className="font-mono text-sm font-semibold text-[#991B1B]">TOTAL WORST-CASE EXPOSURE: ₹32,70,000</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="py-16 border-y border-[#E2E8F0] bg-[#F8FAFC]">
        <div className="max-w-7xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-8">
          {STATS.map((s, i) => (
            <div key={i} className="text-center">
              <s.icon className="w-5 h-5 text-[#64748B] mx-auto mb-3" />
              <p className="text-3xl font-bold text-[#1A1A2E] tracking-tight">{s.value}</p>
              <p className="text-xs text-[#64748B] mt-1 font-medium">{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-24 px-6" data-testid="features-section">
        <div className="max-w-7xl mx-auto">
          <div className="mb-16">
            <p className="text-xs font-semibold tracking-widest text-[#64748B] uppercase mb-3">Capabilities</p>
            <h2 className="text-3xl font-semibold tracking-tight text-[#1A1A2E]">Built for how Indian professionals actually work</h2>
          </div>
          <div className="grid md:grid-cols-2 gap-6">
            {FEATURES.map((f, i) => (
              <div key={i} className="border border-[#E2E8F0] rounded-sm p-6 hover:border-[#CBD5E1] transition-colors group" data-testid={`feature-card-${i}`}>
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 bg-[#F8FAFC] border border-[#E2E8F0] rounded-sm flex items-center justify-center shrink-0 group-hover:bg-[#1A1A2E] transition-colors">
                    <f.icon className="w-5 h-5 text-[#1A1A2E] group-hover:text-white transition-colors" />
                  </div>
                  <div>
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-base font-semibold text-[#0D0D0D]">{f.title}</h3>
                      <span className="text-[10px] font-medium text-[#64748B] bg-[#F1F5F9] px-2 py-0.5 rounded-sm">{f.tag}</span>
                    </div>
                    <p className="text-sm text-[#4A4A4A] leading-relaxed">{f.desc}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Use Cases */}
      <section id="use-cases" className="py-24 px-6 bg-[#F8FAFC] border-y border-[#E2E8F0]" data-testid="use-cases-section">
        <div className="max-w-7xl mx-auto">
          <div className="mb-16">
            <p className="text-xs font-semibold tracking-widest text-[#64748B] uppercase mb-3">Who It's For</p>
            <h2 className="text-3xl font-semibold tracking-tight text-[#1A1A2E]">Every professional. Every practice area.</h2>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {USE_CASES.map((uc, i) => (
              <div key={i} className="bg-white border border-[#E2E8F0] rounded-sm p-6" data-testid={`use-case-card-${i}`}>
                <h3 className="text-base font-semibold text-[#1A1A2E] mb-4">{uc.title}</h3>
                <ul className="space-y-2">
                  {uc.items.map((item, j) => (
                    <li key={j} className="flex items-start gap-2 text-sm text-[#4A4A4A]">
                      <ChevronRight className="w-3 h-3 text-[#1A1A2E] mt-1 shrink-0" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Workflows Preview */}
      <section id="workflows" className="py-24 px-6" data-testid="workflows-section">
        <div className="max-w-7xl mx-auto">
          <div className="mb-16">
            <p className="text-xs font-semibold tracking-widest text-[#64748B] uppercase mb-3">Workflows</p>
            <h2 className="text-3xl font-semibold tracking-tight text-[#1A1A2E]">Court-ready documents in under 3 minutes</h2>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {['Section 138 Notice', 'GST SCN Response', 'Bail Application', 'IT 143(1) Reply',
              'Consumer Complaint', 'RERA Complaint', 'Writ Petition', 'Due Diligence Report',
              'RTI Application', 'Contract Review', 'PMLA Note', 'FEMA Application'
            ].map((w, i) => (
              <div key={i} className="border border-[#E2E8F0] rounded-sm px-4 py-3 text-sm text-[#0D0D0D] hover:bg-[#F8FAFC] hover:border-[#CBD5E1] transition-colors cursor-pointer flex items-center gap-2">
                <Zap className="w-3 h-3 text-[#64748B]" />
                {w}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24 px-6 bg-[#1A1A2E]" data-testid="cta-section">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl sm:text-4xl font-bold text-white tracking-tight mb-4">
            India has 50 million pending cases.<br />
            None of its professionals have a tool built for them.
          </h2>
          <p className="text-base text-[#94A3B8] mb-8">Until now.</p>
          <button
            data-testid="cta-get-started-btn"
            onClick={handleGetStarted}
            className="bg-white text-[#1A1A2E] font-semibold px-8 py-3 rounded-sm hover:bg-[#F1F5F9] transition-colors text-sm"
          >
            {user ? 'Open Dashboard' : 'Start Using Associate'}
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-6 border-t border-[#E2E8F0]" data-testid="footer">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 bg-[#1A1A2E] rounded-sm flex items-center justify-center">
              <Scale className="w-3 h-3 text-white" />
            </div>
            <span className="text-sm font-semibold text-[#1A1A2E]">Associate</span>
          </div>
          <p className="text-xs text-[#64748B]">Built by AlgoRythm Group</p>
        </div>
      </footer>
    </div>
  );
}
