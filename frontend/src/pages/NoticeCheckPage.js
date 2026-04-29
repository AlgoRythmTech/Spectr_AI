import React, { useState } from 'react';
import { FileText, ArrowRight, ShieldCheck, AlertTriangle, CheckCircle, XCircle, Copy, Check } from 'lucide-react';
import api from '../services/api';

export default function NoticeCheckPage() {
  const [noticeType, setNoticeType] = useState('73');
  const [noticeDate, setNoticeDate] = useState('');
  const [financialYear, setFinancialYear] = useState('');
  const [assessmentYear, setAssessmentYear] = useState('');
  const [hasDin, setHasDin] = useState(true);
  const [isFraud, setIsFraud] = useState(false);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const noticeTypes = [
    { value: '73', label: 'GST S.73 (Non-fraud SCN)' },
    { value: '74', label: 'GST S.74 (Fraud/Suppression SCN)' },
    { value: '143(2)', label: 'IT S.143(2) (Scrutiny Notice)' },
    { value: '148', label: 'IT S.148 / 148A (Reassessment)' },
  ];

  const handleCheck = async () => {
    if (!noticeDate) return;
    setLoading(true);
    try {
      const res = await api.post('/tools/notice-checker', {
        notice_type: noticeType,
        notice_date: noticeDate,
        financial_year: financialYear.trim(),
        assessment_year: assessmentYear.trim(),
        has_din: hasDin,
        is_fraud_alleged: isFraud,
      });
      setResult(res.data);
    } catch (err) {
      setResult({ error: err.response?.data?.detail || 'Validity check failed' });
    }
    setLoading(false);
  };

  const copyResult = () => {
    if (!result || result.error) return;
    let text = `Notice Validity Check\nType: ${noticeType}\nDate: ${noticeDate}\nOverall: ${result.overall_validity}\n`;
    if (result.challenge_grounds) {
      text += '\nChallenge Grounds:\n';
      result.challenge_grounds.forEach(g => { text += `- ${g.ground}: ${g.legal_basis}\n`; });
    }
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const validityColor = (v) => {
    if (v === 'Valid') return { bg: '#FAFAFA', border: '#E5E5E5', text: '#000', icon: CheckCircle };
    if (v === 'Potentially Invalid') return { bg: '#FAFAFA', border: '#E5E5E5', text: '#333', icon: XCircle };
    if (v === 'Challengeable') return { bg: '#F5F5F5', border: '#E5E5E5', text: '#333', icon: AlertTriangle };
    return { bg: '#F8FAFC', border: '#E2E8F0', text: '#374151', icon: ShieldCheck };
  };

  return (
    <div style={{ height: '100%', overflow: 'auto', padding: '32px 40px' }}>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
          <div style={{ width: 40, height: 40, background: '#ECFDF5', borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <ShieldCheck style={{ width: 20, height: 20, color: '#0A0A0A' }} />
          </div>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 700, color: '#0A0A0A', margin: 0, letterSpacing: '-0.02em' }}>Notice Validity Check</h1>
            <p style={{ fontSize: 13, color: '#64748B', margin: 0 }}>Check limitation, DIN compliance &amp; procedural validity</p>
          </div>
        </div>
        <p style={{ fontSize: 13.5, color: '#6B7280', maxWidth: 640, lineHeight: 1.6 }}>
          Enter the notice details to instantly check if it's within the statutory limitation period,
          compliant with DIN requirements (CBDT Circular 19/2019), and procedurally valid.
          Identifies automatic challenge grounds for quashing.
        </p>
      </div>

      {/* Input Form */}
      <div style={{ maxWidth: 560, marginBottom: 24 }}>
        <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Notice Type
        </label>
        <select value={noticeType} onChange={e => setNoticeType(e.target.value)} style={{
          width: '100%', padding: '10px 14px', fontSize: 14, border: '1px solid #D1D5DB',
          borderRadius: 8, background: '#fff', outline: 'none', marginBottom: 16,
        }}>
          {noticeTypes.map(nt => <option key={nt.value} value={nt.value}>{nt.label}</option>)}
        </select>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#6B7280', marginBottom: 4, textTransform: 'uppercase' }}>Notice Date</label>
            <input type="date" value={noticeDate} onChange={e => setNoticeDate(e.target.value)} style={{
              width: '100%', padding: '10px 12px', fontSize: 14, border: '1px solid #D1D5DB', borderRadius: 8, outline: 'none',
            }} />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#6B7280', marginBottom: 4, textTransform: 'uppercase' }}>Financial Year (e.g., 2022-23)</label>
            <input value={financialYear} onChange={e => setFinancialYear(e.target.value)} placeholder="2022-23"
              style={{ width: '100%', padding: '10px 12px', fontSize: 14, border: '1px solid #D1D5DB', borderRadius: 8, outline: 'none' }} />
          </div>
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#6B7280', marginBottom: 4, textTransform: 'uppercase' }}>Assessment Year (for IT notices)</label>
          <input value={assessmentYear} onChange={e => setAssessmentYear(e.target.value)} placeholder="e.g., 2023-24"
            style={{ width: '100%', padding: '10px 12px', fontSize: 14, border: '1px solid #D1D5DB', borderRadius: 8, outline: 'none' }} />
        </div>

        <div style={{ display: 'flex', gap: 24, marginBottom: 20 }}>
          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#6B7280', marginBottom: 6, textTransform: 'uppercase' }}>DIN on Notice?</label>
            <div style={{ display: 'flex', gap: 12 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 13, cursor: 'pointer' }}>
                <input type="radio" checked={hasDin} onChange={() => setHasDin(true)} /> Yes
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 13, cursor: 'pointer' }}>
                <input type="radio" checked={!hasDin} onChange={() => setHasDin(false)} /> No
              </label>
            </div>
          </div>
          {(noticeType === '74') && (
            <div>
              <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#6B7280', marginBottom: 6, textTransform: 'uppercase' }}>Fraud Alleged?</label>
              <div style={{ display: 'flex', gap: 12 }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 13, cursor: 'pointer' }}>
                  <input type="radio" checked={isFraud} onChange={() => setIsFraud(true)} /> Yes
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 13, cursor: 'pointer' }}>
                  <input type="radio" checked={!isFraud} onChange={() => setIsFraud(false)} /> No
                </label>
              </div>
            </div>
          )}
        </div>

        <button onClick={handleCheck} disabled={loading || !noticeDate} style={{
          padding: '10px 24px', borderRadius: 8, fontSize: 13, fontWeight: 600,
          background: '#0A0A0A', color: '#fff', border: 'none', cursor: 'pointer',
          opacity: loading || !noticeDate ? 0.5 : 1,
          display: 'flex', alignItems: 'center', gap: 6,
        }}>
          {loading ? 'Checking...' : <><ArrowRight style={{ width: 14, height: 14 }} /> Check Validity</>}
        </button>
      </div>

      {/* Result */}
      {result && !result.error && (() => {
        const vc = validityColor(result.overall_validity);
        const VIcon = vc.icon;
        return (
          <div style={{ maxWidth: 560 }}>
            {/* Overall Verdict */}
            <div style={{
              padding: 20, borderRadius: 12, marginBottom: 16,
              background: vc.bg, border: `1px solid ${vc.border}`,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <VIcon style={{ width: 20, height: 20, color: vc.text }} />
                  <span style={{ fontSize: 18, fontWeight: 800, color: vc.text }}>{result.overall_validity}</span>
                </div>
                <button onClick={copyResult} style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: '#6B7280' }}>
                  {copied ? <Check style={{ width: 12, height: 12, color: '#000' }} /> : <Copy style={{ width: 12, height: 12 }} />}
                  {copied ? 'Copied' : 'Copy'}
                </button>
              </div>

              {result.limitation_check && (
                <div style={{ fontSize: 13, color: '#374151', marginBottom: 8, lineHeight: 1.6 }}>
                  <strong>Limitation:</strong> {result.limitation_check}
                </div>
              )}

              {result.din_check && (
                <div style={{ fontSize: 13, color: '#374151', marginBottom: 8, lineHeight: 1.6 }}>
                  <strong>DIN Compliance:</strong> {result.din_check}
                </div>
              )}
            </div>

            {/* Challenge Grounds */}
            {result.challenge_grounds && result.challenge_grounds.length > 0 && (
              <div style={{ padding: 20, borderRadius: 12, background: '#fff', border: '1px solid #E2E8F0' }}>
                <h3 style={{ fontSize: 13, fontWeight: 700, color: '#0A0A0A', marginBottom: 12 }}>Challenge Grounds for Quashing:</h3>
                {result.challenge_grounds.map((g, i) => (
                  <div key={i} style={{
                    padding: 12, borderRadius: 8, marginBottom: 8,
                    background: g.severity === 'high' ? '#FAFAFA' : g.severity === 'medium' ? '#F5F5F5' : '#F8FAFC',
                    border: `1px solid ${g.severity === 'high' ? '#E5E5E5' : g.severity === 'medium' ? '#E5E5E5' : '#E2E8F0'}`,
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                      <span style={{
                        fontSize: 9, fontWeight: 700, padding: '2px 6px', borderRadius: 3, textTransform: 'uppercase',
                        background: g.severity === 'high' ? '#000' : g.severity === 'medium' ? '#000' : '#6B7280',
                        color: '#fff',
                      }}>{g.severity}</span>
                      <span style={{ fontSize: 13, fontWeight: 700, color: '#0A0A0A' }}>{g.ground}</span>
                    </div>
                    <div style={{ fontSize: 12, color: '#4B5563', lineHeight: 1.5 }}>{g.legal_basis}</div>
                    {g.case_law && <div style={{ fontSize: 11, color: '#6B7280', marginTop: 4, fontStyle: 'italic' }}>{g.case_law}</div>}
                  </div>
                ))}
              </div>
            )}

            {(!result.challenge_grounds || result.challenge_grounds.length === 0) && (
              <div style={{ padding: 16, borderRadius: 10, background: '#FAFAFA', border: '1px solid #E5E5E5', display: 'flex', alignItems: 'center', gap: 8 }}>
                <CheckCircle style={{ width: 16, height: 16, color: '#000' }} />
                <span style={{ fontSize: 13, color: '#000', fontWeight: 500 }}>No automatic challenge grounds detected. Notice appears procedurally valid.</span>
              </div>
            )}
          </div>
        );
      })()}

      {result && result.error && (
        <div style={{ maxWidth: 560, padding: 16, borderRadius: 10, background: '#FAFAFA', border: '1px solid #E5E5E5' }}>
          <div style={{ fontSize: 13, color: '#333' }}>{result.error}</div>
        </div>
      )}
    </div>
  );
}
