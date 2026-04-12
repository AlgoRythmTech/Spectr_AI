import React, { useState } from 'react';
import { ArrowLeftRight, ArrowRight, Copy, Check, AlertTriangle } from 'lucide-react';
import api from '../services/api';

export default function SectionMapperPage() {
  const [section, setSection] = useState('');
  const [direction, setDirection] = useState('old_to_new');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [batchInput, setBatchInput] = useState('');
  const [batchResults, setBatchResults] = useState([]);
  const [mode, setMode] = useState('single'); // 'single' | 'batch'

  const handleMap = async () => {
    if (!section.trim()) return;
    setLoading(true);
    try {
      const res = await api.post('/tools/section-mapper', { section: section.trim(), direction });
      setResult(res.data);
    } catch (err) {
      setResult({ found: false, error: err.response?.data?.detail || 'Failed to map section' });
    }
    setLoading(false);
  };

  const handleBatch = async () => {
    const sections = batchInput.split(/[,\n]/).map(s => s.trim()).filter(Boolean);
    if (!sections.length) return;
    setLoading(true);
    try {
      const res = await api.post('/tools/section-mapper/batch', { sections, direction });
      setBatchResults(res.data.mappings || []);
    } catch (err) {
      setBatchResults([]);
    }
    setLoading(false);
  };

  const copyResult = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const quickSections = ['302', '420', '498A', '376', '354', '438', '482', '138', '34', '120B', '506', '307'];

  return (
    <div style={{ height: '100%', overflow: 'auto', padding: '32px 40px' }}>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
          <div style={{ width: 36, height: 36, background: '#F5F5F5', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <ArrowLeftRight style={{ width: 18, height: 18, color: '#000' }} />
          </div>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 700, color: '#0A0A0A', margin: 0, letterSpacing: '-0.02em' }}>Section Mapper</h1>
            <p style={{ fontSize: 13, color: '#64748B', margin: 0 }}>IPC → BNS &middot; CrPC → BNSS &middot; Evidence Act → BSA</p>
          </div>
        </div>
        <p style={{ fontSize: 13.5, color: '#6B7280', maxWidth: 640, lineHeight: 1.6 }}>
          Instantly convert old criminal law section numbers to the new Bharatiya codes (effective July 1, 2024) and vice versa.
          Covers 120+ IPC sections, 45+ CrPC sections, and 35+ Evidence Act sections.
        </p>
      </div>

      {/* Mode Toggle */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        <button onClick={() => setMode('single')} style={{
          padding: '6px 16px', borderRadius: 6, fontSize: 13, fontWeight: 500, cursor: 'pointer',
          background: mode === 'single' ? '#000' : '#fff',
          color: mode === 'single' ? '#fff' : '#666',
          border: mode === 'single' ? '1px solid #000' : '1px solid #E5E5E5',
        }}>Single Section</button>
        <button onClick={() => setMode('batch')} style={{
          padding: '6px 16px', borderRadius: 6, fontSize: 13, fontWeight: 500, cursor: 'pointer',
          background: mode === 'batch' ? '#000' : '#fff',
          color: mode === 'batch' ? '#fff' : '#666',
          border: mode === 'batch' ? '1px solid #000' : '1px solid #E5E5E5',
        }}>Batch Convert</button>
      </div>

      {/* Direction Toggle */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', fontSize: 13 }}>
          <input type="radio" checked={direction === 'old_to_new'} onChange={() => setDirection('old_to_new')} />
          <span style={{ fontWeight: direction === 'old_to_new' ? 600 : 400 }}>Old → New</span>
          <span style={{ color: '#94A3B8', fontSize: 12 }}>(IPC/CrPC/IEA → BNS/BNSS/BSA)</span>
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', fontSize: 13 }}>
          <input type="radio" checked={direction === 'new_to_old'} onChange={() => setDirection('new_to_old')} />
          <span style={{ fontWeight: direction === 'new_to_old' ? 600 : 400 }}>New → Old</span>
          <span style={{ color: '#94A3B8', fontSize: 12 }}>(BNS/BNSS/BSA → IPC/CrPC/IEA)</span>
        </label>
      </div>

      {mode === 'single' ? (
        <>
          {/* Single Input */}
          <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
            <input
              value={section}
              onChange={e => setSection(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleMap()}
              placeholder="Enter section number (e.g., 420, 302, 438)"
              style={{
                flex: 1, maxWidth: 360, padding: '10px 14px', fontSize: 14,
                border: '1px solid #D1D5DB', borderRadius: 8,
                outline: 'none', transition: 'border 0.15s',
              }}
              onFocus={e => e.target.style.borderColor = '#000'}
              onBlur={e => e.target.style.borderColor = '#D1D5DB'}
            />
            <button onClick={handleMap} disabled={loading || !section.trim()} style={{
              padding: '10px 20px', borderRadius: 8, fontSize: 13, fontWeight: 600,
              background: '#0A0A0A', color: '#fff', border: 'none', cursor: 'pointer',
              opacity: loading || !section.trim() ? 0.5 : 1,
              display: 'flex', alignItems: 'center', gap: 6,
            }}>
              {loading ? 'Mapping...' : <><ArrowRight style={{ width: 14, height: 14 }} /> Convert</>}
            </button>
          </div>

          {/* Quick Access */}
          <div style={{ marginBottom: 24 }}>
            <span style={{ fontSize: 11, color: '#94A3B8', fontWeight: 500, marginRight: 8 }}>Quick:</span>
            {quickSections.map(s => (
              <button key={s} onClick={() => { setSection(s); }} style={{
                padding: '3px 10px', margin: '0 4px 4px 0', borderRadius: 5,
                fontSize: 12, fontWeight: 500, background: '#F5F7FA', border: '1px solid #E8ECF1',
                cursor: 'pointer', color: '#374151',
              }}>{s}</button>
            ))}
          </div>

          {/* Result */}
          {result && (
            <div style={{
              maxWidth: 560, padding: 20, borderRadius: 12,
              background: '#FAFAFA',
              border: `1px solid ${result.found ? '#E5E5E5' : '#E5E5E5'}`,
            }}>
              {result.found ? (
                <>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                    <span style={{ fontSize: 11, fontWeight: 600, color: '#000', background: '#F0F0F0', padding: '2px 8px', borderRadius: 4 }}>MAPPED</span>
                    <button onClick={() => copyResult(`${result.old_section} → ${result.new_section} (${result.title})`)} style={{
                      background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: '#6B7280',
                    }}>
                      {copied ? <Check style={{ width: 12, height: 12, color: '#000' }} /> : <Copy style={{ width: 12, height: 12 }} />}
                      {copied ? 'Copied' : 'Copy'}
                    </button>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                    <div style={{ padding: '8px 14px', background: '#fff', borderRadius: 8, border: '1px solid #D1D5DB' }}>
                      <div style={{ fontSize: 10, color: '#94A3B8', fontWeight: 500, marginBottom: 2 }}>OLD</div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: '#0A0A0A' }}>{result.old_section}</div>
                      <div style={{ fontSize: 11, color: '#6B7280' }}>{result.old_act?.split(',')[0]}</div>
                    </div>
                    <ArrowRight style={{ width: 20, height: 20, color: '#000', flexShrink: 0 }} />
                    <div style={{ padding: '8px 14px', background: '#fff', borderRadius: 8, border: '2px solid #000' }}>
                      <div style={{ fontSize: 10, color: '#000', fontWeight: 500, marginBottom: 2 }}>NEW</div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: '#0A0A0A' }}>{result.new_section}</div>
                      <div style={{ fontSize: 11, color: '#6B7280' }}>{result.new_act?.split(',')[0]}</div>
                    </div>
                  </div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 4 }}>{result.title}</div>
                  {result.effective_from && <div style={{ fontSize: 12, color: '#6B7280' }}>Effective from: {result.effective_from}</div>}
                  {result.note && <div style={{ fontSize: 12, color: '#333', marginTop: 8, padding: '6px 10px', background: '#F5F5F5', borderRadius: 6, border: '1px solid #E5E5E5' }}>
                    <AlertTriangle style={{ width: 11, height: 11, display: 'inline', marginRight: 4 }} />{result.note}
                  </div>}
                </>
              ) : (
                <div style={{ fontSize: 13, color: '#333' }}>{result.error}</div>
              )}
            </div>
          )}
        </>
      ) : (
        <>
          {/* Batch Input */}
          <textarea
            value={batchInput}
            onChange={e => setBatchInput(e.target.value)}
            placeholder="Enter sections separated by commas or new lines:&#10;302, 420, 498A, 354, 438, 482"
            style={{
              width: '100%', maxWidth: 560, minHeight: 100, padding: 14, fontSize: 13,
              border: '1px solid #D1D5DB', borderRadius: 8, marginBottom: 12,
              fontFamily: "'Inter', sans-serif", resize: 'vertical',
            }}
          />
          <button onClick={handleBatch} disabled={loading} style={{
            padding: '10px 20px', borderRadius: 8, fontSize: 13, fontWeight: 600,
            background: '#0A0A0A', color: '#fff', border: 'none', cursor: 'pointer',
            opacity: loading ? 0.5 : 1, marginBottom: 20,
          }}>{loading ? 'Converting...' : 'Convert All'}</button>

          {/* Batch Results Table */}
          {batchResults.length > 0 && (
            <div style={{ maxWidth: 700, overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ background: '#F5F7FA' }}>
                    <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, borderBottom: '2px solid #E2E8F0' }}>Old Section</th>
                    <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, borderBottom: '2px solid #E2E8F0' }}>New Section</th>
                    <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, borderBottom: '2px solid #E2E8F0' }}>Offence / Title</th>
                    <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, borderBottom: '2px solid #E2E8F0' }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {batchResults.map((r, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid #F1F5F9' }}>
                      <td style={{ padding: '8px 12px', fontFamily: "'Inter', sans-serif", fontWeight: 600 }}>{r.old_section || '-'}</td>
                      <td style={{ padding: '8px 12px', fontFamily: "'Inter', sans-serif", fontWeight: 600, color: '#000' }}>{r.new_section || '-'}</td>
                      <td style={{ padding: '8px 12px' }}>{r.title || r.error || '-'}</td>
                      <td style={{ padding: '8px 12px' }}>
                        <span style={{
                          fontSize: 10, fontWeight: 600, padding: '2px 6px', borderRadius: 4,
                          background: r.found ? '#F0F0F0' : '#F0F0F0', color: '#000',
                        }}>{r.found ? 'MAPPED' : 'NOT FOUND'}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
