import React, { useState, useRef } from 'react';
import { Upload, FileSpreadsheet, AlertTriangle, CheckCircle, Download, ArrowRight } from 'lucide-react';
import api from '../services/api';

export default function TallyImportPage() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [fileName, setFileName] = useState('');
  const fileInputRef = useRef(null);

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    setLoading(true);
    setResult(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await api.post('/tools/tally-import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setResult(res.data);
    } catch (err) {
      setResult({ error: err.response?.data?.detail || 'Failed to parse Tally export' });
    }
    setLoading(false);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div style={{ height: '100%', overflow: 'auto', padding: '32px 40px' }}>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
          <div style={{ width: 40, height: 40, background: '#F0F0F0', borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Upload style={{ width: 20, height: 20, color: '#2563EB' }} />
          </div>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 700, color: '#0A0A0A', margin: 0, letterSpacing: '-0.02em' }}>Tally Import</h1>
            <p style={{ fontSize: 13, color: '#64748B', margin: 0 }}>Parse Tally Prime XML exports with auto-violation detection</p>
          </div>
        </div>
        <p style={{ fontSize: 13.5, color: '#6B7280', maxWidth: 640, lineHeight: 1.6 }}>
          Upload a Tally Prime XML export. Spectr parses all vouchers, auto-detects S.40A(3) cash payment violations
          (&gt;Rs 10,000) and S.269ST violations (&gt;Rs 2 lakh), and generates a clean transaction summary.
        </p>
      </div>

      {/* Upload Area */}
      {!result && (
        <div style={{ maxWidth: 480, marginBottom: 24 }}>
          <input ref={fileInputRef} type="file" accept=".xml" onChange={handleUpload} style={{ display: 'none' }} />
          <div
            onClick={() => !loading && fileInputRef.current?.click()}
            style={{
              padding: 48, textAlign: 'center', borderRadius: 12,
              border: '2px dashed #CBD5E1', background: '#F8FAFC',
              cursor: loading ? 'wait' : 'pointer', transition: 'all 0.15s',
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = '#2563EB'; e.currentTarget.style.background = '#F5F5F5'; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = '#CBD5E1'; e.currentTarget.style.background = '#F8FAFC'; }}
          >
            {loading ? (
              <>
                <div style={{ width: 24, height: 24, border: '3px solid #E2E8F0', borderTopColor: '#2563EB', borderRadius: '50%', animation: 'spin 0.8s linear infinite', margin: '0 auto 12px' }} />
                <p style={{ fontSize: 14, fontWeight: 600, color: '#374151' }}>Parsing {fileName}...</p>
              </>
            ) : (
              <>
                <FileSpreadsheet style={{ width: 40, height: 40, color: '#94A3B8', margin: '0 auto 12px' }} />
                <p style={{ fontSize: 14, fontWeight: 600, color: '#374151', marginBottom: 4 }}>Click to upload Tally XML</p>
                <p style={{ fontSize: 12, color: '#94A3B8' }}>Supports Tally Prime and Tally ERP 9 exports</p>
              </>
            )}
          </div>
        </div>
      )}

      {/* Results */}
      {result && !result.error && (
        <div style={{ maxWidth: 900 }}>
          <button onClick={() => setResult(null)} style={{
            padding: '6px 14px', fontSize: 12, fontWeight: 600, color: '#6B7280',
            background: '#F5F7FA', border: '1px solid #E2E8F0', borderRadius: 6, cursor: 'pointer', marginBottom: 16,
          }}>
            Upload Another File
          </button>

          {/* Stats */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 12, marginBottom: 24 }}>
            <div style={{ padding: 16, background: '#FAFAFA', borderRadius: 10, border: '1px solid #E5E5E5', textAlign: 'center' }}>
              <div style={{ fontSize: 10, color: '#000', fontWeight: 600, marginBottom: 4 }}>TOTAL VOUCHERS</div>
              <div style={{ fontSize: 28, fontWeight: 800, color: '#0A0A0A' }}>{result.total_vouchers || 0}</div>
            </div>
            <div style={{ padding: 16, background: '#F5F5F5', borderRadius: 10, border: '1px solid #E5E5E5', textAlign: 'center' }}>
              <div style={{ fontSize: 10, color: '#1E40AF', fontWeight: 600, marginBottom: 4 }}>TOTAL AMOUNT</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: '#0A0A0A' }}>Rs {result.total_amount?.toLocaleString('en-IN') || '0'}</div>
            </div>
            <div style={{ padding: 16, background: result.violations_40a3 > 0 ? '#FAFAFA' : '#FAFAFA', borderRadius: 10, border: `1px solid ${result.violations_40a3 > 0 ? '#E5E5E5' : '#E5E5E5'}`, textAlign: 'center' }}>
              <div style={{ fontSize: 10, color: result.violations_40a3 > 0 ? '#333' : '#000', fontWeight: 600, marginBottom: 4 }}>S.40A(3) VIOLATIONS</div>
              <div style={{ fontSize: 28, fontWeight: 800, color: result.violations_40a3 > 0 ? '#000' : '#000' }}>{result.violations_40a3 || 0}</div>
            </div>
            <div style={{ padding: 16, background: result.violations_269st > 0 ? '#FAFAFA' : '#FAFAFA', borderRadius: 10, border: `1px solid ${result.violations_269st > 0 ? '#E5E5E5' : '#E5E5E5'}`, textAlign: 'center' }}>
              <div style={{ fontSize: 10, color: result.violations_269st > 0 ? '#333' : '#000', fontWeight: 600, marginBottom: 4 }}>S.269ST VIOLATIONS</div>
              <div style={{ fontSize: 28, fontWeight: 800, color: result.violations_269st > 0 ? '#000' : '#000' }}>{result.violations_269st || 0}</div>
            </div>
          </div>

          {/* Violations Detail */}
          {result.violation_details && result.violation_details.length > 0 && (
            <div style={{ marginBottom: 24 }}>
              <h3 style={{ fontSize: 14, fontWeight: 700, color: '#333', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
                <AlertTriangle style={{ width: 15, height: 15 }} /> Flagged Violations
              </h3>
              <div style={{ borderRadius: 10, border: '1px solid #E5E5E5', overflow: 'hidden' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ background: '#FAFAFA' }}>
                      <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, borderBottom: '2px solid #E5E5E5' }}>Date</th>
                      <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, borderBottom: '2px solid #E5E5E5' }}>Party</th>
                      <th style={{ padding: '8px 12px', textAlign: 'right', fontWeight: 600, borderBottom: '2px solid #E5E5E5' }}>Amount</th>
                      <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, borderBottom: '2px solid #E5E5E5' }}>Violation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.violation_details.map((v, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid #F5F5F5' }}>
                        <td style={{ padding: '8px 12px', fontFamily: "'Inter', sans-serif" }}>{v.date}</td>
                        <td style={{ padding: '8px 12px' }}>{v.party}</td>
                        <td style={{ padding: '8px 12px', textAlign: 'right', fontWeight: 700, color: '#000', fontFamily: "'Inter', sans-serif" }}>Rs {v.amount?.toLocaleString('en-IN')}</td>
                        <td style={{ padding: '8px 12px' }}>
                          <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 6px', borderRadius: 4, background: '#F5F5F5', color: '#333' }}>{v.section}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Transaction Summary */}
          {result.transactions && result.transactions.length > 0 && (
            <div>
              <h3 style={{ fontSize: 14, fontWeight: 700, color: '#374151', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
                <CheckCircle style={{ width: 15, height: 15, color: '#000' }} /> Parsed Transactions ({result.transactions.length})
              </h3>
              <div style={{ borderRadius: 10, border: '1px solid #E2E8F0', overflow: 'hidden', maxHeight: 400, overflowY: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead style={{ position: 'sticky', top: 0 }}>
                    <tr style={{ background: '#F5F7FA' }}>
                      <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, borderBottom: '2px solid #E2E8F0' }}>Date</th>
                      <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, borderBottom: '2px solid #E2E8F0' }}>Type</th>
                      <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, borderBottom: '2px solid #E2E8F0' }}>Party</th>
                      <th style={{ padding: '8px 12px', textAlign: 'right', fontWeight: 600, borderBottom: '2px solid #E2E8F0' }}>Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.transactions.slice(0, 100).map((t, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid #F1F5F9' }}>
                        <td style={{ padding: '6px 12px', fontFamily: "'Inter', sans-serif", fontSize: 12 }}>{t.date}</td>
                        <td style={{ padding: '6px 12px' }}>{t.voucher_type}</td>
                        <td style={{ padding: '6px 12px' }}>{t.party}</td>
                        <td style={{ padding: '6px 12px', textAlign: 'right', fontFamily: "'Inter', sans-serif", fontWeight: 600 }}>Rs {t.amount?.toLocaleString('en-IN')}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {result.transactions.length > 100 && (
                <p style={{ fontSize: 11, color: '#94A3B8', marginTop: 8 }}>Showing first 100 of {result.transactions.length} transactions</p>
              )}
            </div>
          )}
        </div>
      )}

      {result && result.error && (
        <div style={{ maxWidth: 480, padding: 16, borderRadius: 10, background: '#FAFAFA', border: '1px solid #E5E5E5' }}>
          <div style={{ fontSize: 13, color: '#333' }}>{result.error}</div>
        </div>
      )}
    </div>
  );
}
