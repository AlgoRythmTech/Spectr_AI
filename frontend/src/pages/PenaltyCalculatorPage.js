import React, { useState } from 'react';
import { Calculator, ArrowRight, AlertTriangle, CheckCircle, Copy, Check, Calendar } from 'lucide-react';
import api from '../services/api';

export default function PenaltyCalculatorPage() {
  const [returnType, setReturnType] = useState('gstr3b');
  const [dueDate, setDueDate] = useState('');
  const [filingDate, setFilingDate] = useState('');
  const [taxAmount, setTaxAmount] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const returnTypes = [
    { value: 'gstr1', label: 'GSTR-1 (Outward Supplies)' },
    { value: 'gstr3b', label: 'GSTR-3B (Monthly Return)' },
    { value: 'gstr9', label: 'GSTR-9 (Annual Return)' },
    { value: 'itr', label: 'Income Tax Return (ITR)' },
    { value: 'tds_return', label: 'TDS Return (24Q/26Q/27Q)' },
    { value: 'tds_deposit', label: 'TDS Deposit (Late Challan)' },
    { value: 'roc', label: 'ROC Filing (AOC-4/MGT-7)' },
  ];

  const handleCalculate = async () => {
    if (!dueDate || !filingDate) return;
    setLoading(true);
    try {
      const res = await api.post('/tools/penalty-calculator', {
        deadline_type: returnType,
        due_date: dueDate,
        actual_date: filingDate,
        tax_amount: parseFloat(taxAmount) || 0,
      });
      setResult(res.data);
    } catch (err) {
      setResult({ error: err.response?.data?.detail || 'Calculation failed' });
    }
    setLoading(false);
  };

  const copyResult = () => {
    if (!result || result.error) return;
    const text = `${result.deadline_type || result.return_type_label}\nDelay: ${result.days_late || result.delay_days} days\nLate Fee: Rs ${(result.late_fee || 0).toLocaleString('en-IN')}\nInterest: Rs ${(result.interest || 0).toLocaleString('en-IN')}\nTotal: Rs ${(result.total_exposure || result.total_penalty || 0).toLocaleString('en-IN')}\nLegal Basis: ${result.legal_basis || result.penalty_type || ''}`;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div style={{ height: '100%', overflow: 'auto', padding: '32px 40px' }}>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
          <div style={{ width: 36, height: 36, background: '#F5F5F5', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Calculator style={{ width: 18, height: 18, color: '#000' }} />
          </div>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 700, color: '#0A0A0A', margin: 0, letterSpacing: '-0.02em' }}>Deadline Penalty Calculator</h1>
            <p style={{ fontSize: 13, color: '#64748B', margin: 0 }}>GST, Income Tax, TDS &amp; ROC late filing penalties</p>
          </div>
        </div>
        <p style={{ fontSize: 13.5, color: '#6B7280', maxWidth: 640, lineHeight: 1.6 }}>
          Calculate exact late fees, interest, and penalties for missed filing deadlines.
          Includes legal basis citations under CGST Act, IT Act, and Companies Act.
        </p>
      </div>

      {/* Input Form */}
      <div style={{ maxWidth: 560, marginBottom: 24 }}>
        <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Return / Filing Type
        </label>
        <select value={returnType} onChange={e => setReturnType(e.target.value)} style={{
          width: '100%', padding: '10px 14px', fontSize: 14, border: '1px solid #D1D5DB',
          borderRadius: 8, background: '#fff', outline: 'none', marginBottom: 16,
        }}>
          {returnTypes.map(rt => <option key={rt.value} value={rt.value}>{rt.label}</option>)}
        </select>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#6B7280', marginBottom: 4, textTransform: 'uppercase' }}>
              <Calendar style={{ width: 11, height: 11, display: 'inline', marginRight: 4 }} />Due Date
            </label>
            <input type="date" value={dueDate} onChange={e => setDueDate(e.target.value)} style={{
              width: '100%', padding: '10px 12px', fontSize: 14, border: '1px solid #D1D5DB', borderRadius: 8, outline: 'none',
            }} />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#6B7280', marginBottom: 4, textTransform: 'uppercase' }}>
              <Calendar style={{ width: 11, height: 11, display: 'inline', marginRight: 4 }} />Actual Filing Date
            </label>
            <input type="date" value={filingDate} onChange={e => setFilingDate(e.target.value)} style={{
              width: '100%', padding: '10px 12px', fontSize: 14, border: '1px solid #D1D5DB', borderRadius: 8, outline: 'none',
            }} />
          </div>
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#6B7280', marginBottom: 4, textTransform: 'uppercase' }}>
            Tax Liability Amount (Rs) — for interest calculation
          </label>
          <input type="number" value={taxAmount} onChange={e => setTaxAmount(e.target.value)} placeholder="e.g., 50000"
            style={{ width: '100%', padding: '10px 12px', fontSize: 14, border: '1px solid #D1D5DB', borderRadius: 8, outline: 'none', fontFamily: "'Inter', sans-serif" }} />
        </div>

        <button onClick={handleCalculate} disabled={loading || !dueDate || !filingDate} style={{
          padding: '10px 24px', borderRadius: 8, fontSize: 13, fontWeight: 600,
          background: '#0A0A0A', color: '#fff', border: 'none', cursor: 'pointer',
          opacity: loading || !dueDate || !filingDate ? 0.5 : 1,
          display: 'flex', alignItems: 'center', gap: 6,
        }}>
          {loading ? 'Calculating...' : <><ArrowRight style={{ width: 14, height: 14 }} /> Calculate Penalty</>}
        </button>
      </div>

      {/* Result */}
      {result && !result.error && (
        <div style={{ maxWidth: 560, padding: 24, borderRadius: 12, background: '#FAFAFA', border: '1px solid #E5E5E5' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <AlertTriangle style={{ width: 16, height: 16, color: '#000' }} />
              <span style={{ fontSize: 12, fontWeight: 700, color: '#000' }}>PENALTY COMPUTED</span>
            </div>
            <button onClick={copyResult} style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: '#6B7280' }}>
              {copied ? <Check style={{ width: 12, height: 12, color: '#000' }} /> : <Copy style={{ width: 12, height: 12 }} />}
              {copied ? 'Copied' : 'Copy'}
            </button>
          </div>

          <div style={{ padding: 14, background: '#fff', borderRadius: 8, border: '1px solid #E2E8F0', marginBottom: 12 }}>
            <div style={{ fontSize: 11, color: '#6B7280', fontWeight: 600, marginBottom: 4 }}>DELAY</div>
            <div style={{ fontSize: 32, fontWeight: 800, color: '#000', fontFamily: "'Inter', sans-serif" }}>
              {result.days_late ?? result.delay_days} days
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 16 }}>
            <div style={{ padding: 12, background: '#fff', borderRadius: 8, border: '1px solid #E5E5E5', textAlign: 'center' }}>
              <div style={{ fontSize: 10, color: '#999', fontWeight: 600, marginBottom: 4 }}>LATE FEE</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: '#000' }}>Rs {(result.late_fee ?? 0).toLocaleString('en-IN')}</div>
            </div>
            <div style={{ padding: 12, background: '#fff', borderRadius: 8, border: '1px solid #E5E5E5', textAlign: 'center' }}>
              <div style={{ fontSize: 10, color: '#999', fontWeight: 600, marginBottom: 4 }}>INTEREST</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: '#000' }}>Rs {(result.interest ?? 0).toLocaleString('en-IN')}</div>
            </div>
            <div style={{ padding: 12, background: '#fff', borderRadius: 8, border: '2px solid #000', textAlign: 'center' }}>
              <div style={{ fontSize: 10, color: '#000', fontWeight: 600, marginBottom: 4 }}>TOTAL</div>
              <div style={{ fontSize: 18, fontWeight: 800, color: '#000' }}>Rs {(result.total_exposure ?? result.total_penalty ?? 0).toLocaleString('en-IN')}</div>
            </div>
          </div>

          {(result.penalty_type || result.legal_basis) && (
            <div style={{ fontSize: 12, color: '#374151', padding: '10px 12px', background: '#F8FAFC', borderRadius: 6, border: '1px solid #E2E8F0', lineHeight: 1.6 }}>
              <span style={{ fontWeight: 700 }}>Legal Basis:</span> {result.penalty_type || result.legal_basis}
            </div>
          )}

          {result.tip && (
            <div style={{ fontSize: 12, color: '#000', padding: '8px 12px', background: '#FAFAFA', borderRadius: 6, border: '1px solid #E5E5E5', marginTop: 10, display: 'flex', alignItems: 'flex-start', gap: 6 }}>
              <CheckCircle style={{ width: 13, height: 13, flexShrink: 0, marginTop: 1 }} />
              {result.tip}
            </div>
          )}
        </div>
      )}

      {result && result.error && (
        <div style={{ maxWidth: 560, padding: 16, borderRadius: 10, background: '#FAFAFA', border: '1px solid #E5E5E5' }}>
          <div style={{ fontSize: 13, color: '#333' }}>{result.error}</div>
        </div>
      )}
    </div>
  );
}
