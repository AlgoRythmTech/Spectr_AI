import React, { useState } from 'react';
import { Receipt, ArrowRight, AlertTriangle, CheckCircle, Copy, Check, Info } from 'lucide-react';
import api from '../services/api';

export default function TDSClassifierPage() {
  const [description, setDescription] = useState('');
  const [amount, setAmount] = useState('');
  const [payeeType, setPayeeType] = useState('individual');
  const [panAvailable, setPanAvailable] = useState(true);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleClassify = async () => {
    if (!description.trim()) return;
    setLoading(true);
    try {
      const res = await api.post('/tools/tds-classifier', {
        description: description.trim(),
        amount: parseFloat(amount) || 0,
        payee_type: payeeType,
        is_non_filer: !panAvailable,
      });
      setResult(res.data);
    } catch (err) {
      setResult({ error: err.response?.data?.detail || 'Classification failed' });
    }
    setLoading(false);
  };

  const copyResult = () => {
    if (!result || result.error) return;
    const text = `Section ${result.section} - ${result.title}\nRate: ${result.rate_percent ?? result.rate}%\nThreshold: Rs ${result.threshold?.toLocaleString('en-IN') || 'N/A'}\nTDS Amount: Rs ${result.tds_amount?.toLocaleString('en-IN') || 'N/A'}`;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const quickExamples = [
    { label: 'Contractor Payment', text: 'Payment to contractor for office renovation work', amt: '250000' },
    { label: 'Professional Fees', text: 'Legal consultation fees paid to advocate', amt: '50000' },
    { label: 'Rent Payment', text: 'Monthly office rent payment to landlord', amt: '60000' },
    { label: 'Commission', text: 'Sales commission paid to agent', amt: '30000' },
    { label: 'Software License', text: 'Annual software license fee (royalty)', amt: '100000' },
    { label: 'Freight Charges', text: 'Freight and transportation charges for goods', amt: '80000' },
  ];

  return (
    <div style={{ height: '100%', overflow: 'auto', padding: '32px 40px' }}>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
          <div style={{ width: 36, height: 36, background: '#F5F5F5', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Receipt style={{ width: 18, height: 18, color: '#000' }} />
          </div>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 700, color: '#0A0A0A', margin: 0, letterSpacing: '-0.02em' }}>TDS Section Classifier</h1>
            <p style={{ fontSize: 13, color: '#64748B', margin: 0 }}>Auto-detect the correct TDS section, rate &amp; threshold</p>
          </div>
        </div>
        <p style={{ fontSize: 13.5, color: '#6B7280', maxWidth: 640, lineHeight: 1.6 }}>
          Describe the payment and we'll identify the applicable TDS section under the Income Tax Act, 1961.
          Covers 194C, 194J, 194H, 194I, 194A, 194T, and 15+ other sections with S.206AB non-filer detection.
        </p>
      </div>

      {/* Input Form */}
      <div style={{ maxWidth: 600, marginBottom: 24 }}>
        <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Payment Description
        </label>
        <textarea
          value={description}
          onChange={e => setDescription(e.target.value)}
          placeholder="Describe the payment (e.g., 'Payment to contractor for building renovation')"
          style={{
            width: '100%', minHeight: 80, padding: 14, fontSize: 14,
            border: '1px solid #D1D5DB', borderRadius: 8, resize: 'vertical',
            outline: 'none', fontFamily: 'inherit', lineHeight: 1.5,
          }}
          onFocus={e => e.target.style.borderColor = '#000'}
          onBlur={e => e.target.style.borderColor = '#D1D5DB'}
        />

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginTop: 16 }}>
          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#6B7280', marginBottom: 4, textTransform: 'uppercase' }}>Amount (Rs)</label>
            <input
              type="number"
              value={amount}
              onChange={e => setAmount(e.target.value)}
              placeholder="e.g., 100000"
              style={{ width: '100%', padding: '10px 12px', fontSize: 14, border: '1px solid #D1D5DB', borderRadius: 8, outline: 'none', fontFamily: "'Inter', sans-serif" }}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#6B7280', marginBottom: 4, textTransform: 'uppercase' }}>Payee Type</label>
            <select value={payeeType} onChange={e => setPayeeType(e.target.value)}
              style={{ width: '100%', padding: '10px 12px', fontSize: 13, border: '1px solid #D1D5DB', borderRadius: 8, background: '#fff', outline: 'none' }}>
              <option value="individual">Individual / HUF</option>
              <option value="company">Company</option>
              <option value="firm">Partnership Firm</option>
              <option value="trust">Trust / AOP</option>
            </select>
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#6B7280', marginBottom: 4, textTransform: 'uppercase' }}>PAN Available?</label>
            <div style={{ display: 'flex', gap: 12, paddingTop: 8 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 13, cursor: 'pointer' }}>
                <input type="radio" checked={panAvailable} onChange={() => setPanAvailable(true)} /> Yes
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 13, cursor: 'pointer' }}>
                <input type="radio" checked={!panAvailable} onChange={() => setPanAvailable(false)} /> No
              </label>
            </div>
          </div>
        </div>

        <button onClick={handleClassify} disabled={loading || !description.trim()} style={{
          marginTop: 16, padding: '10px 24px', borderRadius: 8, fontSize: 13, fontWeight: 600,
          background: '#0A0A0A', color: '#fff', border: 'none', cursor: 'pointer',
          opacity: loading || !description.trim() ? 0.5 : 1,
          display: 'flex', alignItems: 'center', gap: 6,
        }}>
          {loading ? 'Classifying...' : <><ArrowRight style={{ width: 14, height: 14 }} /> Classify TDS Section</>}
        </button>
      </div>

      {/* Quick Examples */}
      <div style={{ marginBottom: 28 }}>
        <span style={{ fontSize: 11, color: '#94A3B8', fontWeight: 500, marginRight: 8 }}>Try:</span>
        {quickExamples.map((ex, i) => (
          <button key={i} onClick={() => { setDescription(ex.text); setAmount(ex.amt); }} style={{
            padding: '4px 10px', margin: '0 4px 4px 0', borderRadius: 5,
            fontSize: 12, fontWeight: 500, background: '#F5F5F5', border: '1px solid #E5E5E5',
            cursor: 'pointer', color: '#333',
          }}>{ex.label}</button>
        ))}
      </div>

      {/* Result */}
      {result && !result.error && (
        <div style={{
          maxWidth: 600, padding: 24, borderRadius: 12,
          background: '#FAFAFA', border: '1px solid #E5E5E5',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <CheckCircle style={{ width: 16, height: 16, color: '#000' }} />
              <span style={{ fontSize: 12, fontWeight: 700, color: '#000' }}>CLASSIFIED</span>
            </div>
            <button onClick={copyResult} style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: '#6B7280' }}>
              {copied ? <Check style={{ width: 12, height: 12, color: '#000' }} /> : <Copy style={{ width: 12, height: 12 }} />}
              {copied ? 'Copied' : 'Copy'}
            </button>
          </div>

          <div style={{ padding: 16, background: '#fff', borderRadius: 10, border: '1px solid #E2E8F0', marginBottom: 16 }}>
            <div style={{ fontSize: 28, fontWeight: 800, color: '#0A0A0A', marginBottom: 4, fontFamily: "'Inter', sans-serif" }}>
              Section {result.section}
            </div>
            <div style={{ fontSize: 15, fontWeight: 600, color: '#374151' }}>{result.title}</div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 16 }}>
            <div style={{ padding: 12, background: '#fff', borderRadius: 8, border: '1px solid #E2E8F0', textAlign: 'center' }}>
              <div style={{ fontSize: 10, color: '#6B7280', fontWeight: 600, marginBottom: 4 }}>RATE</div>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#0A0A0A' }}>{result.rate_percent ?? result.rate}%</div>
            </div>
            <div style={{ padding: 12, background: '#fff', borderRadius: 8, border: '1px solid #E2E8F0', textAlign: 'center' }}>
              <div style={{ fontSize: 10, color: '#6B7280', fontWeight: 600, marginBottom: 4 }}>THRESHOLD</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: '#0A0A0A' }}>Rs {result.threshold?.toLocaleString('en-IN') || 'N/A'}</div>
            </div>
            <div style={{ padding: 12, background: '#fff', borderRadius: 8, border: '1px solid #E2E8F0', textAlign: 'center' }}>
              <div style={{ fontSize: 10, color: '#6B7280', fontWeight: 600, marginBottom: 4 }}>TDS AMOUNT</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: '#000' }}>Rs {result.tds_amount?.toLocaleString('en-IN') || 'N/A'}</div>
            </div>
          </div>

          {!panAvailable && (
            <div style={{ fontSize: 12, color: '#000', padding: '8px 12px', background: '#FAFAFA', borderRadius: 6, border: '1px solid #E5E5E5', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
              <AlertTriangle style={{ width: 13, height: 13, flexShrink: 0 }} />
              S.206AA applies: TDS at 20% (or applicable rate, whichever is higher) since PAN is not available.
            </div>
          )}

          {result.note && (
            <div style={{ fontSize: 12, color: '#333', padding: '8px 12px', background: '#F5F5F5', borderRadius: 6, border: '1px solid #E5E5E5', display: 'flex', alignItems: 'center', gap: 6 }}>
              <Info style={{ width: 13, height: 13, flexShrink: 0 }} />
              {result.note}
            </div>
          )}
        </div>
      )}

      {result && result.error && (
        <div style={{ maxWidth: 600, padding: 16, borderRadius: 10, background: '#FAFAFA', border: '1px solid #E5E5E5' }}>
          <div style={{ fontSize: 13, color: '#333' }}>{result.error}</div>
        </div>
      )}
    </div>
  );
}
