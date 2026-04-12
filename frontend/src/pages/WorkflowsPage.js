import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { Play, Loader2, CheckCircle2, ChevronRight, Search, X } from 'lucide-react';

const API = process.env.NODE_ENV === 'development' ? 'http://localhost:8000/api' : '/api';

const WORKFLOW_TEMPLATES = [
  // --- TAX COMPLIANCE ---
  { id: 'gstr3b_filing', name: 'GSTR-3B Filing', description: 'Compute output tax, reconcile ITC, verify auto-populated data, generate return summary.', steps: 4, category: 'Tax Compliance' },
  { id: 'gstr1_filing', name: 'GSTR-1 Preparation', description: 'Classify outward supplies, generate invoice-wise details, verify HSN summary, prepare filing data.', steps: 4, category: 'Tax Compliance' },
  { id: 'gstr9_annual', name: 'GSTR-9 Annual Return', description: 'Reconcile monthly returns, compare books vs returns, identify discrepancies, prepare annual summary.', steps: 5, category: 'Tax Compliance' },
  { id: 'itr_filing', name: 'ITR Filing Preparation', description: 'Compute total income, apply deductions, compare old vs new regime, generate computation sheet.', steps: 5, category: 'Tax Compliance' },
  { id: 'tds_return', name: 'TDS Return (24Q/26Q)', description: 'Compile deductee records, verify PAN, compute TDS, validate challan matching, generate return data.', steps: 5, category: 'Tax Compliance' },
  { id: 'advance_tax', name: 'Advance Tax Computation', description: 'Estimate income for all quarters, compute tax liability, calculate installment amounts, track payments.', steps: 4, category: 'Tax Compliance' },
  { id: 'tax_audit_3cd', name: 'Tax Audit (Form 3CA/3CD)', description: 'Review books, verify S.44AB applicability, complete 3CD clauses, draft audit report.', steps: 6, category: 'Tax Compliance' },
  { id: 'gst_audit', name: 'GST Audit Preparation', description: 'Reconcile GSTR-3B vs GSTR-1, verify ITC eligibility, check reverse charge, prepare GSTR-9C.', steps: 5, category: 'Tax Compliance' },

  // --- NOTICE & DISPUTE ---
  { id: 'scn_reply', name: 'SCN Reply Drafting', description: 'Analyze show-cause notice, identify defenses, draft point-by-point reply with case law citations.', steps: 4, category: 'Notice & Dispute' },
  { id: 'reassessment_challenge', name: 'Reassessment Challenge', description: 'Validate S.148/148A notice, check limitation, draft objection memo, prepare writ petition grounds.', steps: 4, category: 'Notice & Dispute' },
  { id: 'cita_appeal', name: 'CIT(A) Appeal Preparation', description: 'Analyze assessment order, identify grounds, draft Form 35, prepare written submissions with case law.', steps: 5, category: 'Notice & Dispute' },
  { id: 'itat_appeal', name: 'ITAT Appeal Preparation', description: 'Review CIT(A) order, draft grounds of appeal, prepare paper book, draft written submissions.', steps: 5, category: 'Notice & Dispute' },
  { id: 'drc03_response', name: 'DRC-03 Voluntary Payment', description: 'Assess liability, compute exact amount, prepare DRC-03 submission, draft cover letter.', steps: 3, category: 'Notice & Dispute' },
  { id: 'refund_rfd01', name: 'GST Refund (RFD-01)', description: 'Verify refund eligibility, compute eligible amount, prepare supporting documents, draft application.', steps: 4, category: 'Notice & Dispute' },
  { id: 'notice_validity', name: 'Notice Validity Challenge', description: 'Check jurisdictional validity, DIN compliance, limitation period, draft challenge memo.', steps: 3, category: 'Notice & Dispute' },
  { id: 'penalty_waiver', name: 'Penalty Waiver Application', description: 'Identify penalty provisions, compute exposure, draft reasonable cause explanation under S.273B.', steps: 3, category: 'Notice & Dispute' },

  // --- LEGAL DRAFTING ---
  { id: 'bail_application', name: 'Bail Application', description: 'Analyze FIR/charge sheet, assess eligibility under BNS/BNSS, research precedents, draft application.', steps: 4, category: 'Legal Drafting' },
  { id: 'legal_notice_138', name: 'S.138 Cheque Bounce Notice', description: 'Verify facts, check limitation, draft legal notice, prepare complaint grounds.', steps: 4, category: 'Legal Drafting' },
  { id: 'writ_petition', name: 'Writ Petition Drafting', description: 'Identify Article 226/32 grounds, prepare synopsis, draft grounds with case law, prepare prayer.', steps: 5, category: 'Legal Drafting' },
  { id: 'criminal_complaint', name: 'Criminal Complaint', description: 'Analyze facts for cognizable offence, identify BNS sections, draft complaint with annexures.', steps: 4, category: 'Legal Drafting' },
  { id: 'appeal_memo', name: 'Appeal Memorandum', description: 'Review impugned order, formulate grounds, draft statement of facts, prepare memorial.', steps: 4, category: 'Legal Drafting' },
  { id: 'arbitration_clause', name: 'Arbitration Petition', description: 'Analyze arbitration agreement, identify S.11/S.9 grounds, draft petition with supporting documents.', steps: 4, category: 'Legal Drafting' },
  { id: 'demand_notice', name: 'Civil Demand Notice', description: 'Quantify claim, identify legal basis, draft demand with timeline, prepare evidence summary.', steps: 3, category: 'Legal Drafting' },

  // --- ADVISORY ---
  { id: 'regime_comparison', name: 'Old vs New Tax Regime', description: 'Compute tax under both regimes, analyze deductions impact, recommend optimal regime with breakeven.', steps: 3, category: 'Advisory' },
  { id: 'capital_gains', name: 'Capital Gains Computation', description: 'Classify asset type, apply indexation, compute LTCG/STCG, identify exemption options (S.54/54F/54EC).', steps: 4, category: 'Advisory' },
  { id: 'nri_taxation', name: 'NRI Taxation Advisory', description: 'Determine residential status, identify Indian income sources, compute DTAA benefit, draft advisory.', steps: 4, category: 'Advisory' },
  { id: 'startup_benefits', name: 'Startup Tax Benefits (S.80IAC)', description: 'Verify DPIIT eligibility, compute S.80IAC deduction, check angel tax exemption, draft application.', steps: 4, category: 'Advisory' },
  { id: 'huf_planning', name: 'HUF Tax Planning', description: 'Analyze HUF formation, identify income splitting opportunities, compute tax savings, draft deed.', steps: 4, category: 'Advisory' },
  { id: 'trust_compliance', name: 'Charitable Trust Compliance', description: 'Verify S.12A/12AB registration, check S.11 conditions, compute application of income, file Form 10.', steps: 5, category: 'Advisory' },
  { id: 'transfer_pricing', name: 'Transfer Pricing Documentation', description: 'Identify related party transactions, select TP method, prepare benchmarking study, draft TP report.', steps: 5, category: 'Advisory' },

  // --- CORPORATE ---
  { id: 'company_incorporation', name: 'Company Incorporation', description: 'Draft MOA/AOA, prepare SPICe+ forms, obtain DSC/DIN, file incorporation documents.', steps: 5, category: 'Corporate' },
  { id: 'llp_conversion', name: 'Partnership to LLP Conversion', description: 'Prepare Form 17, draft LLP agreement, file conversion documents, transfer registrations.', steps: 4, category: 'Corporate' },
  { id: 'annual_roc', name: 'Annual ROC Filing', description: 'Prepare AOC-4/MGT-7, draft board resolutions, verify director compliance, file annual returns.', steps: 4, category: 'Corporate' },
  { id: 'msme_registration', name: 'MSME Registration & Benefits', description: 'Verify eligibility criteria, prepare Udyam registration, identify applicable subsidies and schemes.', steps: 3, category: 'Corporate' },
  { id: 'contract_review', name: 'Contract Risk Analysis', description: 'Review commercial terms, identify legal risks, check stamp duty, analyze TDS and GST obligations.', steps: 5, category: 'Corporate' },
  { id: 'due_diligence', name: 'Legal Due Diligence', description: 'Review corporate records, check litigation history, verify regulatory compliance, draft DD report.', steps: 6, category: 'Corporate' },

  // --- RECONCILIATION ---
  { id: 'itc_reconciliation', name: 'ITC Reconciliation', description: 'Match GSTR-2B with purchase register, classify mismatches, draft vendor follow-up letters.', steps: 3, category: 'Reconciliation' },
  { id: 'tds_26as_reconciliation', name: 'TDS vs 26AS Reconciliation', description: 'Match TDS deducted with 26AS/AIS credits, identify short deductions, draft mismatch letters.', steps: 3, category: 'Reconciliation' },
  { id: 'bank_reconciliation', name: 'Bank Reconciliation Statement', description: 'Match book entries with bank statement, identify timing differences, prepare BRS.', steps: 3, category: 'Reconciliation' },
];

