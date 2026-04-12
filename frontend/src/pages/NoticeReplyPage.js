import React, { useState, useRef } from 'react';
import { FileWarning, Upload, ArrowRight, Download, Copy, Check, Loader2, AlertTriangle, CheckCircle, FileText } from 'lucide-react';
import api from '../services/api';

export default function NoticeReplyPage() {
  const [noticeText, setNoticeText] = useState('');
  const [clientName, setClientName] = useState('');
  const [additionalContext, setAdditionalContext] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState('reply');
  const fileInputRef = useRef(null);

  const handleGenerate = async () => {
    if (!noticeText.trim()) return;
    setLoading(true);
    setResult(null);
    try {
      const res = await api.post('/tools/notice-auto-reply', {
        notice_text: noticeText.trim(),
        client_name: clientName.trim(),
        additional_context: additionalContext.trim(),
      });
      setResult(res.data);
      setActiveTab('reply');
    } catch (err) {
      setResult({ error: err.response?.data?.detail || 'Failed to generate reply' });
    }
    setLoading(false);
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target.result;
      if (typeof text === 'string') {
        setNoticeText(text.substring(0, 50000));
      }
    };
    reader.readAsText(file);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const copyReply = () => {
    if (!result?.auto_reply) return;
    navigator.clipboard.writeText(result.auto_reply);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleExportWord = async () => {
    if (!result?.auto_reply) return;
    try {
      const res = await api.post('/export/word', {
        content: result.auto_reply,
        title: `Reply to ${result.notice_type || 'Notice'}`,
        format: 'docx',
      }, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = `Notice_Reply_${new Date().toISOString().slice(0, 10)}.docx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch {
      alert('Export failed. Check if backend is running.');
    }
  };

  return (
    <div style={{ height: '100%', overflow: 'auto', padding: '32px 40px' }}>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
          <div style={{ width: 40, height: 40, background: '#F0F0F0', borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <FileWarning style={{ width: 20, height: 20, color: '#0A0A0A' }} />
          </div>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 700, color: '#0A0A0A', margin: 0, letterSpacing: '-0.02em' }}>Notice Auto-Reply</h1>
            <p style={{ fontSize: 13, color: '#64748B', margin: 0 }}>Upload a tax notice, get a complete legal reply in seconds</p>
          </div>
        </div>
        <p style={{ fontSize: 13.5, color: '#6B7280', maxWidth: 680, lineHeight: 1.6 }}>
          Paste or upload a GST/Income Tax notice. Associate auto-extracts the notice type, demand amount, sections invoked,
          checks validity (limitation, DIN compliance), and drafts a formal 10-point legal reply with case law citations.
        </p>
      </div>

      <div style={{ display: 'flex', gap: 32, maxWidth: 1200 }}>
        {/* Left: Input Panel */}
        <div style={{ flex: '0 0 480px' }}>
          <div style={{ marginBottom: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: '#374151', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Notice Text
              </label>
              <div>
                <input ref={fileInputRef} type="file" accept=".txt,.pdf,.docx" onChange={handleFileUpload} style={{ display: 'none' }} />
                <button onClick={() => fileInputRef.current?.click()} style={{
                  padding: '4px 10px', fontSize: 11, fontWeight: 600, color: '#0A0A0A',
                  background: '#F0F0F0', border: '1px solid #E5E5E5', borderRadius: 5, cursor: 'pointer',
                  display: 'flex', alignItems: 'center', gap: 4,
                }}>
                  <Upload style={{ width: 11, height: 11 }} /> Upload File
                </button>
              </div>
            </div>
            <textarea
              value={noticeText}
              onChange={e => setNoticeText(e.target.value)}
              placeholder="Paste the full text of the notice here... (or upload a text file above)"
              style={{
                width: '100%', minHeight: 240, padding: 14, fontSize: 13,
                border: '1px solid #D1D5DB', borderRadius: 8, resize: 'vertical',
                outline: 'none', fontFamily: "'Inter', sans-serif", lineHeight: 1.6,
              }}
              onFocus={e => e.target.style.borderColor = '#0A0A0A'}
              onBlur={e => e.target.style.borderColor = '#D1D5DB'}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
            <div>
              <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#6B7280', marginBottom: 4, textTransform: 'uppercase' }}>Client Name</label>
              <input value={clientName} onChange={e => setClientName(e.target.value)} placeholder="e.g., M/s Sharma Enterprises"
                style={{ width: '100%', padding: '10px 12px', fontSize: 13, border: '1px solid #D1D5DB', borderRadius: 8, outline: 'none' }} />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#6B7280', marginBottom: 4, textTransform: 'uppercase' }}>Additional Instructions</label>
              <input value={additionalContext} onChange={e => setAdditionalContext(e.target.value)} placeholder="e.g., Client has paid 50% already"
                style={{ width: '100%', padding: '10px 12px', fontSize: 13, border: '1px solid #D1D5DB', borderRadius: 8, outline: 'none' }} />
            </div>
          </div>

          <button onClick={handleGenerate} disabled={loading || !noticeText.trim()} style={{
            width: '100%', padding: '12px 24px', borderRadius: 8, fontSize: 14, fontWeight: 700,
            background: '#0A0A0A', color: '#fff', border: 'none', cursor: 'pointer',
            opacity: loading || !noticeText.trim() ? 0.5 : 1,
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
          }}>
            {loading ? <><Loader2 style={{ width: 16, height: 16, animation: 'spin 1s linear infinite' }} /> Generating Reply (30-60s)...</> : <><ArrowRight style={{ width: 16, height: 16 }} /> Generate Legal Reply</>}
          </button>
        </div>

        {/* Right: Results Panel */}
        {result && !result.error && (
          <div style={{ flex: 1, minWidth: 0 }}>
            {/* Metadata Summary */}
            <div style={{ padding: 16, background: '#F8FAFC', borderRadius: 10, border: '1px solid #E2E8F0', marginBottom: 16 }}>
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 12 }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: '#fff', background: '#0A0A0A', padding: '3px 10px', borderRadius: 4 }}>
                  {result.notice_type || 'Unknown'}
                </span>
                {result.demand_amount > 0 && (
                  <span style={{ fontSize: 11, fontWeight: 700, color: '#000', background: '#FAFAFA', padding: '3px 10px', borderRadius: 4, border: '1px solid #E5E5E5' }}>
                    Demand: Rs {result.demand_amount?.toLocaleString('en-IN')}
                  </span>
                )}
                {result.financial_year && (
                  <span style={{ fontSize: 11, fontWeight: 600, color: '#374151', background: '#F3F4F6', padding: '3px 10px', borderRadius: 4 }}>
                    FY: {result.financial_year}
                  </span>
                )}
              </div>

              {/* Validity Check */}
              {result.validity_check && result.validity_check.challenge_grounds && (
                <div style={{ marginTop: 8 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#333', marginBottom: 6 }}>AUTO-DETECTED VALIDITY ISSUES:</div>
                  {result.validity_check.challenge_grounds.map((g, i) => (
                    <div key={i} style={{
                      display: 'flex', alignItems: 'flex-start', gap: 6, marginBottom: 4, fontSize: 12,
                      color: g.severity === 'high' ? '#000' : '#333',
                    }}>
                      <AlertTriangle style={{ width: 12, height: 12, flexShrink: 0, marginTop: 2 }} />
                      <span><strong>{g.ground}</strong>: {g.legal_basis}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Tab Bar */}
            <div style={{ display: 'flex', gap: 4, marginBottom: 12 }}>
              {['reply', 'metadata'].map(tab => (
                <button key={tab} onClick={() => setActiveTab(tab)} style={{
                  padding: '6px 16px', borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: 'pointer',
                  background: activeTab === tab ? '#0A0A0A' : '#F5F7FA',
                  color: activeTab === tab ? '#fff' : '#4B5563',
                  border: activeTab === tab ? 'none' : '1px solid #E2E8F0',
                  textTransform: 'capitalize',
                }}>{tab === 'reply' ? 'Auto-Draft Reply' : 'Extracted Metadata'}</button>
              ))}
            </div>

            {activeTab === 'reply' && (
              <div style={{ background: '#fff', border: '1px solid #E2E8F0', borderRadius: 10, overflow: 'hidden' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 16px', borderBottom: '1px solid #E2E8F0', background: '#F8FAFC' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <FileText style={{ width: 14, height: 14, color: '#0A0A0A' }} />
                    <span style={{ fontSize: 12, fontWeight: 600, color: '#374151' }}>Auto-Generated Legal Reply</span>
                  </div>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <button onClick={copyReply} style={{ padding: '4px 10px', fontSize: 11, fontWeight: 600, color: '#6B7280', background: '#F3F4F6', border: '1px solid #E2E8F0', borderRadius: 5, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
                      {copied ? <Check style={{ width: 11, height: 11, color: '#000' }} /> : <Copy style={{ width: 11, height: 11 }} />}
                      {copied ? 'Copied' : 'Copy'}
                    </button>
                    <button onClick={handleExportWord} style={{ padding: '4px 10px', fontSize: 11, fontWeight: 600, color: '#0A0A0A', background: '#F0F0F0', border: '1px solid #E5E5E5', borderRadius: 5, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
                      <Download style={{ width: 11, height: 11 }} /> Export DOCX
                    </button>
                  </div>
                </div>
                <div style={{ padding: 20, fontSize: 13.5, lineHeight: 1.8, color: '#1F2937', whiteSpace: 'pre-wrap', maxHeight: 600, overflowY: 'auto', fontFamily: "'Georgia', serif" }}>
                  {result.auto_reply}
                </div>
              </div>
            )}

            {activeTab === 'metadata' && result.notice_metadata && (
              <div style={{ background: '#fff', border: '1px solid #E2E8F0', borderRadius: 10, padding: 20 }}>
                <table style={{ width: '100%', fontSize: 13, borderCollapse: 'collapse' }}>
                  <tbody>
                    {Object.entries(result.notice_metadata).filter(([k]) => k !== 'notice_type').map(([key, value]) => (
                      <tr key={key} style={{ borderBottom: '1px solid #F1F5F9' }}>
                        <td style={{ padding: '8px 12px', fontWeight: 600, color: '#374151', textTransform: 'capitalize', width: 200 }}>
                          {key.replace(/_/g, ' ')}
                        </td>
                        <td style={{ padding: '8px 12px', color: '#1F2937', fontFamily: "'Inter', sans-serif" }}>
                          {typeof value === 'boolean' ? (value ? <CheckCircle style={{ width: 14, height: 14, color: '#000' }} /> : 'No') : String(value)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {result && result.error && (
          <div style={{ flex: 1, padding: 20, borderRadius: 10, background: '#FAFAFA', border: '1px solid #E5E5E5' }}>
            <div style={{ fontSize: 14, color: '#333' }}>{result.error}</div>
          </div>
        )}

        {!result && !loading && (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 300 }}>
            <div style={{ textAlign: 'center', color: '#94A3B8' }}>
              <FileWarning style={{ width: 48, height: 48, margin: '0 auto 16px', opacity: 0.3 }} />
              <p style={{ fontSize: 14, fontWeight: 500 }}>Paste notice text and click Generate</p>
              <p style={{ fontSize: 12, marginTop: 4 }}>The reply will appear here with case law citations</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
