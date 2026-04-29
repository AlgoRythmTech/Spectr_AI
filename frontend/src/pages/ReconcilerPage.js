import React, { useState } from 'react';
import { Upload, FileDown, CheckCircle, AlertTriangle, ArrowRightLeft, FileSpreadsheet, Download, ChevronDown } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const API = process.env.REACT_APP_BACKEND_URL ? `${process.env.REACT_APP_BACKEND_URL}/api` : '/api';

export default function ReconcilerPage() {
  const { user } = useAuth();
  const [purchaseFile, setPurchaseFile] = useState(null);
  const [gstr2bFile, setGstr2bFile] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [activeTab, setActiveTab] = useState('summary');

  const handleProcess = async () => {
    if (!purchaseFile || !gstr2bFile) return;
    setProcessing(true);
    setResult(null);

    const formData = new FormData();
    formData.append('purchase_file', purchaseFile);
    formData.append('gstr2b_file', gstr2bFile);

    try {
      const res = await fetch(`${API}/tools/reconcile-gstr2b`, {
        method: 'POST',
        credentials: 'include',
        body: formData
      });
      if (res.ok) {
        setResult(await res.json());
        setActiveTab('summary');
      } else {
        alert("Reconciliation failed. Please check your Excel file formats.");
      }
    } catch (err) {
      console.error(err);
      alert("Error reaching reconciliation engine.");
    }
    setProcessing(false);
  };

  const matchRate = result ? Math.round(((result.exact_matches || 0) + (result.fuzzy_matches || 0)) / Math.max(result.total_invoices || 1, 1) * 100) : 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'linear-gradient(160deg, #FAFAFA 0%, #F3F3F4 40%, #F0F0F1 100%)' }} data-testid="reconciler-page">
      {/* Header */}
      <div style={{ height: 64, borderBottom: '1px solid rgba(0,0,0,0.06)', padding: '0 32px', display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0, background: 'transparent' }}>
        <div style={{ width: 36, height: 36, background: '#F5F5F5', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <ArrowRightLeft style={{ width: 18, height: 18, color: '#0A0A0A' }} />
        </div>
        <div>
          <h1 style={{ fontSize: 17, fontWeight: 700, color: '#0A0A0A', margin: 0, letterSpacing: '-0.02em' }}>GSTR-2B Reconciler</h1>
          <p style={{ fontSize: 11, color: '#64748B', margin: 0 }}>3-pass matching: Exact, Fuzzy (75%+), Amount-based</p>
        </div>
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 32 }}>
        {!result ? (
          <div style={{ maxWidth: 700, margin: '0 auto' }}>
            <p style={{ fontSize: 14, color: '#6B7280', marginBottom: 28, lineHeight: 1.6 }}>
              Upload your client's <strong>Purchase Register</strong> (from Tally/books) and the <strong>GSTR-2B</strong> (from GST portal).
              Spectr will reconcile using 3-pass matching and identify every ITC mismatch.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 28 }}>
              {/* Purchase Upload */}
              <label style={{
                display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                padding: 32, borderRadius: 16, border: '1px solid rgba(255,255,255,0.3)',
                background: purchaseFile ? 'rgba(255,255,255,0.85)' : 'rgba(255,255,255,0.6)', backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)',
                boxShadow: '0 4px 24px rgba(0,0,0,0.04)', cursor: 'pointer', transition: 'all 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
                minHeight: 180,
              }}>
                <input type="file" accept=".xlsx,.xls,.csv" onChange={(e) => setPurchaseFile(e.target.files[0])} style={{ display: 'none' }} />
                <FileSpreadsheet style={{ width: 32, height: 32, color: purchaseFile ? '#0A0A0A' : '#94A3B8', marginBottom: 10 }} />
                <span style={{ fontSize: 14, fontWeight: 600, color: purchaseFile ? '#0A0A0A' : '#374151', marginBottom: 4 }}>
                  {purchaseFile ? purchaseFile.name : 'Purchase Register'}
                </span>
                <span style={{ fontSize: 12, color: '#94A3B8' }}>
                  {purchaseFile ? `${(purchaseFile.size / 1024).toFixed(0)} KB` : 'Click to upload (.xlsx, .csv)'}
                </span>
              </label>

              {/* GSTR-2B Upload */}
              <label style={{
                display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                padding: 32, borderRadius: 16, border: '1px solid rgba(255,255,255,0.3)',
                background: gstr2bFile ? 'rgba(255,255,255,0.85)' : 'rgba(255,255,255,0.6)', backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)',
                boxShadow: '0 4px 24px rgba(0,0,0,0.04)', cursor: 'pointer', transition: 'all 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
                minHeight: 180,
              }}>
                <input type="file" accept=".xlsx,.xls,.csv" onChange={(e) => setGstr2bFile(e.target.files[0])} style={{ display: 'none' }} />
                <FileDown style={{ width: 32, height: 32, color: gstr2bFile ? '#0A0A0A' : '#94A3B8', marginBottom: 10 }} />
                <span style={{ fontSize: 14, fontWeight: 600, color: gstr2bFile ? '#0A0A0A' : '#374151', marginBottom: 4 }}>
                  {gstr2bFile ? gstr2bFile.name : 'GSTR-2B Export'}
                </span>
                <span style={{ fontSize: 12, color: '#94A3B8' }}>
                  {gstr2bFile ? `${(gstr2bFile.size / 1024).toFixed(0)} KB` : 'Click to upload (.xlsx, .csv)'}
                </span>
              </label>
            </div>

            <button onClick={handleProcess} disabled={processing || !purchaseFile || !gstr2bFile} style={{
              width: '100%', padding: '14px 24px', borderRadius: 100, fontSize: 14, fontWeight: 700,
              background: '#0A0A0A', color: '#fff', border: 'none', cursor: 'pointer',
              opacity: processing || !purchaseFile || !gstr2bFile ? 0.5 : 1,
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
            }}>
              {processing ? (
                <>
                  <div style={{ width: 16, height: 16, border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
                  Running 3-Pass Reconciliation...
                </>
              ) : 'Execute ITC Reconciliation'}
            </button>
          </div>
        ) : (
          <div style={{ maxWidth: 1000, margin: '0 auto' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
              <button onClick={() => { setResult(null); setPurchaseFile(null); setGstr2bFile(null); }} style={{
                padding: '6px 14px', fontSize: 12, fontWeight: 600, color: '#6B7280',
                background: 'rgba(255,255,255,0.6)', border: '1px solid rgba(0,0,0,0.06)', borderRadius: 100, cursor: 'pointer',
                backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)', transition: 'all 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
              }}>
                New Reconciliation
              </button>
            </div>

            {/* Dashboard Stats */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12, marginBottom: 24 }}>
              <div style={{ padding: 16, background: 'rgba(255,255,255,0.6)', backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)', borderRadius: 14, border: '1px solid rgba(255,255,255,0.3)', boxShadow: '0 4px 24px rgba(0,0,0,0.04)', textAlign: 'center', transition: 'all 0.25s cubic-bezier(0.16, 1, 0.3, 1)' }}>
                <div style={{ fontSize: 10, color: '#6B7280', fontWeight: 600, marginBottom: 4 }}>TOTAL INVOICES</div>
                <div style={{ fontSize: 28, fontWeight: 800, color: '#0A0A0A' }}>{result.total_invoices || 0}</div>
              </div>
              <div style={{ padding: 16, background: 'rgba(255,255,255,0.6)', backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)', borderRadius: 14, border: '1px solid rgba(255,255,255,0.3)', boxShadow: '0 4px 24px rgba(0,0,0,0.04)', textAlign: 'center', transition: 'all 0.25s cubic-bezier(0.16, 1, 0.3, 1)' }}>
                <div style={{ fontSize: 10, color: '#000', fontWeight: 600, marginBottom: 4 }}>EXACT MATCH</div>
                <div style={{ fontSize: 28, fontWeight: 800, color: '#000' }}>{result.exact_matches || 0}</div>
              </div>
              <div style={{ padding: 16, background: 'rgba(255,255,255,0.6)', backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)', borderRadius: 14, border: '1px solid rgba(255,255,255,0.3)', boxShadow: '0 4px 24px rgba(0,0,0,0.04)', textAlign: 'center', transition: 'all 0.25s cubic-bezier(0.16, 1, 0.3, 1)' }}>
                <div style={{ fontSize: 10, color: '#0A0A0A', fontWeight: 600, marginBottom: 4 }}>FUZZY MATCH</div>
                <div style={{ fontSize: 28, fontWeight: 800, color: '#0A0A0A' }}>{result.fuzzy_matches || 0}</div>
              </div>
              <div style={{ padding: 16, background: 'rgba(255,255,255,0.6)', backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)', borderRadius: 14, border: '1px solid rgba(255,255,255,0.3)', boxShadow: '0 4px 24px rgba(0,0,0,0.04)', textAlign: 'center', transition: 'all 0.25s cubic-bezier(0.16, 1, 0.3, 1)' }}>
                <div style={{ fontSize: 10, color: '#333', fontWeight: 600, marginBottom: 4 }}>ITC AT RISK</div>
                <div style={{ fontSize: 28, fontWeight: 800, color: '#000' }}>{result.unmatched_pr?.length || result.discrepancies || 0}</div>
              </div>
              <div style={{ padding: 16, background: 'rgba(255,255,255,0.6)', backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)', borderRadius: 14, border: '1px solid rgba(255,255,255,0.3)', boxShadow: '0 4px 24px rgba(0,0,0,0.04)', textAlign: 'center', transition: 'all 0.25s cubic-bezier(0.16, 1, 0.3, 1)' }}>
                <div style={{ fontSize: 10, color: '#6B7280', fontWeight: 600, marginBottom: 4 }}>MATCH RATE</div>
                <div style={{ fontSize: 28, fontWeight: 800, color: matchRate >= 90 ? '#000' : matchRate >= 70 ? '#000' : '#000' }}>{matchRate}%</div>
              </div>
            </div>

            {/* Tabs */}
            <div style={{ display: 'flex', gap: 4, marginBottom: 16 }}>
              {[
                { key: 'summary', label: 'Summary' },
                { key: 'unmatched_pr', label: `ITC at Risk (${result.unmatched_pr?.length || 0})` },
                { key: 'unmatched_g2b', label: `Unclaimed ITC (${result.unmatched_g2b?.length || 0})` },
                { key: 'fuzzy', label: `Fuzzy Matches (${result.fuzzy_matches || 0})` },
              ].map(tab => (
                <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{
                  padding: '7px 16px', borderRadius: 100, fontSize: 12, fontWeight: 600, cursor: 'pointer',
                  background: activeTab === tab.key ? '#0A0A0A' : 'rgba(255,255,255,0.6)',
                  color: activeTab === tab.key ? '#fff' : '#4B5563',
                  border: activeTab === tab.key ? 'none' : '1px solid rgba(0,0,0,0.06)',
                  transition: 'all 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
                }}>{tab.label}</button>
              ))}
            </div>

            {/* Summary Tab */}
            {activeTab === 'summary' && (
              <div style={{ padding: 24, background: 'rgba(255,255,255,0.6)', backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)', borderRadius: 14, border: '1px solid rgba(255,255,255,0.3)', boxShadow: '0 4px 24px rgba(0,0,0,0.04)', overflow: 'hidden' }}>
                <h3 style={{ fontSize: 15, fontWeight: 700, color: '#0A0A0A', marginBottom: 16 }}>Reconciliation Summary</h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                  <div>
                    <div style={{ fontSize: 12, color: '#6B7280', fontWeight: 600, marginBottom: 8 }}>Match Breakdown</div>
                    <table style={{ width: '100%', fontSize: 13, borderCollapse: 'collapse' }}>
                      <tbody>
                        {[
                          ['Pass 1: Exact Match', result.exact_matches || 0, '#000'],
                          ['Pass 2: Fuzzy Match (75%+)', result.fuzzy_matches || 0, '#0A0A0A'],
                          ['Pass 3: Amount Match', result.amount_matches || 0, '#0A0A0A'],
                          ['Unmatched (ITC Risk)', result.unmatched_pr?.length || result.discrepancies || 0, '#000'],
                        ].map(([label, val, color], i) => (
                          <tr key={i} style={{ borderBottom: '1px solid #F1F5F9' }}>
                            <td style={{ padding: '8px 0', color: '#374151' }}>{label}</td>
                            <td style={{ padding: '8px 0', textAlign: 'right', fontWeight: 700, color, fontFamily: "'Inter', sans-serif" }}>{val}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {result.vendor_risk && result.vendor_risk.length > 0 && (
                    <div>
                      <div style={{ fontSize: 12, color: '#6B7280', fontWeight: 600, marginBottom: 8 }}>Top Vendor Risk</div>
                      <table style={{ width: '100%', fontSize: 13, borderCollapse: 'collapse' }}>
                        <tbody>
                          {result.vendor_risk.slice(0, 5).map((v, i) => (
                            <tr key={i} style={{ borderBottom: '1px solid #F1F5F9' }}>
                              <td style={{ padding: '6px 0', color: '#374151', maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{v.gstin || v.vendor}</td>
                              <td style={{ padding: '6px 0', textAlign: 'right', fontWeight: 600, color: '#000', fontFamily: "'Inter', sans-serif" }}>
                                {v.mismatches || v.risk_count} issues
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Unmatched PR (ITC at Risk) */}
            {activeTab === 'unmatched_pr' && (
              <div style={{ borderRadius: 14, border: '1px solid rgba(0,0,0,0.06)', overflow: 'hidden', background: 'rgba(255,255,255,0.6)', backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)', boxShadow: '0 4px 24px rgba(0,0,0,0.04)' }}>
                {result.unmatched_pr && result.unmatched_pr.length > 0 ? (
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                    <thead>
                      <tr style={{ background: '#FAFAFA' }}>
                        <th style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 600, borderBottom: '2px solid rgba(0,0,0,0.06)' }}>GSTIN</th>
                        <th style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 600, borderBottom: '2px solid rgba(0,0,0,0.06)' }}>Invoice No</th>
                        <th style={{ padding: '10px 12px', textAlign: 'right', fontWeight: 600, borderBottom: '2px solid rgba(0,0,0,0.06)' }}>Tax Amount</th>
                        <th style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 600, borderBottom: '2px solid rgba(0,0,0,0.06)' }}>Reason</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.unmatched_pr.slice(0, 100).map((r, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid #F5F5F5' }}>
                          <td style={{ padding: '8px 12px', fontFamily: "'Inter', sans-serif", fontSize: 12 }}>{r.gstin || '-'}</td>
                          <td style={{ padding: '8px 12px', fontWeight: 600 }}>{r.invoice_no || '-'}</td>
                          <td style={{ padding: '8px 12px', textAlign: 'right', fontWeight: 700, color: '#000', fontFamily: "'Inter', sans-serif" }}>
                            {r.tax_amount ? `Rs ${r.tax_amount.toLocaleString('en-IN')}` : '-'}
                          </td>
                          <td style={{ padding: '8px 12px', color: '#6B7280' }}>{r.reason || 'Not in GSTR-2B'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div style={{ padding: 32, textAlign: 'center', color: '#000' }}>
                    <CheckCircle style={{ width: 24, height: 24, margin: '0 auto 8px' }} />
                    <p style={{ fontSize: 14, fontWeight: 600 }}>No ITC at risk. All purchase invoices matched.</p>
                  </div>
                )}
              </div>
            )}

            {/* Unmatched G2B (Unclaimed ITC) */}
            {activeTab === 'unmatched_g2b' && (
              <div style={{ borderRadius: 14, border: '1px solid rgba(0,0,0,0.06)', overflow: 'hidden', background: 'rgba(255,255,255,0.6)', backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)', boxShadow: '0 4px 24px rgba(0,0,0,0.04)' }}>
                {result.unmatched_g2b && result.unmatched_g2b.length > 0 ? (
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                    <thead>
                      <tr style={{ background: '#F5F5F5' }}>
                        <th style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 600, borderBottom: '2px solid rgba(0,0,0,0.06)' }}>GSTIN</th>
                        <th style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 600, borderBottom: '2px solid rgba(0,0,0,0.06)' }}>Invoice No</th>
                        <th style={{ padding: '10px 12px', textAlign: 'right', fontWeight: 600, borderBottom: '2px solid rgba(0,0,0,0.06)' }}>Tax Amount</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.unmatched_g2b.slice(0, 100).map((r, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid #F0F0F0' }}>
                          <td style={{ padding: '8px 12px', fontFamily: "'Inter', sans-serif", fontSize: 12 }}>{r.gstin || '-'}</td>
                          <td style={{ padding: '8px 12px', fontWeight: 600 }}>{r.invoice_no || '-'}</td>
                          <td style={{ padding: '8px 12px', textAlign: 'right', fontWeight: 700, color: '#0A0A0A', fontFamily: "'Inter', sans-serif" }}>
                            {r.tax_amount ? `Rs ${r.tax_amount.toLocaleString('en-IN')}` : '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div style={{ padding: 32, textAlign: 'center', color: '#6B7280' }}>
                    <p style={{ fontSize: 14 }}>No unclaimed ITC entries found.</p>
                  </div>
                )}
              </div>
            )}

            {/* Fuzzy Matches */}
            {activeTab === 'fuzzy' && (
              <div style={{ borderRadius: 14, border: '1px solid rgba(0,0,0,0.06)', overflow: 'hidden', background: 'rgba(255,255,255,0.6)', backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)', boxShadow: '0 4px 24px rgba(0,0,0,0.04)' }}>
                {result.fuzzy_match_details && result.fuzzy_match_details.length > 0 ? (
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                    <thead>
                      <tr style={{ background: '#F5F7FA' }}>
                        <th style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 600, borderBottom: '2px solid rgba(0,0,0,0.06)' }}>Purchase Invoice</th>
                        <th style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 600, borderBottom: '2px solid rgba(0,0,0,0.06)' }}>GSTR-2B Invoice</th>
                        <th style={{ padding: '10px 12px', textAlign: 'center', fontWeight: 600, borderBottom: '2px solid rgba(0,0,0,0.06)' }}>Similarity</th>
                        <th style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 600, borderBottom: '2px solid rgba(0,0,0,0.06)' }}>GSTIN</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.fuzzy_match_details.slice(0, 100).map((r, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid #F1F5F9' }}>
                          <td style={{ padding: '8px 12px', fontFamily: "'Inter', sans-serif", fontSize: 12 }}>{r.pr_invoice || '-'}</td>
                          <td style={{ padding: '8px 12px', fontFamily: "'Inter', sans-serif", fontSize: 12 }}>{r.g2b_invoice || '-'}</td>
                          <td style={{ padding: '8px 12px', textAlign: 'center' }}>
                            <span style={{
                              fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 4,
                              background: r.score >= 90 ? '#FAFAFA' : '#F5F5F5',
                              color: r.score >= 90 ? '#000' : '#333',
                            }}>{r.score}%</span>
                          </td>
                          <td style={{ padding: '8px 12px', fontFamily: "'Inter', sans-serif", fontSize: 11, color: '#6B7280' }}>{r.gstin || '-'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div style={{ padding: 32, textAlign: 'center', color: '#6B7280' }}>
                    <p style={{ fontSize: 14 }}>No fuzzy match details available.</p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