const CATEGORIES = [...new Set(WORKFLOW_TEMPLATES.map(t => t.category))];

export default function WorkflowsPage() {
  const { getToken } = useAuth();
  const [templates, setTemplates] = useState(WORKFLOW_TEMPLATES);
  const [loading] = useState(false);
  const [activeCategory, setActiveCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [initialInput, setInitialInput] = useState('');
  const [activeChain, setActiveChain] = useState(null);
  const [chainLoading, setChainLoading] = useState(false);
  const [editedOutput, setEditedOutput] = useState('');
  const [showModal, setShowModal] = useState(false);
  const modalRef = useRef(null);

  useEffect(() => { fetchTemplates(); }, []); // eslint-disable-line

  /* close modal on outside click */
  useEffect(() => {
    if (!showModal) return;
    const handler = (e) => {
      if (modalRef.current && !modalRef.current.contains(e.target)) {
        setShowModal(false);
        setSelectedTemplate(null);
        setInitialInput('');
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [showModal]);

  /* close modal on Escape */
  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'Escape' && showModal) {
        setShowModal(false);
        setSelectedTemplate(null);
        setInitialInput('');
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [showModal]);

  const fetchTemplates = async () => {
    try {
      let token = 'dev_mock_token_7128';
      try { token = await getToken() || token; } catch {}
      const res = await fetch(`${API}/workflows/chain/templates`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        /* Only use API templates if they have proper categories and are more than local */
        if (data.templates?.length > WORKFLOW_TEMPLATES.length) {
          const valid = data.templates.every(t => t.category && t.name);
          if (valid) setTemplates(data.templates);
        }
      }
    } catch {}
  };

  const openWorkflow = (t) => {
    setSelectedTemplate(t);
    setInitialInput('');
    setShowModal(true);
  };

  const handleStartChain = async () => {
    if (!selectedTemplate || !initialInput.trim()) return;
    setChainLoading(true);
    setShowModal(false);
    try {
      let token = 'dev_mock_token_7128';
      try { token = await getToken() || token; } catch {}
      const res = await fetch(`${API}/workflows/chain/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ chain_type: selectedTemplate.id, initial_input: initialInput })
      });
      if (res.ok) {
        const data = await res.json();
        setActiveChain(data);
        setEditedOutput(data.step_output);
      }
    } catch (err) { console.error(err); }
    setChainLoading(false);
  };

  const handleNextStep = async () => {
    if (!activeChain) return;
    setChainLoading(true);
    try {
      let token = 'dev_mock_token_7128';
      try { token = await getToken() || token; } catch {}
      const res = await fetch(`${API}/workflows/chain/next`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ chain_id: activeChain.chain_id, edited_output: editedOutput })
      });
      if (res.ok) {
        const data = await res.json();
        setActiveChain(data);
        if (data.status !== 'completed') setEditedOutput(data.step_output);
      }
    } catch (err) { console.error(err); }
    setChainLoading(false);
  };

  const resetWorkflow = () => {
    setSelectedTemplate(null);
    setInitialInput('');
    setActiveChain(null);
    setEditedOutput('');
    setShowModal(false);
  };

  const filtered = templates.filter(t => {
    const matchCategory = activeCategory === 'all' || t.category === activeCategory;
    const matchSearch = !searchQuery || t.name.toLowerCase().includes(searchQuery.toLowerCase()) || t.description.toLowerCase().includes(searchQuery.toLowerCase());
    return matchCategory && matchSearch;
  });

  const grouped = {};
  filtered.forEach(t => {
    if (!grouped[t.category]) grouped[t.category] = [];
    grouped[t.category].push(t);
  });

  /* ── Glass ── */
  const glass = {
    background: 'rgba(255,255,255,0.6)',
    backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)',
    border: '1px solid rgba(255,255,255,0.3)',
    boxShadow: '0 4px 24px rgba(0,0,0,0.04)',
  };

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      fontFamily: "'Inter', sans-serif",
      background: 'linear-gradient(160deg, #FAFAFA 0%, #F3F3F4 40%, #F0F0F1 100%)',
    }}>
      {/* Header */}
      <div style={{
        height: 52, padding: '0 32px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0,
        background: 'rgba(255,255,255,0.6)',
        backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)',
        borderBottom: '1px solid rgba(0,0,0,0.04)',
      }}>
        <span style={{ fontSize: 14, fontWeight: 600, color: '#0A0A0A', letterSpacing: '-0.02em' }}>Workflows</span>
        {activeChain && (
          <button onClick={resetWorkflow} style={{
            fontSize: 13, color: '#999', background: 'none', border: 'none', cursor: 'pointer',
            fontFamily: "'Inter', sans-serif",
          }}>New workflow</button>
        )}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: '28px 32px' }}>
        <div style={{ maxWidth: 1000, margin: '0 auto' }}>

          {!activeChain ? (
            <>
              {/* Search + category filter */}
              <div style={{ marginBottom: 28 }}>
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  padding: '10px 14px', borderRadius: 12,
                  ...glass,
                  marginBottom: 16,
                }}>
                  <Search style={{ width: 15, height: 15, color: '#BBB', flexShrink: 0 }} />
                  <input
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    placeholder={`Search ${templates.length} workflows...`}
                    style={{
                      flex: 1, border: 'none', outline: 'none', background: 'transparent',
                      fontSize: 14, color: '#0A0A0A', fontFamily: "'Inter', sans-serif",
                    }}
                  />
                  {searchQuery && (
                    <button onClick={() => setSearchQuery('')} style={{
                      background: 'none', border: 'none', cursor: 'pointer', padding: 0,
                      display: 'flex', color: '#CCC',
                    }}>
                      <X style={{ width: 14, height: 14 }} />
                    </button>
                  )}
                </div>

                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {['all', ...CATEGORIES].map(cat => {
                    const isActive = activeCategory === cat;
                    const label = cat === 'all' ? 'All' : cat;
                    const count = cat === 'all'
                      ? templates.length
                      : templates.filter(t => t.category === cat).length;
                    return (
                      <button key={cat} onClick={() => setActiveCategory(cat)} style={{
                        padding: '6px 14px', fontSize: 12, fontWeight: 500,
                        borderRadius: 100, cursor: 'pointer',
                        background: isActive ? '#0A0A0A' : 'rgba(255,255,255,0.5)',
                        color: isActive ? '#fff' : '#888',
                        border: isActive ? '1px solid #0A0A0A' : '1px solid rgba(0,0,0,0.06)',
                        transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
                        fontFamily: "'Inter', sans-serif",
                        backdropFilter: 'blur(8px)',
                        letterSpacing: '-0.01em',
                      }}>
                        {label} <span style={{ opacity: 0.5, marginLeft: 2 }}>{count}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Grouped workflows */}
              {Object.entries(grouped).map(([category, items]) => (
                <div key={category} style={{ marginBottom: 36 }}>
                  <h3 style={{
                    fontSize: 11, fontWeight: 600, color: '#BBB', letterSpacing: '0.06em',
                    textTransform: 'uppercase', marginBottom: 12, padding: '0 4px',
                  }}>
                    {category}
                  </h3>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
                    {items.map((t, i) => (
                      <button
                        key={t.id}
                        onClick={() => openWorkflow(t)}
                        style={{
                          textAlign: 'left', padding: '20px',
                          ...glass,
                          borderRadius: 14, cursor: 'pointer',
                          fontFamily: "'Inter', sans-serif",
                          transition: 'all 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
                          animationDelay: `${i * 30}ms`,
                        }}
                        onMouseEnter={e => {
                          e.currentTarget.style.transform = 'translateY(-2px)';
                          e.currentTarget.style.boxShadow = '0 8px 32px rgba(0,0,0,0.08)';
                          e.currentTarget.style.background = 'rgba(255,255,255,0.85)';
                        }}
                        onMouseLeave={e => {
                          e.currentTarget.style.transform = 'translateY(0)';
                          e.currentTarget.style.boxShadow = '0 4px 24px rgba(0,0,0,0.04)';
                          e.currentTarget.style.background = 'rgba(255,255,255,0.6)';
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                          <span style={{ fontSize: 14, fontWeight: 600, color: '#0A0A0A', letterSpacing: '-0.02em' }}>{t.name}</span>
                          <span style={{
                            fontSize: 10, fontWeight: 500, color: '#CCC',
                            background: 'rgba(0,0,0,0.03)', padding: '2px 8px', borderRadius: 100,
                          }}>{t.steps}s</span>
                        </div>
                        <p style={{ fontSize: 12.5, color: '#999', lineHeight: 1.5, margin: 0 }}>{t.description}</p>
                      </button>
                    ))}
                  </div>
                </div>
              ))}

              {filtered.length === 0 && (
                <div style={{ textAlign: 'center', padding: '60px 0' }}>
                  <p style={{ fontSize: 14, color: '#BBB' }}>No workflows match your search.</p>
                </div>
              )}
            </>
          ) : activeChain.status === 'completed' ? (
            <div style={{ maxWidth: 640, margin: '0 auto' }}>
              <div style={{ textAlign: 'center', marginBottom: 28 }}>
                <CheckCircle2 style={{ width: 36, height: 36, color: '#0A0A0A', margin: '0 auto 12px' }} />
                <h2 style={{ fontSize: 22, fontWeight: 600, color: '#0A0A0A', marginBottom: 4, letterSpacing: '-0.03em' }}>Completed</h2>
                <p style={{ fontSize: 13, color: '#888' }}>All steps finished.</p>
              </div>

              <div style={{ ...glass, borderRadius: 16, padding: 28, marginBottom: 20 }}>
                {Object.entries(activeChain.all_outputs).map(([stepId, output], idx) => (
                  <div key={stepId} style={{ marginBottom: idx < Object.entries(activeChain.all_outputs).length - 1 ? 24 : 0 }}>
                    <h4 style={{ fontSize: 11, fontWeight: 600, color: '#999', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                      Step {idx + 1}: {stepId}
                    </h4>
                    <div style={{ fontSize: 14, color: '#0A0A0A', lineHeight: 1.7, whiteSpace: 'pre-wrap' }} dangerouslySetInnerHTML={{ __html: output }} />
                    {idx < Object.entries(activeChain.all_outputs).length - 1 && (
                      <hr style={{ border: 'none', borderTop: '1px solid rgba(0,0,0,0.06)', margin: '24px 0 0' }} />
                    )}
                  </div>
                ))}
              </div>

              <button onClick={resetWorkflow} style={{
                width: '100%', padding: 14, background: '#0A0A0A', color: '#fff',
                border: 'none', borderRadius: 12, fontSize: 14, fontWeight: 600, cursor: 'pointer',
                fontFamily: "'Inter', sans-serif",
              }}>Start new workflow</button>
            </div>
          ) : (
            <div style={{ display: 'flex', gap: 24 }}>
              {/* Progress sidebar */}
              <div style={{ width: 200, flexShrink: 0 }}>
                <div style={{ position: 'sticky', top: 24, ...glass, borderRadius: 14, padding: 18 }}>
                  <h3 style={{ fontSize: 12, fontWeight: 600, color: '#0A0A0A', marginBottom: 14 }}>Progress</h3>
                  {Array.from({ length: activeChain.total_steps }).map((_, i) => (
                    <div key={i} style={{
                      display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10,
                      opacity: i <= activeChain.current_step ? 1 : 0.3,
                      transition: 'opacity 0.3s',
                    }}>
                      <div style={{
                        width: 22, height: 22, borderRadius: '50%',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: 11, fontWeight: 600,
                        background: i <= activeChain.current_step ? '#0A0A0A' : 'rgba(0,0,0,0.06)',
                        color: i <= activeChain.current_step ? '#fff' : '#999',
                        transition: 'all 0.3s',
                      }}>
                        {i < activeChain.current_step ? '✓' : i + 1}
                      </div>
                      <span style={{ fontSize: 12, fontWeight: i === activeChain.current_step ? 600 : 400, color: '#0A0A0A' }}>
                        {i === activeChain.current_step ? activeChain.step_title : `Step ${i + 1}`}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Main content */}
              <div style={{ flex: 1 }}>
                <div style={{ ...glass, borderRadius: 16, padding: 28 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                    <h3 style={{ fontSize: 18, fontWeight: 600, color: '#0A0A0A', margin: 0, letterSpacing: '-0.02em' }}>
                      Step {activeChain.current_step + 1}: {activeChain.step_title}
                    </h3>
                    <span style={{
                      fontSize: 11, fontWeight: 500, color: '#BBB',
                      background: 'rgba(0,0,0,0.03)', padding: '3px 10px', borderRadius: 100,
                    }}>Review & edit</span>
                  </div>

                  <textarea
                    value={editedOutput}
                    onChange={e => setEditedOutput(e.target.value)}
                    style={{
                      width: '100%', minHeight: 340, padding: 20, fontSize: 14,
                      background: 'rgba(0,0,0,0.02)', border: '1px solid rgba(0,0,0,0.06)',
                      borderRadius: 12, outline: 'none', lineHeight: 1.7, resize: 'vertical',
                      fontFamily: "'Inter', sans-serif", boxSizing: 'border-box',
                    }}
                  />

                  <button
                    onClick={handleNextStep}
                    disabled={chainLoading || !editedOutput.trim()}
                    style={{
                      marginTop: 16, width: '100%', padding: 14,
                      background: '#0A0A0A', color: '#fff', border: 'none',
                      borderRadius: 12, fontSize: 14, fontWeight: 600,
                      cursor: !chainLoading && editedOutput.trim() ? 'pointer' : 'default',
                      opacity: !chainLoading && editedOutput.trim() ? 1 : 0.4,
                      display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                      fontFamily: "'Inter', sans-serif",
                    }}
                  >
                    {chainLoading ? (
                      <><Loader2 style={{ width: 16, height: 16, animation: 'spin 1s linear infinite' }} /> Processing...</>
                    ) : activeChain.next_step ? (
                      <>Approve & continue <ChevronRight style={{ width: 16, height: 16 }} /></>
                    ) : (
                      <><CheckCircle2 style={{ width: 16, height: 16 }} /> Finalize</>
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ═══ MODAL — workflow launch popup ═══ */}
      {showModal && selectedTemplate && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 200,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'rgba(0,0,0,0.4)',
          backdropFilter: 'blur(6px)', WebkitBackdropFilter: 'blur(6px)',
          animation: 'fadeIn 0.2s ease-out',
        }}>
          <div ref={modalRef} style={{
            width: 540, maxWidth: '90vw', maxHeight: '80vh',
            background: 'rgba(255,255,255,0.92)',
            backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)',
            borderRadius: 20, padding: 32,
            border: '1px solid rgba(255,255,255,0.5)',
            boxShadow: '0 24px 80px rgba(0,0,0,0.15), 0 0 0 1px rgba(0,0,0,0.03)',
            animation: 'slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
            overflow: 'auto',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
              <div>
                <span style={{
                  fontSize: 11, fontWeight: 600, color: '#BBB', letterSpacing: '0.04em',
                  textTransform: 'uppercase',
                }}>
                  {selectedTemplate.category}
                </span>
                <h3 style={{
                  fontSize: 22, fontWeight: 650, color: '#0A0A0A', marginTop: 6,
                  letterSpacing: '-0.03em', lineHeight: 1.2,
                }}>
                  {selectedTemplate.name}
                </h3>
              </div>
              <button onClick={() => { setShowModal(false); setSelectedTemplate(null); }} style={{
                width: 32, height: 32, display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: 'rgba(0,0,0,0.04)', border: 'none', borderRadius: 8,
                cursor: 'pointer', color: '#999', transition: 'all 0.15s',
              }}
              onMouseEnter={e => e.currentTarget.style.background = 'rgba(0,0,0,0.08)'}
              onMouseLeave={e => e.currentTarget.style.background = 'rgba(0,0,0,0.04)'}
              >
                <X style={{ width: 16, height: 16 }} />
              </button>
            </div>

            <p style={{ fontSize: 14, color: '#888', marginBottom: 24, lineHeight: 1.55 }}>
              {selectedTemplate.description}
            </p>

            {/* Steps preview */}
            <div style={{
              display: 'flex', gap: 8, marginBottom: 24,
            }}>
              {Array.from({ length: selectedTemplate.steps }).map((_, i) => (
                <div key={i} style={{
                  flex: 1, height: 3, borderRadius: 2,
                  background: 'rgba(0,0,0,0.08)',
                }} />
              ))}
            </div>

            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#0A0A0A', marginBottom: 8 }}>
              Input
            </label>
            <textarea
              value={initialInput}
              onChange={e => setInitialInput(e.target.value)}
              placeholder="Paste the facts, notice text, or context here..."
              autoFocus
              style={{
                width: '100%', minHeight: 160, padding: 16, fontSize: 14,
                background: 'rgba(0,0,0,0.02)', border: '1px solid rgba(0,0,0,0.06)',
                borderRadius: 12, resize: 'vertical',
                outline: 'none', fontFamily: "'Inter', sans-serif", lineHeight: 1.6,
                boxSizing: 'border-box',
                transition: 'border-color 0.2s',
              }}
              onFocus={e => e.target.style.borderColor = 'rgba(0,0,0,0.15)'}
              onBlur={e => e.target.style.borderColor = 'rgba(0,0,0,0.06)'}
            />
            <button
              onClick={handleStartChain}
              disabled={!initialInput.trim() || chainLoading}
              style={{
                marginTop: 16, width: '100%', padding: '14px',
                background: '#0A0A0A', color: '#fff', border: 'none',
                borderRadius: 12, fontSize: 14, fontWeight: 600,
                cursor: initialInput.trim() && !chainLoading ? 'pointer' : 'default',
                opacity: initialInput.trim() && !chainLoading ? 1 : 0.3,
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                fontFamily: "'Inter', sans-serif",
                transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
              }}
            >
              {chainLoading
                ? <><Loader2 style={{ width: 16, height: 16, animation: 'spin 1s linear infinite' }} /> Starting...</>
                : <><Play style={{ width: 16, height: 16 }} /> Start {selectedTemplate.steps}-step workflow</>
              }
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
